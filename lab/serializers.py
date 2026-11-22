from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from users.validators import validate_document_upload
from .models import LabProfile, LabTest



class LabTestCreateSerializer(serializers.Serializer):
    batch_id = serializers.CharField()
    laboratory_id = serializers.UUIDField()
    test_type = serializers.CharField(max_length=255)
    test_date = serializers.DateField()
    test_parameters = serializers.JSONField(required=False, default=dict)


class LabTestResultSerializer(serializers.Serializer):
    test_id = serializers.UUIDField()
    test_parameters = serializers.JSONField(required=False)
    test_result = serializers.CharField(required=False, allow_blank=True)
    result_summary = serializers.CharField(required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)
    certificate_file = serializers.FileField(
        required=False,
        allow_null=True,
        validators=[validate_document_upload],
    )


class LabTestActionSerializer(serializers.Serializer):
    test_id = serializers.UUIDField()
    remarks = serializers.CharField(required=False, allow_blank=True)


class LabTestSerializer(serializers.ModelSerializer):
    certificate_file = serializers.FileField(write_only=True, required=False, allow_null=True)
    certificate_available = serializers.SerializerMethodField()

    @extend_schema_field(serializers.BooleanField())
    def get_certificate_available(self, obj) -> bool:
        return bool(obj.certificate_file)

    class Meta:
        model = LabTest
        fields = '__all__'


class LabProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabProfile
        fields = '__all__'
        read_only_fields = (
            'lab_id',
            'user',
            'organization',
            'verification_status',
            'created_at',
            'updated_at',
        )
