from django.test import TestCase
from rest_framework.test import APIClient

from .models import Product
from factory.models import FactoryProfile, ManufacturingRecord
from organization.models import Organization
from users.models import User


class PublicVerificationTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(
            organization_name='Factory',
            organization_type='MANUFACTURER',
            registration_number='FAC-VERIFY',
            email='factory@example.com',
            phone_number='123',
            address='Address',
            state='State',
            district='District',
            pincode='123456',
        )
        user = User.objects.create_user(
            email='factory@example.com', password='StrongPass123',
            name='Factory', role='FACTORY', organization=org,
            is_email_verified=True,
        )
        factory = FactoryProfile.objects.create(
            user=user, organization=org, factory_name='Factory',
            registration_number='FAC-VERIFY', address='Address', contact_number='123',
        )
        record = ManufacturingRecord.objects.create(
            factory=factory, created_by=user, product_name='Herb Powder',
            process_date='2026-11-19', process_description='Processing',
            input_quantity=10, output_quantity=8, unit='kg', status='COMPLETED',
        )
        self.product = Product.objects.create(
            product_name='Herb Powder',
            product_type='Powder',
            manufacturer=factory,
            manufacturing_record=record,
            manufacture_date='2026-11-19',
            batch_number='PROD-001',
            total_quantity=8,
            unit='kg',
        )

    def test_public_verification_returns_incomplete_without_input_batch(self):
        client = APIClient()
        response = client.get(f'/api/products/verify/{self.product.qr_reference}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['verification_status'], 'INCOMPLETE')
