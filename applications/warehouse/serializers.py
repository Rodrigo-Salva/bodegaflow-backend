from rest_framework import serializers
from django.db import transaction
from .models import Warehouse, Stock, Movement
from applications.catalog.models import Product


class WarehouseSerializer(serializers.ModelSerializer):
    total_stock = serializers.SerializerMethodField()
    capacity_used = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'location', 'capacity', 'is_active',
                  'created_at', 'updated_at', 'total_stock', 
                  'capacity_used', 'products_count']
        read_only_fields = ['created_at', 'updated_at']

    def get_total_stock(self, obj):
        """Retorna el total de productos en el almacén"""
        return obj.get_total_stock()

    def get_capacity_used(self, obj):
        """Retorna el porcentaje de capacidad usado"""
        return round(obj.get_capacity_used(), 2)

    def get_products_count(self, obj):
        """Retorna cantidad de productos diferentes"""
        return obj.stocks.count()

    def validate_name(self, value):
        """Valida que el nombre no esté vacío"""
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre no puede estar vacío")
        return value.strip()

    def validate_capacity(self, value):
        """Valida la capacidad"""
        if value is not None and value < 0:
            raise serializers.ValidationError("La capacidad no puede ser negativa")
        return value


class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    is_low_stock = serializers.SerializerMethodField()
    min_stock = serializers.IntegerField(source='product.min_stock', read_only=True)

    class Meta:
        model = Stock
        fields = ['id', 'product', 'product_name', 'product_sku',
                  'warehouse', 'warehouse_name', 'quantity', 
                  'is_low_stock', 'min_stock', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_is_low_stock(self, obj):
        """Indica si está bajo de stock"""
        return obj.is_low_stock()

    def validate_quantity(self, value):
        """Valida que la cantidad no sea negativa"""
        if value < 0:
            raise serializers.ValidationError("La cantidad no puede ser negativa")
        return value

    def validate(self, data):
        """Validación de unicidad manual si es creación"""
        if not self.instance:  # Solo en creación
            product = data.get('product')
            warehouse = data.get('warehouse')
            
            if Stock.objects.filter(product=product, warehouse=warehouse).exists():
                raise serializers.ValidationError(
                    "Ya existe un registro de stock para este producto en este almacén"
                )
        
        return data


class MovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Movement
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'warehouse', 'warehouse_name',
            'type', 'type_display', 'quantity', 'reference', 'notes',
            'created_by', 'created_by_username',
            'created_at'
        ]
        read_only_fields = ['created_by', 'created_at']

    def validate_quantity(self, value):
        """Valida que la cantidad sea mayor a 0"""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        return value

    def validate_warehouse(self, value):
        """Valida que el almacén esté activo"""
        if not value.is_active:
            raise serializers.ValidationError("El almacén no está activo")
        return value

    def validate(self, data):
        """Validación de stock disponible para salidas"""
        movement_type = data.get('type')
        product = data.get('product')
        warehouse = data.get('warehouse')
        quantity = data.get('quantity')

        # Validar stock disponible solo para salidas (OUT)
        if movement_type == Movement.OUT:
            try:
                stock = Stock.objects.get(product=product, warehouse=warehouse)
                if stock.quantity < quantity:
                    raise serializers.ValidationError({
                        'quantity': f'Stock insuficiente. Disponible: {stock.quantity}, '
                                   f'Solicitado: {quantity}'
                    })
            except Stock.DoesNotExist:
                raise serializers.ValidationError({
                    'warehouse': 'No hay stock registrado para este producto en este almacén'
                })

        return data

    @transaction.atomic
    def create(self, validated_data):
        """Crear movimiento y actualizar stock automáticamente"""
        # Crear el movimiento
        movement = Movement.objects.create(**validated_data)

        # Actualizar o crear stock
        stock, created = Stock.objects.get_or_create(
            product=movement.product,
            warehouse=movement.warehouse,
            defaults={'quantity': 0}
        )

        # Actualizar cantidad según tipo de movimiento
        if movement.type == Movement.IN:
            stock.quantity += movement.quantity
        elif movement.type == Movement.OUT:
            stock.quantity -= movement.quantity
            
            # Validar que no quede negativo
            if stock.quantity < 0:
                raise serializers.ValidationError({
                    'quantity': f'Operación dejaría el stock negativo: {stock.quantity}'
                })

        stock.save()

        return movement