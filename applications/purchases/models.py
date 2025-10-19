from django.db import models
from django.core.validators import MinValueValidator
from applications.warehouse.models import Warehouse
from applications.users.models import User
from applications.catalog.models import Product


class Supplier(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    contact_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    ruc = models.CharField(max_length=30, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['ruc']),
        ]

    def __str__(self):
        return self.name

    def get_total_purchases(self):
        """Retorna el total de compras al proveedor"""
        return self.purchases.aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0


class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchases')
    invoice_number = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    purchase_date = models.DateField(db_index=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='purchases')
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='purchases_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-purchase_date', '-created_at']
        indexes = [
            models.Index(fields=['-purchase_date']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['supplier', '-purchase_date']),
            models.Index(fields=['warehouse', '-purchase_date']),
        ]

    def __str__(self):
        return f"PUR-{self.id} - {self.supplier.name}"

    def calculate_total(self):
        """Calcula el total basado en los detalles"""
        return self.details.aggregate(
            total=models.Sum('subtotal')
        )['total'] or 0


class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_details')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    cost_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    subtotal = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    def save(self, *args, **kwargs):
        """Calcula automáticamente el subtotal"""
        self.subtotal = self.quantity * self.cost_price
        super().save(*args, **kwargs)