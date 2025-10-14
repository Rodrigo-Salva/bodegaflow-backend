from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, StockViewSet, MovementViewSet

router = DefaultRouter()
router.register(r'warehouses', WarehouseViewSet)
router.register(r'stocks', StockViewSet)
router.register(r'movements', MovementViewSet)

urlpatterns = router.urls
