from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from factory.models import ManufacturingRecord
from .models import Product, ProductBatch


class ProductSourceBatchSerializer(serializers.ModelSerializer):
    batch_id = serializers.CharField(source='herb_batch.batch_id', read_only=True)
    herb_name = serializers.CharField(source='herb_batch.herb_name', read_only=True)
    botanical_name = serializers.CharField(
        source='herb_batch.botanical_name',
        read_only=True,
    )
    village = serializers.CharField(source='herb_batch.village', read_only=True)
    district = serializers.CharField(source='herb_batch.district', read_only=True)
    state = serializers.CharField(source='herb_batch.state', read_only=True)
    harvest_date = serializers.DateField(
        source='herb_batch.collection_date',
        read_only=True,
    )

    class Meta:
        model = ProductBatch
        fields = (
            'batch_id',
            'herb_name',
            'botanical_name',
            'village',
            'district',
            'state',
            'harvest_date',
        )


class ProductManufacturingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManufacturingRecord
        fields = (
            'manufacturing_id',
            'product_name',
            'process_date',
            'process_description',
            'facility_line',
            'shift',
            'standard_operating_procedure',
            'solvent_method',
            'target_yield_ratio',
            'process_parameters',
            'quality_control_lead',
            'input_quantity',
            'output_quantity',
            'unit',
            'status',
        )


def _product_asset_url(serializer, product, asset):
    if not getattr(product, 'qr_code_image' if asset == 'qr' else 'product_image'):
        return None
    url = reverse('product-asset', kwargs={'product_id': product.product_id, 'asset': asset})
    request = serializer.context.get('request')
    return request.build_absolute_uri(url) if request else url


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
    product_image = serializers.SerializerMethodField()
    qr_code_image = serializers.SerializerMethodField()
    source_batches = ProductSourceBatchSerializer(
        source='input_batches',
        many=True,
        read_only=True,
    )
    manufacturing = ProductManufacturingSerializer(
        source='manufacturing_record',
        read_only=True,
    )

    class Meta:
        model = Product
        fields = '__all__'

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_product_image(self, obj) -> str | None:
        return _product_asset_url(self, obj, 'image')

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_qr_code_image(self, obj) -> str | None:
        return _product_asset_url(self, obj, 'qr')
