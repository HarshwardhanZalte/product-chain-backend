import secrets
import uuid

from django.db import models

from factory.models import FactoryProfile, ManufacturingRecord
from farmer.models import HerbBatch
from users.validators import validate_image_upload


def generate_qr_reference():
    return secrets.token_urlsafe(24)


class Product(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        HOLD = 'HOLD', 'Hold'
        REJECTED = 'REJECTED', 'Rejected'
        COMPLETED = 'COMPLETED', 'Completed'

    product_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    product_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    product_type = models.CharField(max_length=100)
    manufacturer = models.ForeignKey(
        FactoryProfile,
        on_delete=models.PROTECT,
        related_name='products',
    )
    manufacturing_record = models.ForeignKey(
        ManufacturingRecord,
        on_delete=models.PROTECT,
        related_name='products',
    )
    manufacture_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    batch_number = models.CharField(max_length=100, unique=True)
    total_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=20)
    product_image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        validators=[validate_image_upload],
    )
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_reference = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        default=generate_qr_reference,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    blockchain_transaction_hash = models.CharField(max_length=255, blank=True, null=True)
    blockchain_data_hash = models.CharField(max_length=255, blank=True, null=True)
    blockchain_status = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.CheckConstraint(condition=models.Q(total_quantity__gt=0), name='product_quantity_positive'),
        ]


class ProductBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='input_batches')
    herb_batch = models.ForeignKey(HerbBatch, on_delete=models.PROTECT, related_name='product_links')
    quantity_used = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'herb_batch')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_used__gt=0),
                name='product_batch_quantity_positive',
            ),
        ]
