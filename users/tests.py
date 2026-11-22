from django.test import TestCase
from django.test import override_settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from farmer.models import HerbBatch
from organization.models import Organization

from .models import EmailOTP, User


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.organization = Organization.objects.create(
            organization_name='Test Farmer Group',
            organization_type='FARMER_GROUP',
            registration_number='ORG-001',
            email='org@example.com',
            phone_number='1234567890',
            address='Test address',
            state='State',
            district='District',
            pincode='123456',
        )

    def test_registration_and_email_verification(self):
        registration_data = {
            'name': 'Test Farmer',
            'email': 'farmer@example.com',
            'phone_number': '1234567890',
            'password': 'StrongPass123',
            'role': 'FARMER',
            'organization': self.organization.pk,
        }
        rejected = self.client.post('/api/auth/register/', registration_data, format='json')
        self.assertEqual(rejected.status_code, 400)
        registration_data.pop('organization')
        response = self.client.post('/api/auth/register/', registration_data, format='json')
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='farmer@example.com')
        self.assertIsNone(user.organization_id)
        self.assertFalse(user.is_email_verified)
        otp = EmailOTP.objects.filter(user=user).latest('created_at')
        response = self.client.post('/api/auth/verify-otp/', {
            'email': user.email,
            'otp': '000000',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])
        response = self.client.post('/api/auth/login/', {
            'email': user.email,
            'password': 'StrongPass123',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json()['tokens'])

    @override_settings(DEBUG=True)
    def test_default_otp_verifies_email_in_debug(self):
        user = User.objects.create_user(
            email='default-otp@example.com',
            password='StrongPass123',
            name='Default OTP User',
            role='FARMER',
            organization=self.organization,
            is_email_verified=False,
        )

        response = self.client.post(
            '/api/auth/verify-otp/',
            {'email': user.email,             'otp': '098765'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    @override_settings(DEBUG=True)
    def test_default_otp_can_reset_password_in_debug(self):
        user = User.objects.create_user(
            email='debug-reset@example.com',
            password='StrongPass123',
            name='Debug Reset User',
            role='FARMER',
            organization=self.organization,
            is_email_verified=True,
        )
        response = self.client.post('/api/auth/reset-password/', {
            'email': user.email,
            'otp': '098765',
            'new_password': 'DifferentStrongPass456!',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password('DifferentStrongPass456!'))

    @override_settings(DEBUG=False)
    def test_default_otp_is_rejected_outside_debug(self):
        user = User.objects.create_user(
            email='production-otp@example.com',
            password='StrongPass123',
            name='Production OTP User',
            role='FARMER',
            organization=self.organization,
            is_email_verified=False,
        )
        response = self.client.post(
            '/api/auth/verify-otp/',
            {'email': user.email, 'otp': '098765'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)

        EmailOTP.objects.create(
            user=user,
            purpose=EmailOTP.Purpose.VERIFY_EMAIL,
            otp_hash=EmailOTP.hash_otp('123456'),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            resend_available_at=timezone.now(),
        )
        universal = self.client.post(
            '/api/auth/verify-otp/',
            {'email': user.email, 'otp': '098765'},
            format='json',
        )
        self.assertEqual(universal.status_code, 400)
        valid = self.client.post(
            '/api/auth/verify-otp/',
            {'email': user.email, 'otp': '123456'},
            format='json',
        )
        self.assertEqual(valid.status_code, 200)

    @override_settings(DEBUG=False)
    def test_seed_command_is_disabled_outside_debug(self):
        with self.assertRaises(CommandError):
            call_command('seed_test_data')

    @override_settings(DEBUG=True)
    def test_seed_command_creates_consistent_traceability_data_in_debug(self):
        call_command('seed_test_data')
        batch = HerbBatch.objects.get(batch_id='ASH-2026-00001')
        self.assertEqual(batch.status, HerbBatch.Status.CONSUMED)
        self.assertEqual(batch.available_quantity, 0)
        self.assertEqual(
            batch.transfers.filter(status='ACCEPTED').count(),
            2,
        )

    def test_generated_random_otp_also_verifies_email(self):
        user = User.objects.create_user(
            email='random-otp@example.com',
            password='StrongPass123',
            name='Random OTP User',
            role='FARMER',
            organization=self.organization,
            is_email_verified=False,
        )
        EmailOTP.objects.create(
            user=user,
            purpose=EmailOTP.Purpose.VERIFY_EMAIL,
            otp_hash=EmailOTP.hash_otp('123456'),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            resend_available_at=timezone.now(),
        )

        response = self.client.post(
            '/api/auth/verify-otp/',
            {'email': user.email, 'otp': '123456'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_resend_otp_requires_unverified_account_and_returns_cooldown(self):
        user = User.objects.create_user(
            email='resend@example.com',
            password='StrongPass123',
            name='Resend User',
            role='FARMER',
            organization=self.organization,
            is_email_verified=False,
        )

        first = self.client.post(
            '/api/auth/resend-otp/',
            {'email': user.email},
            format='json',
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(
            EmailOTP.objects.filter(
                user=user,
                purpose=EmailOTP.Purpose.VERIFY_EMAIL,
                used_at__isnull=True,
            ).count(),
            1,
        )

        cooldown = self.client.post(
            '/api/auth/resend-otp/',
            {'email': user.email},
            format='json',
        )
        self.assertEqual(cooldown.status_code, 429)

        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])
        verified = self.client.post(
            '/api/auth/resend-otp/',
            {'email': user.email},
            format='json',
        )
        self.assertEqual(verified.status_code, 400)
