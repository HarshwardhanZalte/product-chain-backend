from rest_framework import serializers
from users.validators import validate_document_upload

from .models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    verification_document = serializers.FileField(
        required=False,
        allow_null=True,
        write_only=True,
        validators=[validate_document_upload],
    )

    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = (
            'organization_id',
            'verification_status',
            'created_at',
            'updated_at',
        )
