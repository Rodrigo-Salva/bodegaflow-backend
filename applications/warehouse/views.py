from rest_framework import viewsets, permissions
from .models import Warehouse, Stock, Movement
from .serializers import WarehouseSerializer, StockSerializer, MovementSerializer
from applications.users.permissions import IsAdminOrAlmacenero
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import F

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]


class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.select_related('product', 'warehouse').all()
    serializer_class = StockSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Endpoint: /api/warehouse/stocks/low_stock/"""
        low = self.queryset.filter(quantity__lt=F('product__min_stock'))
        serializer = self.get_serializer(low, many=True)
        return Response(serializer.data)


class MovementViewSet(viewsets.ModelViewSet):
    queryset = Movement.objects.select_related('product', 'warehouse', 'created_by').all()
    serializer_class = MovementSerializer
    permission_classes = [IsAdminOrAlmacenero]

    def perform_create(self, serializer):
        # Asignar automáticamente el usuario que crea el movimiento
        movement = serializer.save(created_by=self.request.user)

        # Actualizar stock automáticamente
        stock, _ = Stock.objects.get_or_create(
            product=movement.product,
            warehouse=movement.warehouse,
            defaults={'quantity': 0}
        )

        if movement.type == 'IN':
            stock.quantity += movement.quantity
        elif movement.type == 'OUT':
            stock.quantity -= movement.quantity

        stock.save()
