from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, 
    ProfileViewSet, 
    RegisterView,
    CustomTokenObtainPairView
)
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

# Crear router
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', ProfileViewSet, basename='profile')

# URLs del router
urlpatterns = router.urls

# URLs adicionales
urlpatterns += [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]