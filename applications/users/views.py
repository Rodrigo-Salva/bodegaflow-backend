from rest_framework import viewsets, permissions, decorators, response, generics
from django.contrib.auth import get_user_model
from .models import Profile
from applications.users.permissions import IsAdmin
from .serializers import UserSerializer, ProfileSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().select_related('profile')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        # 🔹 Evitar errores al generar Swagger
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()
        
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'vendedor':
            # Los vendedores solo ven su propio usuario
            return User.objects.filter(id=user.id)
        # Admin ve todos
        return User.objects.all()

    @decorators.action(detail=False, methods=['get'])
    def me(self, request):
        """Endpoint: /api/users/users/me/ -> retorna el usuario logueado"""
        serializer = self.get_serializer(request.user)
        return response.Response(serializer.data)


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user')
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 🔹 Evitar errores al generar Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Profile.objects.none()
        
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'vendedor':
            # Vendedor solo ve su perfil
            return Profile.objects.filter(user=user)
        return Profile.objects.all()


class RegisterView(generics.CreateAPIView):
    """Endpoint para registrar usuarios: /api/users/register/"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


# --- SERIALIZER PERSONALIZADO PARA JWT ---
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Agregar información extra al token
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = getattr(user, 'role', None)
        return token


# --- VISTA PERSONALIZADA JWT ---
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
