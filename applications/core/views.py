from rest_framework import viewsets, permissions
from .models import Purchase
from .serializers import PurchaseSerializer

class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.all().order_by('-purchase_date')
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['supplier','warehouse','purchase_date']