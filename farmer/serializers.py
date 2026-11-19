from rest_framework import serializers

from .models import FarmerProfile, HerbBatch


class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = '__all__'
        read_only_fields = (
            'farmer_id',
            'user',
            'organization',
            'verification_status',
            'created_at',
            'updated_at',
        )


class HerbBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = HerbBatch
        fields = '__all__'
        read_only_fields = (
            'batch_id',
            'farmer',
            'current_owner',
            'organization',
            'available_quantity',
            'status',
            'blockchain_record_id',
            'blockchain_transaction_hash',
            'blockchain_data_hash',
            'blockchain_status',
            'created_at',
            'updated_at',
        )

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Quantity must be greater than zero.')
        return value
