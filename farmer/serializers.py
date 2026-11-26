from decimal import Decimal

from rest_framework import serializers

from .models import FarmerProfile, FieldEvidence, HerbBatch
from users.validators import validate_document_upload


class FieldEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldEvidence
        fields = (
            'evidence_id',
            'kind',
            'file',
            'label',
            'captured_at',
            'latitude',
            'longitude',
            'created_at',
        )
        read_only_fields = fields


class FieldEvidenceUploadSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=FieldEvidence.Kind.choices)
    file = serializers.FileField(validators=[validate_document_upload])
    label = serializers.CharField(max_length=255, required=False, allow_blank=True)
    captured_at = serializers.DateTimeField(required=False, allow_null=True)
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
    )

    def validate_file(self, value):
        if self.initial_data.get('kind') == FieldEvidence.Kind.PHOTO:
            from users.validators import validate_image_upload

            validate_image_upload(value)
            try:
                from PIL import Image

                with Image.open(value) as image:
                    image.verify()
            except OSError as exc:
                raise serializers.ValidationError(
                    'The uploaded file is not a valid image.'
                ) from exc
            finally:
                value.seek(0)
        return value

    def validate(self, attrs):
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                'Latitude and longitude must be provided together.'
            )
        if latitude is not None and not Decimal('-90') <= latitude <= Decimal('90'):
            raise serializers.ValidationError({'latitude': 'Latitude must be between -90 and 90.'})
        if longitude is not None and not Decimal('-180') <= longitude <= Decimal('180'):
            raise serializers.ValidationError({'longitude': 'Longitude must be between -180 and 180.'})
        return attrs


class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        exclude = ('organization',)
        read_only_fields = (
            'farmer_id',
            'user',
            'verification_status',
            'created_at',
            'updated_at',
        )


class HerbBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = HerbBatch
        exclude = ('organization',)
        read_only_fields = (
            'batch_id',
            'farmer',
            'current_owner',
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
