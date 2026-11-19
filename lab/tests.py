from django.test import TestCase
from rest_framework.test import APIClient

from farmer.models import FarmerProfile, HerbBatch
from organization.models import Organization
from users.models import User

from .models import LabProfile, LabTest


class LabWorkflowTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(
            organization_name='Lab',
            organization_type='TESTING_LAB',
            registration_number='LAB-TEST',
            email='lab@example.com',
            phone_number='123',
            address='Address',
            state='State',
            district='District',
            pincode='123456',
        )
        lab_user = User.objects.create_user(
            email='lab@example.com', password='StrongPass123',
            name='Lab', role='LAB', organization=org, is_email_verified=True,
        )
        self.lab_profile = LabProfile.objects.create(
            user=lab_user, organization=org, laboratory_name='Lab',
            registration_number='LAB-TEST', address='Address', contact_number='123',
        )
        farmer_user = User.objects.create_user(
            email='farmer@example.com', password='StrongPass123',
            name='Farmer', role='FARMER', organization=org, is_email_verified=True,
        )
        farmer_profile = FarmerProfile.objects.create(
            user=farmer_user, organization=org, farmer_name='Farmer',
            phone_number='123', address='Address', village='Village',
            district='District', state='State', pincode='123456',
        )
        self.batch = HerbBatch.objects.create(
            batch_id='ASH-2026-00003', herb_name='Ashwagandha',
            botanical_name='Withania somnifera', quantity=10,
            unit='kg', available_quantity=10, source_type='CULTIVATED',
            collection_date='2026-11-19', collection_time='10:30',
            collection_address='Farm', village='Village', district='District',
            state='State', farmer=farmer_profile, current_owner=lab_user,
            organization=org,
        )
        self.test = LabTest.objects.create(
            batch=self.batch, laboratory=self.lab_profile, submitted_by=lab_user,
            test_date='2026-11-19', test_type='Purity',
        )
        self.client = APIClient()
        self.client.force_authenticate(lab_user)

    def test_reject_marks_batch_rejected(self):
        response = self.client.post('/api/labs/reject-test/', {
            'test_id': str(self.test.test_id),
            'remarks': 'Contaminated',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, 'REJECTED')
