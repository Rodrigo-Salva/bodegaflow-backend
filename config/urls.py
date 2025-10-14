from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView
)
from applications.users.views import CustomTokenObtainPairView
from .swagger import schema_view  # 👈 Import del swagger

urlpatterns = [
    path('admin/', admin.site.urls),

    # 🔐 Autenticación JWT
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # 🔗 Rutas de las aplicaciones
    path('api/users/', include('applications.users.urls')),
    path('api/catalog/', include('applications.catalog.urls')),
    path('api/warehouse/', include('applications.warehouse.urls')),
    path('api/purchases/', include('applications.purchases.urls')),
    path('api/sales/', include('applications.sales.urls')),

    # 📘 Documentación Swagger y Redoc
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
