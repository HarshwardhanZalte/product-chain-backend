import uuid

from django.conf import settings
from django.db import models

from farmer.models import HerbBatch
from organization.models import Organization


class CollectorProfile(models.Model):
    collector_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collector_profile',
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name='collectors',
    )
    collector_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    verification_status = models.CharField(default='PENDING', max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TransferEvent(models.Model):
    class Status(models.TextChoices):
        INITIATED = 'INITIATED', 'Initiated'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    event_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    batch = models.ForeignKey(HerbBatch, on_delete=models.PROTECT, related_name='transfers')
    from_party = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='outgoing_transfers',
    )
    to_party = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='incoming_transfers',
    )
    from_organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name='outgoing_transfers',
    )
    to_organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name='incoming_transfers',
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    transfer_date = models.DateField()
    transfer_location = models.CharField(max_length=255)
    remarks = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INITIATED,
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='recorded_transfers',
    )
    blockchain_transaction_hash = models.CharField(max_length=255, blank=True, null=True)
    blockchain_data_hash = models.CharField(max_length=255, blank=True, null=True)
    blockchain_status = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='transfer_quantity_positive'),
        ]
