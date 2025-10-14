from django.urls import path
from .views import RegisterView
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ProfileViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profiles', ProfileViewSet)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
]


urlpatterns = router.urls
