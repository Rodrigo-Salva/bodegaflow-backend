from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Bodega API",
        default_version='v1',
        description="API para gestión de bodega — productos, ventas, compras, almacén, usuarios y clientes.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="support@bodegaapi.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)
