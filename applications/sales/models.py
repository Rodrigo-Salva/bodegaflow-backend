from django.db import models
from django.core.validators import MinValueValidator
from applications.users.models import User
from applications.catalog.models import Product


class Customer(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    document_type = models.CharField(max_length=50, blank=True)
    document_number = models.CharField(max_length=100, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['document_number']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

    def get_total_purchases(self):
        """Retorna el total de compras del cliente"""
        return self.sales.aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0


class Sale(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    invoice_number = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    sale_date = models.DateField(db_index=True)
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sale_date', '-created_at']
        indexes = [
            models.Index(fields=['-sale_date']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['customer', '-sale_date']),
        ]

    def __str__(self):
        return f"SALE-{self.id} - {self.customer.name}"

    def calculate_total(self):
        """Calcula el total basado en los detalles"""
        return self.details.aggregate(
            total=models.Sum('subtotal')
        )['total'] or 0


class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_details')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
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
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)