from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

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
    batch_identifier = serializers.CharField(source='batch.batch_id', read_only=True)
    herb_name = serializers.CharField(source='batch.herb_name', read_only=True)
    botanical_name = serializers.CharField(source='batch.botanical_name', read_only=True)
    unit = serializers.CharField(source='batch.unit', read_only=True)
    from_party_name = serializers.CharField(source='from_party.name', read_only=True)
    to_party_name = serializers.CharField(source='to_party.name', read_only=True)
    class Meta:
        model = TransferEvent
        exclude = ('from_organization', 'to_organization')


class CollectorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectorProfile
        exclude = ('organization',)
        read_only_fields = (
            'collector_id',
            'user',
            'verification_status',
            'created_at',
            'updated_at',
        )


class BusinessParticipantSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    profile_id = serializers.SerializerMethodField()
    profile_name = serializers.SerializerMethodField()
    profile_registration_number = serializers.SerializerMethodField()
    PROFILE_FIELDS = {
        'COLLECTOR': ('collector_profile', 'collector_id', 'collector_name', None),
        'FACTORY': (
            'factory_profile',
            'factory_id',
            'factory_name',
            'registration_number',
        ),
        'LAB': ('lab_profile', 'lab_id', 'laboratory_name', 'registration_number'),
    }

    def _profile_value(self, obj, value_index):
        relation, *fields = self.PROFILE_FIELDS[obj.role]
        profile = getattr(obj, relation)
        field = fields[value_index]
        return getattr(profile, field) if field else None

    @extend_schema_field(serializers.UUIDField())
    def get_profile_id(self, obj):
        return self._profile_value(obj, 0)

    @extend_schema_field(serializers.CharField())
    def get_profile_name(self, obj):
        return self._profile_value(obj, 1)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_profile_registration_number(self, obj):
        return self._profile_value(obj, 2)
