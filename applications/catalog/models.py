from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError


class ActiveManager(models.Manager):
    """Manager para obtener solo registros activos"""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_deleted', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def soft_delete(self):
        """Marca como eliminado sin borrar de la BD"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def get_products_count(self):
        """Retorna cantidad de productos activos en esta categoría"""
        return self.products.filter(is_deleted=False).count()


class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    sku = models.CharField(
        max_length=64, 
        unique=True, 
        db_index=True,
        help_text="Código único del producto"
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name='products',
        limit_choices_to={'is_deleted': False, 'is_active': True}
    )
    unit = models.CharField(max_length=50, default='unit')
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    min_stock = models.PositiveIntegerField(
        default=0,
        help_text="Stock mínimo antes de alertar"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['name']),
            models.Index(fields=['category', 'is_deleted']),
            models.Index(fields=['is_deleted', 'is_active']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def clean(self):
        """Validaciones personalizadas"""
        if self.price < 0:
            raise ValidationError({'price': 'El precio no puede ser negativo'})
        
        if self.min_stock < 0:
            raise ValidationError({'min_stock': 'El stock mínimo no puede ser negativo'})
        
        # Validar SKU no vacío
        if not self.sku or not self.sku.strip():
            raise ValidationError({'sku': 'El SKU no puede estar vacío'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def soft_delete(self):
        """Marca como eliminado sin borrar de la BD"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save()

    def get_total_stock(self):
        """Retorna el stock total en todos los almacenes"""
        from apps.warehouse.models import Stock
        total = Stock.objects.filter(
            product=self, 
            warehouse__is_deleted=False
        ).aggregate(
            total=models.Sum('quantity')
        )['total']
        return total or 0

    def is_low_stock(self):
        """Verifica si el stock está por debajo del mínimo"""
        return self.get_total_stock() <= self.min_stock

    def get_stock_by_warehouse(self):
        """Retorna stock agrupado por almacén"""
        from apps.warehouse.models import Stock
        return Stock.objects.filter(
            product=self,
            warehouse__is_deleted=False
        ).select_related('warehouse').values(
            'warehouse__name', 'quantity'
        )


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='images',
        limit_choices_to={'is_deleted': False}
    )
    image = models.ImageField(
        upload_to='product_images/%Y/%m/', 
        null=True, 
        blank=True
    )
    caption = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['order', '-is_primary', '-created_at']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        # Si esta imagen es primaria, desmarcar las demás
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, 
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def clean(self):
        """Validar que la imagen no sea muy grande"""
        if self.image and hasattr(self.image, 'size'):
            # Límite de 5MB
            if self.image.size > 5 * 1024 * 1024:
                raise ValidationError({
                    'image': 'La imagen no puede ser mayor a 5MB'
                })