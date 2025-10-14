from rest_framework import serializers
from .models import Supplier, Purchase, PurchaseDetail
from applications.catalog.models import Product
from applications.warehouse.models import Warehouse, Stock

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class PurchaseDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PurchaseDetail
        fields = ['id', 'product', 'product_name', 'quantity', 'cost_price', 'subtotal']


class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    details = PurchaseDetailSerializer(many=True)

    class Meta:
        model = Purchase
        fields = [
            'id', 'supplier', 'supplier_name', 'invoice_number',
            'purchase_date', 'warehouse', 'total_amount',
            'created_by', 'created_by_name', 'details'
        ]

    def create(self, validated_data):
        details_data = validated_data.pop('details', [])
        purchase = Purchase.objects.create(**validated_data)

        total = 0
        for detail_data in details_data:
            product = detail_data['product']
            quantity = detail_data['quantity']
            cost_price = detail_data['cost_price']
            subtotal = quantity * cost_price

            # Crear detalle de compra
            PurchaseDetail.objects.create(
                purchase=purchase,
                product=product,
                quantity=quantity,
                cost_price=cost_price,
                subtotal=subtotal
            )
            total += subtotal

            # Actualizar stock automáticamente
            stock, _ = Stock.objects.get_or_create(
                product=product,
                warehouse=purchase.warehouse,
                defaults={'quantity': 0}
            )
            stock.quantity += quantity
            stock.save()

        purchase.total_amount = total
        purchase.save()

        return purchase
