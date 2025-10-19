from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    ADMIN = 'admin'
    VENDEDOR = 'vendedor'
    ALMACENERO = 'almacenero'
    
    ROLE_CHOICES = (
        (ADMIN, 'Admin'),
        (VENDEDOR, 'Vendedor'),
        (ALMACENERO, 'Almacenero')
    )
    
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default=VENDEDOR,
        db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['username']
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def is_admin(self):
        return self.role == self.ADMIN

    def is_vendedor(self):
        return self.role == self.VENDEDOR

    def is_almacenero(self):
        return self.role == self.ALMACENERO


class Profile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    phone = models.CharField(
        max_length=20, 
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^[\d\s\+\-\(\)]{0,20}$',
                message='Número telefónico inválido'
            )
        ]
    )
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return f"Profile: {self.user.username}"