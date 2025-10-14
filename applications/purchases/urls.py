from rest_framework.routers import DefaultRouter
from .views import SupplierViewSet, PurchaseViewSet, PurchaseDetailViewSet

router = DefaultRouter()

router.register(r'suppliers', SupplierViewSet)
router.register(r'purchases', PurchaseViewSet)
router.register(r'details', PurchaseDetailViewSet)

urlpatterns = router.urls
