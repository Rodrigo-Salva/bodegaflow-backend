from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from datetime import timedelta
from django.utils import timezone

from .models import Customer, Sale, SaleDetail
from applications.users.permissions import IsAdminOrVendedor
from .serializers import CustomerSerializer, SaleSerializer, SaleDetailSerializer


# ===============================
#   CUSTOMER VIEWSET
# ===============================
class CustomerViewSet(viewsets.ModelViewSet):
    """📇 ViewSet para gestión de clientes"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'document_number', 'email', 'phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


# ===============================
#   SALE VIEWSET
# ===============================
class SaleViewSet(viewsets.ModelViewSet):
    """💰 ViewSet para gestión de ventas"""
    queryset = Sale.objects.select_related('customer', 'created_by').prefetch_related('details__product').all()
    serializer_class = SaleSerializer
    permission_classes = [IsAdminOrVendedor]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'sale_date']
    search_fields = ['invoice_number', 'customer__name']
    ordering_fields = ['sale_date', 'total_amount', 'created_at']
    ordering = ['-sale_date', '-created_at']

    def perform_create(self, serializer):
        """Asignar usuario actual al crear venta"""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """📅 Ventas del día actual"""
        today = timezone.now().date()
        sales = self.get_queryset().filter(sale_date=today)

        serializer = self.get_serializer(sales, many=True)
        return Response({
            'count': sales.count(),
            'total': sales.aggregate(total=Sum('total_amount'))['total'] or 0,
            'sales': serializer.data
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """📊 Estadísticas de ventas (día, semana, mes)"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        def get_stats(start_date=None):
            qs = Sale.objects.all()
            if start_date:
                qs = qs.filter(sale_date__gte=start_date)
            total = qs.aggregate(total=Sum('total_amount'))['total'] or 0
            return {'count': qs.count(), 'total': total}

        stats = {
            'today': get_stats(today),
            'week': get_stats(week_ago),
            'month': get_stats(month_ago)
        }
        return Response(stats)


# ===============================
#   SALE DETAIL VIEWSET
# ===============================
class SaleDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """🧾 ViewSet de solo lectura para detalles de venta"""
    queryset = SaleDetail.objects.select_related('sale', 'product', 'sale__customer').all()
    serializer_class = SaleDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sale', 'product']
