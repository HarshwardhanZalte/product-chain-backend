from rest_framework import serializers

from .models import LabTest


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
    certificate_file = serializers.FileField(required=False)


class LabTestActionSerializer(serializers.Serializer):
    test_id = serializers.UUIDField()
    remarks = serializers.CharField(required=False, allow_blank=True)


class LabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = '__all__'
