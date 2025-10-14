from django.db import models
from applications.users.models import User
from applications.catalog.models import Product

class Customer(models.Model):
    name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50, blank=True)
    document_number = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Sale(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    invoice_number = models.CharField(max_length=120, blank=True, null=True)
    sale_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"SALE-{self.id} - {self.customer.name}"

class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
