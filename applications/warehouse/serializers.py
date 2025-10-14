from rest_framework import serializers
from .models import Warehouse, Stock, Movement
from applications.catalog.models import Product


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'location', 'capacity']


class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = Stock
        fields = ['id', 'product', 'product_name', 'warehouse', 'warehouse_name', 'quantity']


class MovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Movement
        fields = [
            'id', 'product', 'product_name',
            'warehouse', 'warehouse_name',
            'type', 'quantity', 'reference',
            'created_by', 'created_by_username',
            'created_at'
        ]
        read_only_fields = ['created_by', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        movement = Movement.objects.create(created_by=user, **validated_data)

        # 🧠 Actualizamos el stock automáticamente
        stock, _ = Stock.objects.get_or_create(
            product=movement.product,
            warehouse=movement.warehouse
        )
        if movement.type == Movement.IN:
            stock.quantity += movement.quantity
        else:
            stock.quantity -= movement.quantity
        stock.save()

        return movement
