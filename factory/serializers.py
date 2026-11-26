from rest_framework import serializers
from .models import FactoryProfile, ManufacturingBatch

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
    facility_line = serializers.CharField(max_length=255, required=False, allow_blank=True)
    shift = serializers.CharField(max_length=100, required=False, allow_blank=True)
    standard_operating_procedure = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    solvent_method = serializers.CharField(max_length=255, required=False, allow_blank=True)
    target_yield_ratio = serializers.CharField(max_length=50, required=False, allow_blank=True)
    process_parameters = serializers.JSONField(required=False, default=dict)
    quality_control_lead = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    save_as_draft = serializers.BooleanField(required=False, default=False)
    input_batches = ManufacturingBatchInputSerializer(many=True)

    def validate_input_batches(self, value):
        batch_ids = [item['batch_id'] for item in value]
        if len(batch_ids) != len(set(batch_ids)):
            raise serializers.ValidationError('A batch may only be listed once per manufacturing record.')
        return value

    def validate_output_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Output quantity must be greater than zero.'
            )
        return value


class ManufacturingInputBatchSerializer(serializers.ModelSerializer):
    batch_id = serializers.CharField(source='herb_batch.batch_id', read_only=True)
    herb_name = serializers.CharField(source='herb_batch.herb_name', read_only=True)
    botanical_name = serializers.CharField(
        source='herb_batch.botanical_name',
        read_only=True,
    )
    available_quantity = serializers.DecimalField(
        source='herb_batch.available_quantity',
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    class Meta:
        model = ManufacturingBatch
        fields = (
            'batch_id',
            'herb_name',
            'botanical_name',
            'quantity_used',
            'unit',
            'available_quantity',
        )


class ManufacturingRecordSerializer(serializers.ModelSerializer):
    input_batches = ManufacturingInputBatchSerializer(many=True, read_only=True)

    class Meta:
        model = ManufacturingRecord
        fields = '__all__'


class ReceiveBatchSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    remarks = serializers.CharField(required=False, allow_blank=True)


class ManufacturingActionSerializer(serializers.Serializer):
    manufacturing_id = serializers.UUIDField()


class FactoryProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FactoryProfile
        exclude = ('organization',)
        read_only_fields = (
            'factory_id',
            'user',
            'verification_status',
            'created_at',
            'updated_at',
        )
