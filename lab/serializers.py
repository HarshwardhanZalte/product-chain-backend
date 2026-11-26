from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from users.validators import validate_document_upload
from .models import LabMeasurement, LabProfile, LabTest


class LabMeasurementInputSerializer(serializers.Serializer):
    analyte = serializers.CharField(max_length=255)
    method = serializers.CharField(max_length=255, required=False, allow_blank=True)
    result_value = serializers.CharField(max_length=255)
    numeric_value = serializers.DecimalField(
        max_digits=16,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    unit = serializers.CharField(max_length=50, required=False, allow_blank=True)
    threshold = serializers.CharField(max_length=255, required=False, allow_blank=True)
    verdict = serializers.ChoiceField(choices=LabMeasurement.Verdict.choices)


class LabMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabMeasurement
        fields = (
            'measurement_id',
            'analyte',
            'method',
            'result_value',
            'numeric_value',
            'unit',
            'threshold',
            'verdict',
        )
        read_only_fields = fields


class LabTestDetailSerializer(serializers.ModelSerializer):
    measurements = LabMeasurementSerializer(many=True, read_only=True)
    batch_id = serializers.CharField(source='batch.batch_id', read_only=True)
    herb_name = serializers.CharField(source='batch.herb_name', read_only=True)
    botanical_name = serializers.CharField(source='batch.botanical_name', read_only=True)
    laboratory_name = serializers.CharField(
        source='laboratory.laboratory_name',
        read_only=True,
    )
    certificate_available = serializers.SerializerMethodField()

    class Meta:
        model = LabTest
        fields = (
            'test_id',
            'batch_id',
            'herb_name',
            'botanical_name',
            'laboratory',
            'laboratory_name',
            'submitted_by',
            'reviewed_by',
            'test_date',
            'test_type',
            'test_parameters',
            'test_result',
            'result_summary',
            'remarks',
            'certificate_available',
            'certificate_hash',
            'measurements',
            'status',
            'created_at',
            'updated_at',
        )

    @extend_schema_field(serializers.BooleanField())
    def get_certificate_available(self, obj):
        return bool(obj.certificate_file)



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
    measurements = LabMeasurementInputSerializer(many=True, required=False)

    def validate(self, attrs):
        if not (attrs.get('test_result', '').strip() or attrs.get('measurements')):
            raise serializers.ValidationError(
                'Provide a test result or at least one assay measurement.'
            )
        return attrs


class LabTestActionSerializer(serializers.Serializer):
    test_id = serializers.UUIDField()
    remarks = serializers.CharField(required=False, allow_blank=True)


class LabTestSerializer(serializers.ModelSerializer):
    certificate_file = serializers.FileField(write_only=True, required=False, allow_null=True)
    certificate_available = serializers.SerializerMethodField()
    measurements = LabMeasurementSerializer(many=True, read_only=True)

    @extend_schema_field(serializers.BooleanField())
    def get_certificate_available(self, obj) -> bool:
        return bool(obj.certificate_file)

    class Meta:
        model = LabTest
        fields = '__all__'


class LabProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabProfile
        exclude = ('organization',)
        read_only_fields = (
            'lab_id',
            'user',
            'verification_status',
            'created_at',
            'updated_at',
        )
