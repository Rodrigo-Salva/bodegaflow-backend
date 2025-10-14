from django.db import models
from applications.users.models import User
from django.utils import timezone

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=500)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

class Report(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
