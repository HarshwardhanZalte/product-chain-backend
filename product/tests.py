from unittest.mock import patch

import qrcode
from django.test import TestCase
from django.test import override_settings
from rest_framework.test import APIClient

from .models import Product
from factory.models import FactoryProfile, ManufacturingBatch, ManufacturingRecord
from farmer.models import FarmerProfile, HerbBatch
from lab.models import LabMeasurement, LabProfile, LabTest
from organization.models import Organization
from users.models import User
from .models import ProductBatch
from .views import generate_product_qr


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
        LabMeasurement.objects.create(
            test=self.lab_test,
            analyte='Withanolide content',
            method='HPLC',
            result_value='5.82',
            numeric_value='5.82',
            unit='% w/w',
            threshold='>= 2.50',
            verdict=LabMeasurement.Verdict.PASS,
        )
        response = client.get(f'/api/products/verify/{self.product.qr_reference}/')
        self.assertEqual(response.json()['verification_status'], 'VERIFIED')
        self.assertEqual(
            response.json()['input_herb_batches'][0]['lab_measurements'][0]['analyte'],
            'Withanolide content',
        )
        self.assertEqual(
            response.json()['product']['product_id'],
            str(self.product.product_id),
        )

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


    def test_generated_qr_points_to_frontend_verification_page_when_configured(self):
        payloads = []
        original_add_data = qrcode.QRCode.add_data

        def capture_payload(qr, data, optimize=20):
            payloads.append(data)
            return original_add_data(qr, data, optimize)

        with (
            override_settings(
                PRODUCT_VERIFICATION_FRONTEND_URL='https://trace.example',
                PRODUCT_VERIFICATION_BASE_URL='https://api.example',
            ),
            patch('qrcode.QRCode.add_data', capture_payload),
            patch.object(self.product.qr_code_image, 'save'),
        ):
            generate_product_qr(self.product)

        self.assertEqual(
            payloads,
            [f'https://trace.example/verify/{self.product.qr_reference}/'],
        )
