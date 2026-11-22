from django.test import TestCase
from rest_framework.test import APIClient

from organization.models import Organization
from users.models import User

from .models import FarmerProfile, HerbBatch


class FarmerBatchTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Farmers',
            organization_type='FARMER_GROUP',
            registration_number='FARM-001',
            email='farm@example.com',
            phone_number='123',
            address='Address',
            state='State',
            district='District',
            pincode='123456',
            verification_status='VERIFIED',
        )
        self.user = User.objects.create_user(
            email='farmer@example.com',
            password='StrongPass123',
            name='Farmer',
            role='FARMER',
            organization=self.organization,
            is_email_verified=True,
        )
        self.profile = FarmerProfile.objects.create(
            user=self.user,
            organization=self.organization,
            farmer_name='Farmer',
            phone_number='123',
            address='Address',
            village='Village',
            district='District',
            state='State',
            pincode='123456',
            verification_status='VERIFIED',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_register_batch_and_unique_id(self):
        response = self.client.post('/api/farmers/batches/register/', {
            'herb_name': 'Ashwagandha',
            'botanical_name': 'Withania somnifera',
            'quantity': '10.000',
            'unit': 'kg',
            'source_type': 'CULTIVATED',
            'collection_date': '2026-11-19',
            'collection_time': '10:30:00',
            'collection_address': 'Farm',
            'village': 'Village',
            'district': 'District',
            'state': 'State',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        batch = HerbBatch.objects.get(batch_id=response.json()['batch_id'])
        self.assertEqual(batch.available_quantity, batch.quantity)
        self.assertTrue(batch.batch_id.startswith('ASH-'))

    def test_batch_registration_requires_approved_organization_and_profile(self):
        response_data = {
            'herb_name': 'Ashwagandha',
            'botanical_name': 'Withania somnifera',
            'quantity': '10.000',
            'unit': 'kg',
            'source_type': 'CULTIVATED',
            'collection_date': '2026-11-19',
            'collection_time': '10:30:00',
            'collection_address': 'Farm',
            'village': 'Village',
            'district': 'District',
            'state': 'State',
        }
        self.profile.verification_status = 'PENDING'
        self.profile.save(update_fields=['verification_status'])
        profile_pending = self.client.post(
            '/api/farmers/batches/register/',
            response_data,
            format='json',
        )
        self.assertEqual(profile_pending.status_code, 403)

        self.profile.verification_status = 'VERIFIED'
        self.profile.save(update_fields=['verification_status'])
        self.organization.verification_status = 'PENDING'
        self.organization.save(update_fields=['verification_status'])
        organization_pending = self.client.post(
            '/api/farmers/batches/register/',
            response_data,
            format='json',
        )
        self.assertEqual(organization_pending.status_code, 403)
