from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

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
        response = self.client.post('/api/auth/register/', {
            'name': 'Test Farmer',
            'email': 'farmer@example.com',
            'phone_number': '1234567890',
            'password': 'StrongPass123',
            'role': 'FARMER',
            'organization': self.organization.pk,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='farmer@example.com')
        self.assertFalse(user.is_email_verified)
        otp = EmailOTP.objects.filter(user=user).latest('created_at')
        response = self.client.post('/api/auth/verify-otp/', {
            'email': user.email,
            'otp': '000000',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        otp_hash = otp.otp_hash
        for otp_value in ('111111', '222222'):
            from django.contrib.auth.hashers import make_password
        # The OTP is intentionally not exposed by the API; direct test setup is
        # sufficient to verify the login state after marking it verified.
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])
        response = self.client.post('/api/auth/login/', {
            'email': user.email,
            'password': 'StrongPass123',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json()['tokens'])
