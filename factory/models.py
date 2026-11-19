import uuid

from django.conf import settings
from django.db import models

from farmer.models import HerbBatch
from organization.models import Organization


class FactoryProfile(models.Model):
    factory_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='factory_profile',
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name='factories',
    )
    factory_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    contact_number = models.CharField(max_length=20)
    verification_status = models.CharField(default='PENDING', max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ManufacturingRecord(models.Model):
    class Status(models.TextChoices):
        PLANNED = 'PLANNED', 'Planned'
        IN_PROGRESS = 'IN_PROGRESS', 'In progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    manufacturing_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    factory = models.ForeignKey(
        FactoryProfile,
        on_delete=models.PROTECT,
        related_name='manufacturing_records',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='manufacturing_records',
    )
    product_name = models.CharField(max_length=255)
    process_date = models.DateField()
    process_description = models.TextField()
    input_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    output_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    remarks = models.TextField(blank=True)
    blockchain_transaction_hash = models.CharField(max_length=255, blank=True, null=True)
    blockchain_data_hash = models.CharField(max_length=255, blank=True, null=True)
    blockchain_status = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(input_quantity__gt=0), name='manufacturing_input_positive'),
            models.CheckConstraint(condition=models.Q(output_quantity__gte=0), name='manufacturing_output_nonnegative'),
        ]


class ManufacturingBatch(models.Model):
    manufacturing_record = models.ForeignKey(
        ManufacturingRecord,
        on_delete=models.CASCADE,
        related_name='input_batches',
    )
    herb_batch = models.ForeignKey(HerbBatch, on_delete=models.PROTECT, related_name='manufacturing_links')
    quantity_used = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('manufacturing_record', 'herb_batch')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_used__gt=0),
                name='manufacturing_batch_quantity_positive',
            ),
        ]
