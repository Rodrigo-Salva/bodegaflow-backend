from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, SaleViewSet, SaleDetailViewSet

router = DefaultRouter()

router.register(r'customers', CustomerViewSet)
router.register(r'sales', SaleViewSet)
router.register(r'details', SaleDetailViewSet)

urlpatterns = router.urls
