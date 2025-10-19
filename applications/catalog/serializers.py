from rest_framework import serializers
from django.db import transaction
from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'is_active', 
                  'created_at', 'updated_at', 'products_count']
        read_only_fields = ['created_at', 'updated_at']

    def get_products_count(self, obj):
        """Retorna cantidad de productos activos"""
        return obj.get_products_count()

    def validate_name(self, value):
        """Valida que el nombre no esté vacío y sea único"""
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre no puede estar vacío")
        
        # Validar unicidad excluyendo el objeto actual en updates
        query = Category.objects.filter(name__iexact=value, is_deleted=False)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        
        if query.exists():
            raise serializers.ValidationError("Ya existe una categoría con este nombre")
        
        return value.strip()


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'image_url', 'caption', 
                  'is_primary', 'order', 'created_at']
        read_only_fields = ['created_at']

    def get_image_url(self, obj):
        """Retorna URL completa de la imagen"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def validate_image(self, value):
        """Valida el tamaño y tipo de imagen"""
        if value:
            # Validar tamaño (5MB máximo)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    "La imagen no puede ser mayor a 5MB"
                )
            
            # Validar tipo de archivo
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
            if hasattr(value, 'content_type') and value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Solo se permiten imágenes JPG, PNG o WebP"
                )
        
        return value


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'category_name', 'price', 
                  'unit', 'primary_image', 'stock_status', 'is_active']

    def get_primary_image(self, obj):
        """Retorna la imagen principal del producto"""
        image = obj.images.filter(is_primary=True).first()
        if image and image.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(image.image.url)
            return image.image.url
        return None

    def get_stock_status(self, obj):
        """Retorna estado del stock"""
        total_stock = obj.get_total_stock()
        return {
            'quantity': total_stock,
            'is_low': obj.is_low_stock(),
            'min_stock': obj.min_stock
        }


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.active.all(),
        source='category',
        write_only=True,
        error_messages={
            'does_not_exist': 'La categoría no existe o está inactiva'
        }
    )
    images = ProductImageSerializer(many=True, read_only=True)
    total_stock = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    stock_by_warehouse = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'category', 'category_id', 'unit', 
                  'price', 'min_stock', 'description', 'is_active',
                  'created_at', 'updated_at', 'images', 'total_stock', 
                  'is_low_stock', 'stock_by_warehouse']
        read_only_fields = ['created_at', 'updated_at']

    def get_total_stock(self, obj):
        """Retorna stock total"""
        return obj.get_total_stock()

    def get_is_low_stock(self, obj):
        """Retorna si está bajo de stock"""
        return obj.is_low_stock()

    def get_stock_by_warehouse(self, obj):
        """Retorna stock por almacén"""
        # Solo incluir si se solicita explícitamente
        if self.context.get('include_warehouse_stock'):
            return list(obj.get_stock_by_warehouse())
        return None

    def validate_sku(self, value):
        """Valida que el SKU sea único y no esté vacío"""
        if not value or not value.strip():
            raise serializers.ValidationError("El SKU no puede estar vacío")
        
        value = value.strip().upper()
        
        # Validar unicidad
        query = Product.objects.filter(sku=value, is_deleted=False)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        
        if query.exists():
            raise serializers.ValidationError("Ya existe un producto con este SKU")
        
        return value

    def validate_price(self, value):
        """Valida que el precio sea positivo"""
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo")
        if value == 0:
            raise serializers.ValidationError("El precio debe ser mayor a cero")
        return value

    def validate_min_stock(self, value):
        """Valida el stock mínimo"""
        if value < 0:
            raise serializers.ValidationError(
                "El stock mínimo no puede ser negativo"
            )
        return value

    def validate(self, data):
        """Validaciones que involucran múltiples campos"""
        # Validar que la categoría esté activa
        category = data.get('category') or (self.instance.category if self.instance else None)
        if category and not category.is_active:
            raise serializers.ValidationError({
                'category_id': 'No se puede asignar una categoría inactiva'
            })
        
        return data

    @transaction.atomic
    def create(self, validated_data):
        """Crear producto con transacción"""
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        """Actualizar producto con transacción"""
        return super().update(instance, validated_data)


class ProductBulkUploadSerializer(serializers.Serializer):
    """Serializer para carga masiva de productos"""
    file = serializers.FileField(
        help_text="Archivo CSV o Excel con productos"
    )

    def validate_file(self, value):
        """Valida el archivo"""
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        file_name = value.name.lower()
        
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                "Solo se permiten archivos CSV o Excel"
            )
        
        # Validar tamaño (10MB máximo)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                "El archivo no puede ser mayor a 10MB"
            )
        
        return value