from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Solo usuarios con rol admin"""
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and
            request.user.role == 'admin'
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admin puede hacer todo, otros solo lectura"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            request.user and 
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'admin'
        )


class IsAdminOrVendedor(permissions.BasePermission):
    """Admin o Vendedor"""
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role in ['admin', 'vendedor']
        )


class IsAdminOrAlmacenero(permissions.BasePermission):
    """Admin o Almacenero"""
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role in ['admin', 'almacenero']
        )


class IsAdminOrSelf(permissions.BasePermission):
    """Admin puede modificar cualquiera, otros solo su propio perfil"""
    def has_object_permission(self, request, view, obj):
        # Admin puede hacer todo
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return True
        
        # Otros solo pueden modificarse a sí mismos
        if hasattr(obj, 'user'):  # Es un Profile
            return obj.user == request.user
        
        # Es un User
        return obj == request.userÑ