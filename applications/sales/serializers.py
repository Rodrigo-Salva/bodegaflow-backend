from applications.core import models
from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from .models import Customer, Sale, SaleDetail
from applications.warehouse.models import Stock
from applications.catalog.models import Product


class CustomerSerializer(serializers.ModelSerializer):
    total_purchases = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'document_type', 'document_number', 
                  'email', 'phone', 'address', 'created_at', 'updated_at', 
                  'total_purchases']
        read_only_fields = ['created_at', 'updated_at']

    def get_total_purchases(self, obj):
        """Retorna el total de compras del cliente"""
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


class SaleDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = SaleDetail
        fields = ['id', 'product', 'product_name', 'product_sku', 
                  'quantity', 'unit_price', 'subtotal']
        read_only_fields = ['subtotal']

    def validate_quantity(self, value):
        """Valida que la cantidad sea mayor a 0"""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        return value

    def validate_unit_price(self, value):
        """Valida que el precio sea mayor a 0"""
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0")
        return value


class SaleSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    details = SaleDetailSerializer(many=True)

    class Meta:
        model = Sale
        fields = [
            'id', 'customer', 'customer_name',
            'invoice_number', 'sale_date', 'total_amount',
            'created_by', 'created_by_name', 'details',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def validate_sale_date(self, value):
        """Valida que la fecha no sea futura"""
        if value > timezone.now().date():
            raise serializers.ValidationError("La fecha de venta no puede ser futura")
        return value

    def validate_details(self, value):
        """Valida que haya al menos un detalle"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("Debe incluir al menos un producto")
        return value

    def validate(self, data):
        """Validaciones que involucran múltiples campos"""
        details = data.get('details', [])
        
        if not details:
            raise serializers.ValidationError({
                'details': 'Debe incluir al menos un producto'
            })

        # Validar stock disponible ANTES de crear la venta
        for detail in details:
            product = detail['product']
            quantity = detail['quantity']
            
            # Obtener stock total del producto
            total_stock = Stock.objects.filter(
                product=product
            ).aggregate(total=models.Sum('quantity'))['total'] or 0
            
            if total_stock < quantity:
                raise serializers.ValidationError({
                    'details': f"Stock insuficiente para {product.name}. "
                               f"Disponible: {total_stock}, Solicitado: {quantity}"
                })

        # Validar que el total coincida con la suma de subtotales
        calculated_total = sum(
            detail['quantity'] * detail['unit_price'] 
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
        """Crear venta con transacción atómica"""
        details_data = validated_data.pop('details', [])
        
        # Crear la venta
        sale = Sale.objects.create(**validated_data)

        # Crear detalles y actualizar stock
        for detail_data in details_data:
            product = detail_data['product']
            quantity = detail_data['quantity']
            unit_price = detail_data['unit_price']
            subtotal = quantity * unit_price

            # Crear detalle
            SaleDetail.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal
            )

            # Reducir stock (tomando del primer almacén con stock disponible)
            stocks = Stock.objects.filter(
                product=product, 
                quantity__gt=0
            ).order_by('-quantity')

            remaining = quantity
            for stock in stocks:
                if remaining <= 0:
                    break
                
                if stock.quantity >= remaining:
                    stock.quantity -= remaining
                    stock.save()
                    remaining = 0
                else:
                    remaining -= stock.quantity
                    stock.quantity = 0
                    stock.save()

            if remaining > 0:
                # Esto no debería pasar por la validación previa, pero por seguridad
                raise serializers.ValidationError(
                    f"Error al descontar stock de {product.name}"
                )

        return sale

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Actualizar venta (solo campos básicos, no detalles)
        Los detalles no se pueden modificar una vez creada la venta
        """
        # Remover detalles si se enviaron
        validated_data.pop('details', None)
        
        # Actualizar solo campos permitidos
        instance.invoice_number = validated_data.get('invoice_number', instance.invoice_number)
        instance.save()
        
        return instance