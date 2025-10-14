from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from applications.purchases.models import PurchaseDetail
from applications.sales.models import SaleDetail
from .models import Stock, Movement
import applications.warehouse.signals

@receiver(post_save, sender=PurchaseDetail)
def handle_purchase_detail(sender, instance, created, **kwargs):
    if not created:
        return
    with transaction.atomic():
        product = instance.product
        warehouse = instance.purchase.warehouse
        stock, _ = Stock.objects.select_for_update().get_or_create(product=product, warehouse=warehouse)
        stock.quantity += instance.quantity
        stock.save()
        Movement.objects.create(
            product=product, warehouse=warehouse, type=Movement.IN,
            quantity=instance.quantity, reference=f"PUR-{instance.purchase.id}", created_by=instance.purchase.created_by
        )

@receiver(post_save, sender=SaleDetail)
def handle_sale_detail(sender, instance, created, **kwargs):
    if not created:
        return
    with transaction.atomic():
        product = instance.product
        stocks = Stock.objects.select_for_update().filter(product=product).order_by('-quantity')
        qty_to_remove = instance.quantity

        aggregate_total = sum([s.quantity for s in stocks])
        if aggregate_total < qty_to_remove:
            raise ValueError("Stock insuficiente para completar la venta")

        for s in stocks:
            if qty_to_remove <= 0:
                break
            take = min(s.quantity, qty_to_remove)
            s.quantity -= take
            s.save()
            Movement.objects.create(
                product=product, warehouse=s.warehouse, type=Movement.OUT,
                quantity=take, reference=f"SALE-{instance.sale.id}", created_by=instance.sale.created_by
            )
            qty_to_remove -= take

