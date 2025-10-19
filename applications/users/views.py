from rest_framework import viewsets, permissions, decorators, status, filters
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend

from .models import Profile
from .serializers import (
    UserSerializer, 
    ProfileSerializer, 
    UserDetailSerializer,
    UserCreateSerializer
)
from .permissions import IsAdminOrSelf

User = get_user_model()


# ==========================================================
# 🔐 TOKEN JWT PERSONALIZADO
# ==========================================================
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personalizado para JWT con info extra"""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        token['is_admin'] = user.is_admin()
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ==========================================================
# 👤 USUARIOS
# ==========================================================
class UserViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de usuarios"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'created_at', 'role']
    ordering = ['username']

    def get_queryset(self):
        """Filtrar usuarios según el rol del usuario autenticado"""
        user = self.request.user

        # 🚀 Evitar errores en Swagger (usuario anónimo)
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()

        if not user.is_authenticated:
            return User.objects.none()

        if hasattr(user, "is_admin") and user.is_admin():
            return User.objects.select_related('profile').all()

        return User.objects.filter(id=user.id).select_related('profile')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'list']:
            return [permissions.IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminOrSelf()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        if not request.user.is_admin():
            return Response(
                {'error': 'No tienes permiso para crear usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_admin():
            return Response(
                {'error': 'No tienes permiso para eliminar usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @decorators.action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    @decorators.action(detail=False, methods=['put', 'patch'])
    def change_password(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        new_password_confirm = request.data.get('new_password_confirm')

        if not old_password:
            return Response({'error': 'Se requiere la contraseña actual'}, status=status.HTTP_400_BAD_REQUEST)
        if not user.check_password(old_password):
            return Response({'error': 'La contraseña actual es incorrecta'}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != new_password_confirm:
            return Response({'error': 'Las contraseñas no coinciden'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Contraseña actualizada correctamente'})

    @decorators.action(detail=True, methods=['post'])
    def set_active(self, request, pk=None):
        if not request.user.is_admin():
            return Response({'error': 'No tienes permiso'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({'error': 'Se requiere el campo is_active'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = bool(is_active)
        user.save()
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @decorators.action(detail=True, methods=['post'])
    def set_role(self, request, pk=None):
        if not request.user.is_admin():
            return Response({'error': 'No tienes permiso'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        role = request.data.get('role')
        if role not in dict(User.ROLE_CHOICES):
            return Response({'error': 'Rol inválido'}, status=status.HTTP_400_BAD_REQUEST)
        user.role = role
        user.save()
        serializer = self.get_serializer(user)
        return Response(serializer.data)


# ==========================================================
# 👤 PERFILES
# ==========================================================
class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['user__username', 'created_at']
    ordering = ['user__username']

    def get_queryset(self):
        user = self.request.user

        # 🚀 Evitar error en Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Profile.objects.none()

        if not user.is_authenticated:
            return Profile.objects.none()

        if hasattr(user, "is_admin") and user.is_admin():
            return Profile.objects.select_related('user').all()

        return Profile.objects.filter(user=user)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminOrSelf()]
        return [permissions.IsAuthenticated()]

    @decorators.action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ==========================================================
# 🆕 REGISTRO DE USUARIOS
# ==========================================================
class RegisterView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'message': 'Usuario registrado correctamente'
        }, status=status.HTTP_201_CREATED)
