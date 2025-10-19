from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from applications.catalog.models import Product
from applications.users.models import User


class Warehouse(models.Model):
    name = models.CharField(max_length=120, unique=True, db_index=True)
    location = models.CharField(max_length=255, blank=True)
    capacity = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def get_total_stock(self):
        """Retorna la cantidad total de productos en este almacén"""
        return self.stocks.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0

    def get_capacity_used(self):
        """Retorna el porcentaje de capacidad utilizado"""
        if self.capacity and self.capacity > 0:
            total = self.get_total_stock()
            return (total / self.capacity) * 100
        return 0


class Stock(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='stocks'
    )
    warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.CASCADE, 
        related_name='stocks'
    )
    quantity = models.IntegerField(default=0)  # Puede ser negativo temporalmente
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'warehouse')
        ordering = ['warehouse', 'product']
        indexes = [
            models.Index(fields=['product', 'warehouse']),
            models.Index(fields=['quantity']),
        ]

    def __str__(self):
        return f"{self.product.sku} @ {self.warehouse.name}: {self.quantity}"

    def clean(self):
        """Validar que no haya stock negativo al guardar"""
        if self.quantity < 0:
            raise ValidationError({
                'quantity': f'El stock no puede ser negativo. Stock actual: {self.quantity}'
            })

    def is_low_stock(self):
        """Verifica si está por debajo del stock mínimo del producto"""
        return self.quantity <= self.product.min_stock


class Movement(models.Model):
    IN = 'IN'
    OUT = 'OUT'
    TYPE_CHOICES = (
        (IN, 'Entrada'),
        (OUT, 'Salida')
    )

    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT,  # PROTECT en lugar de CASCADE
        related_name='movements'
    )
    warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.PROTECT,  # PROTECT en lugar de CASCADE
        related_name='movements'
    )
    type = models.CharField(max_length=3, choices=TYPE_CHOICES, db_index=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reference = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='movements_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['product', 'warehouse']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"{self.product.name} {self.get_type_display()} ({self.quantity})"