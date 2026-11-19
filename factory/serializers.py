from rest_framework import serializers
from .models import FactoryProfile

from .models import ManufacturingRecord


class ManufacturingBatchInputSerializer(serializers.Serializer):
    batch_id = serializers.CharField()
    quantity_used = serializers.DecimalField(max_digits=12, decimal_places=3)

    def validate_quantity_used(self, value):
        if value <= 0:
            raise serializers.ValidationError('Quantity used must be greater than zero.')
        return value


class ManufacturingCreateSerializer(serializers.Serializer):
    product_name = serializers.CharField(max_length=255)
    process_date = serializers.DateField()
    process_description = serializers.CharField()
    output_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit = serializers.CharField(max_length=20)
    remarks = serializers.CharField(required=False, allow_blank=True)
    input_batches = ManufacturingBatchInputSerializer(many=True)


class ManufacturingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManufacturingRecord
        fields = '__all__'


class ReceiveBatchSerializer(serializers.Serializer):
    batch_id = serializers.CharField()


class FactoryProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FactoryProfile
        fields = '__all__'
        read_only_fields = (
            'factory_id',
            'user',
            'organization',
            'created_at',
            'updated_at',
        )
