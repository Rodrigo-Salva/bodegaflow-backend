from rest_framework import viewsets, permissions
from .models import Supplier, Purchase, PurchaseDetail
from .serializers import SupplierSerializer, PurchaseSerializer, PurchaseDetailSerializer
from applications.users.permissions import IsAdminOrAlmacenero

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]


class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.prefetch_related('details', 'supplier', 'warehouse')
    serializer_class = PurchaseSerializer
    permission_classes = [IsAdminOrAlmacenero]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PurchaseDetailViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PurchaseDetail.objects.select_related('purchase', 'product')
    serializer_class = PurchaseDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
