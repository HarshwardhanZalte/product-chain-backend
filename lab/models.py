import uuid

from django.conf import settings
from django.db import models

from farmer.models import HerbBatch
from organization.models import Organization
from users.validators import validate_document_upload


class LabProfile(models.Model):
    lab_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lab_profile',
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        related_name='labs',
        blank=True,
        null=True,
    )
    laboratory_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    contact_number = models.CharField(max_length=20)
    verification_status = models.CharField(default='PENDING', max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LabTest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        UNDER_TESTING = 'UNDER_TESTING', 'Under testing'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        NEEDS_REVIEW = 'NEEDS_REVIEW', 'Needs review'

    test_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    batch = models.ForeignKey(HerbBatch, on_delete=models.PROTECT, related_name='laboratory_tests')
    laboratory = models.ForeignKey(LabProfile, on_delete=models.PROTECT, related_name='tests')
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='submitted_lab_tests',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reviewed_lab_tests',
        blank=True,
        null=True,
    )
    test_date = models.DateField()
    test_type = models.CharField(max_length=255)
    test_parameters = models.JSONField(default=dict, blank=True)
    test_result = models.TextField(blank=True)
    result_summary = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    certificate_file = models.FileField(
        upload_to='lab_certificates/',
        blank=True,
        null=True,
        validators=[validate_document_upload],
    )
    certificate_hash = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    blockchain_transaction_hash = models.CharField(max_length=255, blank=True, null=True)
    blockchain_data_hash = models.CharField(max_length=255, blank=True, null=True)
    blockchain_status = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)


class LabMeasurement(models.Model):
    class Verdict(models.TextChoices):
        PASS = 'PASS', 'Pass'
        FAIL = 'FAIL', 'Fail'
        INCONCLUSIVE = 'INCONCLUSIVE', 'Inconclusive'

    measurement_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    test = models.ForeignKey(
        LabTest,
        on_delete=models.CASCADE,
        related_name='measurements',
    )
    analyte = models.CharField(max_length=255)
    method = models.CharField(max_length=255, blank=True)
    result_value = models.CharField(max_length=255)
    numeric_value = models.DecimalField(
        max_digits=16,
        decimal_places=6,
        blank=True,
        null=True,
    )
    unit = models.CharField(max_length=50, blank=True)
    threshold = models.CharField(max_length=255, blank=True)
    verdict = models.CharField(max_length=20, choices=Verdict.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('measurement_id',)
