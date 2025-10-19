from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Profile"""
    
    class Meta:
        model = Profile
        fields = ['id', 'phone', 'address', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_phone(self, value):
        """Valida el teléfono"""
        if value and len(value) < 7:
            raise serializers.ValidationError("El teléfono debe tener al menos 7 caracteres")
        return value


class UserSerializer(serializers.ModelSerializer):
    """Serializer base para usuarios"""
    profile = ProfileSerializer(required=False)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'is_active', 'profile', 'password', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['is_active', 'created_at', 'updated_at']

    def validate_username(self, value):
        """Valida que el username no esté vacío y sea único"""
        if not value or not value.strip():
            raise serializers.ValidationError("El usuario no puede estar vacío")
        
        value = value.strip().lower()
        query = User.objects.filter(username=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        
        if query.exists():
            raise serializers.ValidationError("Ya existe un usuario con ese nombre")
        
        return value

    def validate_email(self, value):
        """Valida que el email sea único"""
        if value:
            value = value.strip().lower()
            query = User.objects.filter(email=value)
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
            
            if query.exists():
                raise serializers.ValidationError("Ya existe un usuario con ese email")
        
        return value

    def validate_password(self, value):
        """Valida la contraseña"""
        if value:
            try:
                validate_password(value)
            except serializers.ValidationError as e:
                raise serializers.ValidationError(e.messages)
        return value

    def validate_role(self, value):
        """Valida que el rol sea válido"""
        if value not in dict(User.ROLE_CHOICES):
            raise serializers.ValidationError("Rol inválido")
        return value

    def create(self, validated_data):
        """Crear usuario con perfil opcional"""
        profile_data = validated_data.pop('profile', None)
        password = validated_data.pop('password', None)

        user = User.objects.create_user(**validated_data)
        
        if password:
            user.set_password(password)
            user.save()

        Profile.objects.create(user=user, **(profile_data or {}))
        return user

    def update(self, instance, validated_data):
        """Actualizar usuario y perfil"""
        profile_data = validated_data.pop('profile', None)
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if profile_data is not None:
            Profile.objects.update_or_create(
                user=instance, 
                defaults=profile_data
            )

        return instance


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer con información detallada del usuario"""
    profile = ProfileSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'is_active', 'profile',
            'created_at', 'updated_at', 'last_login'
        ]
        read_only_fields = fields  # ✅ TODAS LAS FIELDS SOLO LECTURA


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer para registro de nuevos usuarios"""
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name'
        ]

    def validate(self, data):
        """Validar que las contraseñas coincidan"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Las contraseñas no coinciden'
            })
        
        try:
            validate_password(data['password'])
        except serializers.ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
        
        return data

    def create(self, validated_data):
        """Crear usuario y su perfil"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        Profile.objects.create(user=user)
        return user
