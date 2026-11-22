from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User


class OrganizationOnboardingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='StrongPass123',
            name='Organization Owner',
            role='FARMER',
            is_email_verified=True,
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='StrongPass123',
            name='Other Farmer',
            role='FARMER',
            is_email_verified=True,
        )
        self.client = APIClient()

    def test_creation_assigns_only_the_authenticated_user_and_hides_document(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post('/api/organizations/create/', {
            'organization_name': 'Owner Cooperative',
            'organization_type': 'FARMER_GROUP',
            'registration_number': 'OWNER-ORG-001',
            'email': 'cooperative@example.com',
            'phone_number': '1234567890',
            'address': 'Farm Road',
            'state': 'State',
            'district': 'District',
            'pincode': '123456',
            'verification_status': 'VERIFIED',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('verification_document', response.json())
        self.owner.refresh_from_db()
        self.assertIsNotNone(self.owner.organization_id)
        self.assertEqual(self.owner.organization.verification_status, 'PENDING')

        self.client.force_authenticate(self.other_user)
        detail = self.client.get(
            f"/api/organizations/detail/{response.json()['organization_id']}/"
        )
        self.assertEqual(detail.status_code, 404)

    def test_organization_type_must_match_account_role(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post('/api/organizations/create/', {
            'organization_name': 'Wrong Type',
            'organization_type': 'MANUFACTURER',
            'registration_number': 'OWNER-ORG-002',
            'email': 'wrong@example.com',
            'phone_number': '1234567890',
            'address': 'Address',
            'state': 'State',
            'district': 'District',
            'pincode': '123456',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.owner.refresh_from_db()
        self.assertIsNone(self.owner.organization_id)
