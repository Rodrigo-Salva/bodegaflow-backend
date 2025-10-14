from rest_framework.routers import DefaultRouter
from django.urls import path, include
from applications.catalog.views import ProductViewSet, CategoryViewSet
from applications.purchases.views import PurchaseViewSet
from applications.sales.views import SaleViewSet
from applications.warehouse.views import StockViewSet, MovementViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register('products', ProductViewSet)
router.register('categories', CategoryViewSet)
router.register('purchases', PurchaseViewSet, basename='purchase')
router.register('sales', SaleViewSet, basename='sale')
router.register('stock', StockViewSet, basename='stock')
router.register('movements', MovementViewSet, basename='movement')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
