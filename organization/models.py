import uuid

from django.db import models
from users.validators import validate_document_upload


class Organization(models.Model):
    class OrganizationType(models.TextChoices):
        FARMER_GROUP = 'FARMER_GROUP', 'Farmer group'
        COLLECTOR = 'COLLECTOR', 'Collector'
        TESTING_LAB = 'TESTING_LAB', 'Testing laboratory'
        MANUFACTURER = 'MANUFACTURER', 'Manufacturer'
        OTHER = 'OTHER', 'Other'

    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    organization_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    organization_name = models.CharField(max_length=255)
    organization_type = models.CharField(max_length=30, choices=OrganizationType.choices)
    registration_number = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    pincode = models.CharField(max_length=20)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    verification_document = models.FileField(
        upload_to='organizations/',
        blank=True,
        null=True,
        validators=[validate_document_upload],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('organization_name',)
        indexes = [
            models.Index(
                fields=['organization_name', 'verification_status'],
                name='organizatio_organiz_0da110_idx',
            )
        ]

    def __str__(self):
        return self.organization_name


class BlockchainEvent(models.Model):
    blockchain_event_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    event_type = models.CharField(max_length=100)
    transaction_hash = models.CharField(max_length=255, blank=True, null=True)
    block_number = models.PositiveBigIntegerField(blank=True, null=True)
    network_name = models.CharField(max_length=100, blank=True, null=True)
    contract_address = models.CharField(max_length=255, blank=True, null=True)
    data_hash = models.CharField(max_length=255, blank=True, null=True)
    transaction_status = models.CharField(max_length=50, blank=True, null=True)
    recorded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
