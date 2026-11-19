from rest_framework import serializers

from .models import Product


class ProductCreateSerializer(serializers.Serializer):
    manufacturing_id = serializers.UUIDField()
    product_name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    product_type = serializers.CharField(max_length=100)
    manufacture_date = serializers.DateField()
    expiry_date = serializers.DateField(required=False, allow_null=True)
    batch_number = serializers.CharField(max_length=100)
    total_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit = serializers.CharField(max_length=20)
    product_image = serializers.ImageField(required=False, allow_null=True)

    def validate_total_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Total quantity must be greater than zero.')
        return value


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'
