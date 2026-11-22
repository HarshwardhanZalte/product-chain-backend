from django.test import TestCase
from rest_framework.test import APIClient

from .models import Product
from factory.models import FactoryProfile, ManufacturingBatch, ManufacturingRecord
from farmer.models import FarmerProfile, HerbBatch
from lab.models import LabProfile, LabTest
from organization.models import Organization
from users.models import User
from .models import ProductBatch


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
            verification_status='VERIFIED',
        )
        user = User.objects.create_user(
            email='factory@example.com', password='StrongPass123',
            name='Factory', role='FACTORY', organization=org,
            is_email_verified=True,
        )
        factory = FactoryProfile.objects.create(
            user=user, organization=org, factory_name='Factory',
            registration_number='FAC-VERIFY', address='Address', contact_number='123',
            verification_status='VERIFIED',
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
        farmer_user = User.objects.create_user(
            email='farmer@example.com', password='StrongPass123',
            name='Farmer', role='FARMER', organization=org, is_email_verified=True,
        )
        farmer_profile = FarmerProfile.objects.create(
            user=farmer_user, organization=org, farmer_name='Farmer',
            phone_number='123', address='Address', village='Village',
            district='District', state='State', pincode='123456',
        )
        self.input_batch = HerbBatch.objects.create(
            batch_id='ASH-2026-VERIFY', herb_name='Ashwagandha',
            botanical_name='Withania somnifera', quantity=10,
            unit='kg', available_quantity=0, source_type='CULTIVATED',
            collection_date='2026-11-19', collection_time='10:30',
            collection_address='Farm', village='Village', district='District',
            state='State', farmer=farmer_profile, current_owner=user,
            organization=org, status='CONSUMED',
        )
        ManufacturingBatch.objects.create(
            manufacturing_record=record,
            herb_batch=self.input_batch,
            quantity_used=10,
            unit='kg',
        )
        ProductBatch.objects.create(
            product=self.product,
            herb_batch=self.input_batch,
            quantity_used=10,
            unit='kg',
        )
        lab_user = User.objects.create_user(
            email='lab@example.com', password='StrongPass123',
            name='Lab', role='LAB', organization=org, is_email_verified=True,
        )
        lab_profile = LabProfile.objects.create(
            user=lab_user, organization=org, laboratory_name='Lab',
            registration_number='LAB-VERIFY', address='Address', contact_number='123',
            verification_status='VERIFIED',
        )
        self.lab_test = LabTest.objects.create(
            batch=self.input_batch,
            laboratory=lab_profile,
            submitted_by=lab_user,
            test_date='2026-11-19',
            test_type='Purity',
            status=LabTest.Status.PENDING,
        )

    def test_public_verification_is_incomplete_until_latest_test_is_approved(self):
        client = APIClient()
        response = client.get(f'/api/products/verify/{self.product.qr_reference}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['verification_status'], 'INCOMPLETE')

        self.lab_test.status = LabTest.Status.APPROVED
        self.lab_test.save(update_fields=['status'])
        response = client.get(f'/api/products/verify/{self.product.qr_reference}/')
        self.assertEqual(response.json()['verification_status'], 'VERIFIED')

    def test_product_allocations_cannot_exceed_manufacturing_output(self):
        client = APIClient()
        client.force_authenticate(self.product.manufacturer.user)
        response = client.post('/api/products/create/', {
            'manufacturing_id': str(self.product.manufacturing_record.manufacturing_id),
            'product_name': 'Additional Powder',
            'product_type': 'Powder',
            'manufacture_date': '2026-11-20',
            'batch_number': 'PROD-002',
            'total_quantity': '0.001',
            'unit': 'kg',
        }, format='json')
        self.assertEqual(response.status_code, 400)
