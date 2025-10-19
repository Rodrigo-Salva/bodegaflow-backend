from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F, Sum, Q

from .models import Warehouse, Stock, Movement
from .serializers import WarehouseSerializer, StockSerializer, MovementSerializer
from applications.users.permissions import IsAdminOrAlmacenero


class WarehouseViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de almacenes"""
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'location']
    ordering_fields = ['name', 'created_at', 'capacity']
    ordering = ['name']

    def get_queryset(self):
        """Filtrar por estado activo si se solicita"""
        queryset = super().get_queryset()
        is_active = self.request.query_params.get('is_active')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset

    @action(detail=True, methods=['get'])
    def stock_list(self, request, pk=None):
        """Obtener todo el stock de un almacén"""
        warehouse = self.get_object()
        stocks = warehouse.stocks.select_related('product').all()
        
        serializer = StockSerializer(stocks, many=True)
        return Response({
            'warehouse': WarehouseSerializer(warehouse).data,
            'total_products': stocks.count(),
            'total_quantity': stocks.aggregate(total=Sum('quantity'))['total'] or 0,
            'stocks': serializer.data
        })

    @action(detail=True, methods=['get'])
    def low_stock_items(self, request, pk=None):
        """Productos con stock bajo en este almacén"""
        warehouse = self.get_object()
        low_stocks = warehouse.stocks.filter(
            quantity__lte=F('product__min_stock')
        ).select_related('product')
        
        serializer = StockSerializer(low_stocks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def capacity_report(self, request):
        """Reporte de capacidad de todos los almacenes"""
        warehouses = self.get_queryset()
        
        report = []
        for warehouse in warehouses:
            total_stock = warehouse.get_total_stock()
            capacity_used = warehouse.get_capacity_used()
            
            report.append({
                'id': warehouse.id,
                'name': warehouse.name,
                'capacity': warehouse.capacity,
                'total_stock': total_stock,
                'capacity_used': capacity_used,
                'is_full': capacity_used >= 90 if warehouse.capacity else False
            })
        
        return Response(report)


class StockViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de stock"""
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['warehouse', 'product']
    search_fields = ['product__name', 'product__sku', 'warehouse__name']
    ordering_fields = ['quantity', 'updated_at']
    ordering = ['warehouse', 'product']

    def get_queryset(self):
        """Queryset optimizado"""
        return Stock.objects.select_related(
            'product', 'warehouse'
        ).all()

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Productos con stock bajo en todos los almacenes"""
        low_stocks = self.get_queryset().filter(
            quantity__lte=F('product__min_stock')
        )
        
        serializer = self.get_serializer(low_stocks, many=True)
        return Response({
            'count': low_stocks.count(),
            'stocks': serializer.data
        })

    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        """Productos sin stock"""
        out_of_stock = self.get_queryset().filter(quantity=0)
        
        serializer = self.get_serializer(out_of_stock, many=True)
        return Response({
            'count': out_of_stock.count(),
            'stocks': serializer.data
        })

    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Stock de un producto en todos los almacenes"""
        product_id = request.query_params.get('product_id')
        
        if not product_id:
            return Response(
                {'error': 'Se requiere product_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stocks = self.get_queryset().filter(product_id=product_id)
        
        serializer = self.get_serializer(stocks, many=True)
        return Response({
            'total_quantity': stocks.aggregate(total=Sum('quantity'))['total'] or 0,
            'warehouses_count': stocks.count(),
            'stocks': serializer.data
        })

    @action(detail=False, methods=['post'])
    def transfer(self, request):
        """Transferir stock entre almacenes"""
        product_id = request.data.get('product_id')
        from_warehouse_id = request.data.get('from_warehouse_id')
        to_warehouse_id = request.data.get('to_warehouse_id')
        quantity = request.data.get('quantity')

        # Validaciones
        if not all([product_id, from_warehouse_id, to_warehouse_id, quantity]):
            return Response(
                {'error': 'Faltan campos requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if from_warehouse_id == to_warehouse_id:
            return Response(
                {'error': 'Los almacenes de origen y destino deben ser diferentes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError()
        except ValueError:
            return Response(
                {'error': 'La cantidad debe ser un número positivo'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar stock disponible
        try:
            from_stock = Stock.objects.get(
                product_id=product_id,
                warehouse_id=from_warehouse_id
            )
        except Stock.DoesNotExist:
            return Response(
                {'error': 'No hay stock en el almacén de origen'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if from_stock.quantity < quantity:
            return Response(
                {'error': f'Stock insuficiente. Disponible: {from_stock.quantity}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear movimientos de salida y entrada
        Movement.objects.create(
            product_id=product_id,
            warehouse_id=from_warehouse_id,
            type=Movement.OUT,
            quantity=quantity,
            reference=f'Transferencia a almacén {to_warehouse_id}',
            created_by=request.user
        )

        Movement.objects.create(
            product_id=product_id,
            warehouse_id=to_warehouse_id,
            type=Movement.IN,
            quantity=quantity,
            reference=f'Transferencia desde almacén {from_warehouse_id}',
            created_by=request.user
        )

        # Actualizar stocks
        from_stock.quantity -= quantity
        from_stock.save()

        to_stock, _ = Stock.objects.get_or_create(
            product_id=product_id,
            warehouse_id=to_warehouse_id,
            defaults={'quantity': 0}
        )
        to_stock.quantity += quantity
        to_stock.save()

        return Response({
            'message': 'Transferencia exitosa',
            'from_stock': StockSerializer(from_stock).data,
            'to_stock': StockSerializer(to_stock).data
        })


class MovementViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de movimientos"""
    queryset = Movement.objects.all() 
    serializer_class = MovementSerializer
    permission_classes = [IsAdminOrAlmacenero]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'warehouse', 'type', 'created_by']
    search_fields = ['product__name', 'product__sku', 'reference']
    ordering_fields = ['created_at', 'quantity']
    ordering = ['-created_at']

    def get_queryset(self):
        """Queryset optimizado"""
        return Movement.objects.select_related(
            'product', 'warehouse', 'created_by'
        ).all()

    def perform_create(self, serializer):
        """Asignar usuario actual al crear movimiento"""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Movimientos recientes (últimos 50)"""
        recent_movements = self.get_queryset()[:50]
        
        serializer = self.get_serializer(recent_movements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Filtrar movimientos por tipo"""
        movement_type = request.query_params.get('type')
        
        if movement_type not in [Movement.IN, Movement.OUT]:
            return Response(
                {'error': 'Tipo inválido. Use IN o OUT'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        movements = self.get_queryset().filter(type=movement_type)
        
        serializer = self.get_serializer(movements, many=True)
        return Response({
            'count': movements.count(),
            'total_quantity': movements.aggregate(total=Sum('quantity'))['total'] or 0,
            'movements': serializer.data
        })