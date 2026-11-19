from django.test import TestCase
from rest_framework.test import APIClient

from farmer.models import FarmerProfile, HerbBatch
from organization.models import Organization
from users.models import User

from .models import FactoryProfile


class ManufacturingTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Factory',
            organization_type='MANUFACTURER',
            registration_number='FAC-TEST',
            email='factory@example.com',
            phone_number='123',
            address='Address',
            state='State',
            district='District',
            pincode='123456',
        )
        self.factory_user = User.objects.create_user(
            email='factory@example.com', password='StrongPass123',
            name='Factory', role='FACTORY', organization=self.organization,
            is_email_verified=True,
        )
        self.profile = FactoryProfile.objects.create(
            user=self.factory_user, organization=self.organization,
            factory_name='Factory', registration_number='FAC-TEST',
            address='Address', contact_number='123',
        )
        farmer_user = User.objects.create_user(
            email='farmer@example.com', password='StrongPass123',
            name='Farmer', role='FARMER', organization=self.organization,
            is_email_verified=True,
        )
        farmer_profile = FarmerProfile.objects.create(
            user=farmer_user, organization=self.organization, farmer_name='Farmer',
            phone_number='123', address='Address', village='Village',
            district='District', state='State', pincode='123456',
        )
        self.batch = HerbBatch.objects.create(
            batch_id='ASH-2026-00002', herb_name='Ashwagandha',
            botanical_name='Withania somnifera', quantity=10,
            unit='kg', available_quantity=10, source_type='CULTIVATED',
            collection_date='2026-11-19', collection_time='10:30',
            collection_address='Farm', village='Village', district='District',
            state='State', farmer=farmer_profile, current_owner=self.factory_user,
            organization=self.organization, status='APPROVED',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.factory_user)

    def test_rejects_quantity_above_available(self):
        response = self.client.post('/api/factories/manufacturing/create/', {
            'product_name': 'Herb Powder',
            'process_date': '2026-11-19',
            'process_description': 'Powder processing',
            'output_quantity': '8.000',
            'unit': 'kg',
            'input_batches': [{'batch_id': self.batch.batch_id, 'quantity_used': '11.000'}],
        }, format='json')
        self.assertEqual(response.status_code, 400)
