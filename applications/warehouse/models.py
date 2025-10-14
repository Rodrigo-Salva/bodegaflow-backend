from django.db import models
from applications.catalog.models import Product
from applications.users.models import User

class Warehouse(models.Model):
    name = models.CharField(max_length=120, unique=True)
    location = models.CharField(max_length=255, blank=True)
    capacity = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name

class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.IntegerField(default=0)

    class Meta:
        unique_together = ('product','warehouse')

    def __str__(self):
        return f"{self.product.sku} @ {self.warehouse.name}: {self.quantity}"

class Movement(models.Model):
    IN = 'IN'
    OUT = 'OUT'
    TYPE_CHOICES = ((IN, 'Entrada'), (OUT, 'Salida'))

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    reference = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Movements'

    def __str__(self):
        return f"{self.product.name} {self.type} ({self.quantity})"

