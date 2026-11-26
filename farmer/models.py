import uuid

from django.conf import settings
from django.db import models

from organization.models import Organization


class FarmerProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    farmer_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='farmer_profile',
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        related_name='farmers',
        blank=True,
        null=True,
    )
    farmer_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    village = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=20)
    land_area = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    land_record_reference = models.CharField(max_length=255, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.farmer_name


class HerbBatch(models.Model):
    class SourceType(models.TextChoices):
        CULTIVATED = 'CULTIVATED', 'Cultivated'
        WILD_COLLECTED = 'WILD_COLLECTED', 'Wild collected'

    class Status(models.TextChoices):
        REGISTERED = 'REGISTERED', 'Registered'
        COLLECTED = 'COLLECTED', 'Collected'
        WITH_COLLECTOR = 'WITH_COLLECTOR', 'With collector'
        SENT_TO_LAB = 'SENT_TO_LAB', 'Sent to lab'
        UNDER_TESTING = 'UNDER_TESTING', 'Under testing'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        ON_HOLD = 'ON_HOLD', 'On hold'
        SENT_TO_FACTORY = 'SENT_TO_FACTORY', 'Sent to factory'
        IN_PROCESSING = 'IN_PROCESSING', 'In processing'
        CONSUMED = 'CONSUMED', 'Consumed'
        COMPLETED = 'COMPLETED', 'Completed'

    batch_id = models.CharField(max_length=30, unique=True, editable=False)
    herb_name = models.CharField(max_length=255)
    botanical_name = models.CharField(max_length=255)
    plant_part = models.CharField(max_length=100, blank=True)
    cultivar = models.CharField(max_length=255, blank=True)
    quality_grade = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    packaging_details = models.CharField(max_length=255, blank=True)
    drying_notes = models.TextField(blank=True)
    gacp_attested = models.BooleanField(default=False)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=20)
    available_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    collection_date = models.DateField()
    collection_time = models.TimeField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    collection_address = models.TextField()
    village = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.PROTECT, related_name='batches')
    current_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_batches',
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        related_name='batches',
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REGISTERED,
    )
    remarks = models.TextField(blank=True)
    blockchain_record_id = models.CharField(max_length=255, blank=True, null=True)
    blockchain_transaction_hash = models.CharField(max_length=255, blank=True, null=True)
    blockchain_data_hash = models.CharField(max_length=255, blank=True, null=True)
    blockchain_status = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['batch_id', 'status'], name='farmer_herb_batch_i_578d68_idx'),
            models.Index(fields=['herb_name', 'district'], name='farmer_herb_herb_na_5f6477_idx'),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name='herb_quantity_nonnegative'),
            models.CheckConstraint(condition=models.Q(available_quantity__gte=0), name='herb_available_nonnegative'),
        ]

    def __str__(self):
        return self.batch_id


class FieldEvidence(models.Model):
    class Kind(models.TextChoices):
        PHOTO = 'PHOTO', 'Field photo'
        DOCUMENT = 'DOCUMENT', 'Supporting document'

    evidence_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    batch = models.ForeignKey(
        HerbBatch,
        on_delete=models.CASCADE,
        related_name='field_evidence',
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    file = models.FileField(upload_to='batch_evidence/')
    label = models.CharField(max_length=255, blank=True)
    captured_at = models.DateTimeField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)

    def __str__(self):
        return f'{self.batch.batch_id} - {self.kind}'
