from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from .models import Supplier, Purchase, PurchaseDetail
from applications.catalog.models import Product
from applications.warehouse.models import Warehouse, Stock


class SupplierSerializer(serializers.ModelSerializer):
    total_purchases = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact_name', 'phone', 'email', 
                  'address', 'ruc', 'created_at', 'updated_at', 'total_purchases']
        read_only_fields = ['created_at', 'updated_at']

    def get_total_purchases(self, obj):
        """Retorna el total de compras al proveedor"""
        return obj.get_total_purchases()

    def validate_name(self, value):
        """Valida que el nombre no esté vacío"""
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre no puede estar vacío")
        return value.strip()

    def validate_email(self, value):
        """Valida el email si se proporciona"""
        if value and not value.strip():
            return ''
        return value.strip() if value else ''

    def validate_ruc(self, value):
        """Valida el RUC si se proporciona"""
        if value:
            value = value.strip()
            # Puedes agregar validación específica de RUC aquí
            if len(value) > 0 and len(value) < 8:
                raise serializers.ValidationError("El RUC debe tener al menos 8 caracteres")
        return value


class PurchaseDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = PurchaseDetail
        fields = ['id', 'product', 'product_name', 'product_sku', 
                  'quantity', 'cost_price', 'subtotal']
        read_only_fields = ['subtotal']

    def validate_quantity(self, value):
        """Valida que la cantidad sea mayor a 0"""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        return value

    def validate_cost_price(self, value):
        """Valida que el precio de costo sea mayor a 0"""
        if value <= 0:
            raise serializers.ValidationError("El precio de costo debe ser mayor a 0")
        return value


class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    details = PurchaseDetailSerializer(many=True)

    class Meta:
        model = Purchase
        fields = [
            'id', 'supplier', 'supplier_name', 
            'invoice_number', 'purchase_date', 
            'warehouse', 'warehouse_name',
            'total_amount', 'created_by', 'created_by_name', 
            'details', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def validate_purchase_date(self, value):
        """Valida que la fecha no sea futura"""
        if value > timezone.now().date():
            raise serializers.ValidationError("La fecha de compra no puede ser futura")
        return value

    def validate_details(self, value):
        """Valida que haya al menos un detalle"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("Debe incluir al menos un producto")
        return value

    def validate_warehouse(self, value):
        """Valida que el almacén exista y esté activo"""
        if not value:
            raise serializers.ValidationError("Debe seleccionar un almacén")
        return value

    def validate(self, data):
        """Validaciones que involucran múltiples campos"""
        details = data.get('details', [])
        
        if not details:
            raise serializers.ValidationError({
                'details': 'Debe incluir al menos un producto'
            })

        # Validar que no haya productos duplicados
        product_ids = [detail['product'].id for detail in details]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError({
                'details': 'No puede incluir el mismo producto más de una vez'
            })

        # Validar que el total coincida con la suma de subtotales
        calculated_total = sum(
            detail['quantity'] * detail['cost_price'] 
            for detail in details
        )
        
        if abs(calculated_total - data['total_amount']) > 0.01:  # Tolerancia de 1 centavo
            raise serializers.ValidationError({
                'total_amount': f"El total no coincide. "
                                f"Calculado: {calculated_total}, "
                                f"Recibido: {data['total_amount']}"
            })

        return data

    @transaction.atomic
    def create(self, validated_data):
        """Crear compra con transacción atómica"""
        details_data = validated_data.pop('details', [])
        
        # Crear la compra
        purchase = Purchase.objects.create(**validated_data)

        # Crear detalles y actualizar stock
        for detail_data in details_data:
            product = detail_data['product']
            quantity = detail_data['quantity']
            cost_price = detail_data['cost_price']
            subtotal = quantity * cost_price

            # Crear detalle
            PurchaseDetail.objects.create(
                purchase=purchase,
                product=product,
                quantity=quantity,
                cost_price=cost_price,
                subtotal=subtotal
            )

            # Actualizar o crear stock en el almacén especificado
            stock, created = Stock.objects.get_or_create(
                product=product,
                warehouse=purchase.warehouse,
                defaults={'quantity': 0}
            )
            stock.quantity += quantity
            stock.save()

        return purchase

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Actualizar compra (solo campos básicos, no detalles)
        Los detalles no se pueden modificar una vez creada la compra
        """
        # Remover detalles si se enviaron
        validated_data.pop('details', None)
        
        # Actualizar solo campos permitidos
        instance.invoice_number = validated_data.get('invoice_number', instance.invoice_number)
        instance.save()
        
        return instance