from django.test import TestCase
from rest_framework.test import APIClient

from collector.models import CollectorProfile
from users.models import User


class OrganizationRemovalTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='StrongPass123',
            name='Organization Owner',
            role='FARMER',
            is_email_verified=True,
        )
        self.client = APIClient()

    def test_organization_api_is_removed(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post('/api/organizations/create/', {}, format='json')
        self.assertEqual(response.status_code, 404)
        self.assertIsNone(self.owner.organization_id)

    def test_participant_directory_lists_verified_profiles_without_organizations(self):
        collector = User.objects.create_user(
            email='verified-collector@example.com',
            password='StrongPass123',
            name='Verified Collector',
            role='COLLECTOR',
            is_email_verified=True,
        )
        profile = CollectorProfile.objects.create(
            user=collector,
            collector_name='Collector Profile',
            phone_number='1234567890',
            address='Depot',
            verification_status='VERIFIED',
        )
        unverified = User.objects.create_user(
            email='unverified-collector@example.com',
            password='StrongPass123',
            name='Unverified Collector',
            role='COLLECTOR',
            is_email_verified=True,
        )
        CollectorProfile.objects.create(
            user=unverified,
            collector_name='Unverified Profile',
            phone_number='1234567890',
            address='Depot',
            verification_status='PENDING',
        )

        self.client.force_authenticate(self.owner)
        response = self.client.get(
            '/api/participants/?role=COLLECTOR&search=Verified'
        )

        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], collector.pk)
        self.assertEqual(results[0]['user_id'], str(collector.user_id))
        self.assertEqual(results[0]['profile_id'], str(profile.collector_id))
        self.assertNotIn('organization_name', results[0])

    def test_participant_directory_requires_a_supported_role(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get('/api/participants/?role=ADMIN')
        self.assertEqual(response.status_code, 400)
