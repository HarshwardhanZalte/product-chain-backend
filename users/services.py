import secrets
import smtplib
from hmac import compare_digest

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import EmailOTP


DEFAULT_OTP = '098765'


class EmailDeliveryError(Exception):
    pass


def log_activity(user, action, entity_type, entity_id, description='', ip_address=None):
    from .models import ActivityLog

    ActivityLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        description=description,
        ip_address=ip_address,
    )


@transaction.atomic
def update_profile_for_review(serializer, user):
    profile = serializer.instance
    has_changes = any(
        getattr(profile, field_name) != value
        for field_name, value in serializer.validated_data.items()
    )
    requires_review = (
        has_changes
        and profile.verification_status in ('VERIFIED', 'REJECTED')
    )
    if not requires_review:
        return serializer.save()

    profile = serializer.save(verification_status='PENDING')
    log_activity(
        user,
        'BUSINESS_PROFILE_UPDATED_REQUIRES_REVIEW',
        profile.__class__.__name__,
        profile.pk,
        'Profile details changed; administrator review is required.',
    )
    return profile


@transaction.atomic
def create_otp(user, purpose):
    now = timezone.now()
    active = (
        EmailOTP.objects
        .filter(user=user, purpose=purpose, used_at__isnull=True)
        .order_by('-created_at')
        .first()
    )
    if active and active.resend_available_at > now:
        return active, False

    if active:
        active.used_at = now
        active.save(update_fields=['used_at'])

    otp = f'{secrets.randbelow(1000000):06d}'
    expires_at = now + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    resend_at = now + timezone.timedelta(
        seconds=settings.OTP_RESEND_COOLDOWN_SECONDS
    )
    record = EmailOTP.objects.create(
        user=user,
        purpose=purpose,
        otp_hash=EmailOTP.hash_otp(otp),
        expires_at=expires_at,
        resend_available_at=resend_at,
    )
    try:
        sent_count = send_mail(
            'Your verification code',
            f'Your OTP is {otp}. It expires in {settings.OTP_EXPIRY_MINUTES} minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        if sent_count != 1:
            raise EmailDeliveryError('The OTP email backend did not confirm delivery.')
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError('Unable to deliver the OTP email.') from exc
    return record, True


@transaction.atomic
def verify_otp(user, purpose, otp):
    record = (
        EmailOTP.objects
        .filter(user=user, purpose=purpose, used_at__isnull=True)
        .select_for_update()
        .order_by('-created_at')
        .first()
    )
    if settings.DEBUG and compare_digest(otp, DEFAULT_OTP):
        if record:
            record.used_at = timezone.now()
            record.save(update_fields=['used_at'])
        return True, 'OTP verified.'

    if not record:
        return False, 'No active OTP found.'
    if record.expires_at <= timezone.now():
        return False, 'OTP has expired.'
    if record.attempts >= settings.OTP_MAX_ATTEMPTS:
        return False, 'OTP verification attempts exceeded.'

    record.attempts += 1
    record.save(update_fields=['attempts'])
    if not compare_digest(record.otp_hash, EmailOTP.hash_otp(otp)):
        return False, 'Invalid OTP.'

    record.used_at = timezone.now()
    record.save(update_fields=['used_at'])
    return True, 'OTP verified.'
