from rest_framework import serializers
from .models import Customer, Sale, SaleDetail
from applications.warehouse.models import Stock
from applications.catalog.models import Product
from applications.users.models import User
from applications.warehouse.models import Warehouse


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class SaleDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SaleDetail
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'subtotal']


class SaleSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    details = SaleDetailSerializer(many=True)

    class Meta:
        model = Sale
        fields = [
            'id', 'customer', 'customer_name',
            'invoice_number', 'sale_date', 'total_amount',
            'created_by', 'created_by_name', 'details'
        ]

    def create(self, validated_data):
        details_data = validated_data.pop('details', [])
        sale = Sale.objects.create(**validated_data)

        total = 0
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
            total += subtotal

            # Reducir stock del producto en su almacén principal
            try:
                stock = Stock.objects.get(product=product)
                if stock.quantity < quantity:
                    raise serializers.ValidationError(f"Stock insuficiente para {product.name}")
                stock.quantity -= quantity
                stock.save()
            except Stock.DoesNotExist:
                raise serializers.ValidationError(f"El producto {product.name} no tiene stock registrado")

        sale.total_amount = total
        sale.save()

        return sale
