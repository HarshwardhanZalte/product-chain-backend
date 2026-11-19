from django.contrib.auth import get_user_model
from rest_framework import serializers

from farmer.models import HerbBatch
from .models import CollectorProfile

from .models import TransferEvent


class TransferCreateSerializer(serializers.Serializer):
    batch_id = serializers.CharField()
    to_party = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    transfer_location = serializers.CharField(max_length=255)
    remarks = serializers.CharField(required=False, allow_blank=True)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Quantity must be greater than zero.')
        return value

    def validate(self, attrs):
        try:
            batch = HerbBatch.objects.get(batch_id=attrs['batch_id'])
        except HerbBatch.DoesNotExist:
            raise serializers.ValidationError({'batch_id': 'Batch not found.'})
        if attrs['quantity'] > batch.available_quantity:
            raise serializers.ValidationError({'quantity': 'Quantity exceeds available quantity.'})
        attrs['batch'] = batch
        return attrs


class TransferActionSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    remarks = serializers.CharField(required=False, allow_blank=True)


class TransferEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransferEvent
        fields = '__all__'


class CollectorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectorProfile
        fields = '__all__'
        read_only_fields = (
            'collector_id',
            'user',
            'organization',
            'created_at',
            'updated_at',
        )
