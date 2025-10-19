from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from datetime import timedelta
from django.utils import timezone

from .models import Supplier, Purchase, PurchaseDetail
from .serializers import SupplierSerializer, PurchaseSerializer, PurchaseDetailSerializer
from applications.users.permissions import IsAdminOrAlmacenero


class SupplierViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de proveedores"""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'ruc', 'email', 'phone', 'contact_name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class PurchaseViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de compras"""
    queryset = Purchase.objects.all()  # ✅ agregado para que el router tenga referencia
    serializer_class = PurchaseSerializer
    permission_classes = [IsAdminOrAlmacenero]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['supplier', 'warehouse', 'purchase_date']
    search_fields = ['invoice_number', 'supplier__name']
    ordering_fields = ['purchase_date', 'total_amount', 'created_at']
    ordering = ['-purchase_date', '-created_at']

    def get_queryset(self):
        """Queryset optimizado con relaciones para mejorar rendimiento"""
        return Purchase.objects.select_related(
            'supplier', 'warehouse', 'created_by'
        ).prefetch_related(
            'details__product'
        ).all()

    def perform_create(self, serializer):
        """Asigna el usuario actual al crear una compra"""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """📅 Compras del día actual"""
        today = timezone.now().date()
        purchases = self.get_queryset().filter(purchase_date=today)
        
        serializer = self.get_serializer(purchases, many=True)
        return Response({
            'count': purchases.count(),
            'total': purchases.aggregate(total=Sum('total_amount'))['total'] or 0,
            'purchases': serializer.data
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """📊 Estadísticas de compras: día, semana y mes"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {
            'today': {
                'count': Purchase.objects.filter(purchase_date=today).count(),
                'total': Purchase.objects.filter(purchase_date=today).aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
            },
            'week': {
                'count': Purchase.objects.filter(purchase_date__gte=week_ago).count(),
                'total': Purchase.objects.filter(purchase_date__gte=week_ago).aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
            },
            'month': {
                'count': Purchase.objects.filter(purchase_date__gte=month_ago).count(),
                'total': Purchase.objects.filter(purchase_date__gte=month_ago).aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
            }
        }
        
        return Response(stats)


class PurchaseDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet solo lectura para detalles de compra"""
    queryset = PurchaseDetail.objects.all()  # ✅ agregado para evitar el error del basename
    serializer_class = PurchaseDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['purchase', 'product']

    def get_queryset(self):
        """Queryset optimizado con relaciones"""
        return PurchaseDetail.objects.select_related(
            'purchase', 'product', 'purchase__supplier', 'purchase__warehouse'
        ).all()
