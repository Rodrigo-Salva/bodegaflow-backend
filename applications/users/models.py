from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLES = (("admin","Admin"),("vendedor","Vendedor"),("almacenero","Almacenero"))
    role = models.CharField(max_length=20, choices=ROLES, default="vendedor")

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name or self.user.username
