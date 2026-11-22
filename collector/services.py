from django.db import transaction

from farmer.models import HerbBatch

from .models import TransferEvent


@transaction.atomic
def accept_transfer(event, user, remarks=''):
    batch = HerbBatch.objects.select_for_update().get(pk=event.batch_id)
    allowed_statuses = {
        'FARMER': (
            HerbBatch.Status.REGISTERED,
            HerbBatch.Status.COLLECTED,
            HerbBatch.Status.APPROVED,
        ),
        'COLLECTOR': (
            HerbBatch.Status.WITH_COLLECTOR,
            HerbBatch.Status.APPROVED,
        ),
    }.get(event.from_party.role, ())
    expected_recipient_role = {
        'FARMER': 'COLLECTOR',
        'COLLECTOR': 'FACTORY',
    }.get(event.from_party.role)
    latest_test = (
        batch.laboratory_tests.order_by('-created_at').first()
        if user.role == 'FACTORY'
        else None
    )
    if (
        batch.current_owner_id != event.from_party_id
        or batch.available_quantity != event.quantity
        or event.to_party_id != user.pk
        or user.role != expected_recipient_role
        or batch.status not in allowed_statuses
        or (user.role == 'FACTORY' and (not latest_test or latest_test.status != 'APPROVED'))
    ):
        event.status = TransferEvent.Status.CANCELLED
        event.save(update_fields=['status', 'updated_at'])
        return False

    event.status = TransferEvent.Status.ACCEPTED
    event.remarks = remarks
    event.save(update_fields=['status', 'remarks', 'updated_at'])
    batch.current_owner = user
    batch.status = (
        HerbBatch.Status.WITH_COLLECTOR
        if user.role == 'COLLECTOR'
        else HerbBatch.Status.SENT_TO_FACTORY
    )
    batch.save(update_fields=['current_owner', 'status', 'updated_at'])
    return True
