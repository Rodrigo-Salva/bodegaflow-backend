from rest_framework import viewsets, permissions
from .models import Customer, Sale, SaleDetail
from applications.users.permissions import IsAdminOrVendedor
from .serializers import CustomerSerializer, SaleSerializer, SaleDetailSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.prefetch_related('details', 'customer')
    serializer_class = SaleSerializer
    permission_classes = [IsAdminOrVendedor]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SaleDetailViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SaleDetail.objects.select_related('sale', 'product')
    serializer_class = SaleDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
