from django.test import TestCase
from rest_framework.test import APIClient

from collector.models import CollectorProfile, TransferEvent
from farmer.models import FarmerProfile, HerbBatch
from lab.models import LabProfile, LabTest
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
            verification_status='VERIFIED',
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
            verification_status='VERIFIED',
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
            organization=self.organization, status='SENT_TO_FACTORY',
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

    def test_rejects_duplicate_batch_entries(self):
        response = self.client.post('/api/factories/manufacturing/create/', {
            'product_name': 'Herb Powder',
            'process_date': '2026-11-19',
            'process_description': 'Powder processing',
            'output_quantity': '8.000',
            'unit': 'kg',
            'input_batches': [
                {'batch_id': self.batch.batch_id, 'quantity_used': '2.000'},
                {'batch_id': self.batch.batch_id, 'quantity_used': '2.000'},
            ],
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_receive_requires_pending_transfer_event(self):
        response = self.client.post(
            '/api/factories/receive-batch/',
            {'batch_id': self.batch.batch_id},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_receive_batch_requires_and_accepts_a_pending_transfer(self):
        collector = User.objects.create_user(
            email='collector@example.com', password='StrongPass123',
            name='Collector', role='COLLECTOR',
            organization=self.organization, is_email_verified=True,
        )
        CollectorProfile.objects.create(
            user=collector,
            organization=self.organization,
            collector_name='Collector',
            phone_number='123',
            address='Depot',
            verification_status='VERIFIED',
        )
        self.batch.current_owner = collector
        self.batch.status = HerbBatch.Status.APPROVED
        self.batch.save(update_fields=['current_owner', 'status'])
        lab_user = User.objects.create_user(
            email='lab@example.com', password='StrongPass123',
            name='Lab', role='LAB',
            organization=self.organization, is_email_verified=True,
        )
        lab_profile = LabProfile.objects.create(
            user=lab_user,
            organization=self.organization,
            laboratory_name='Lab',
            registration_number='LAB-FACTORY-TEST',
            address='Lab',
            contact_number='123',
            verification_status='VERIFIED',
        )
        LabTest.objects.create(
            batch=self.batch,
            laboratory=lab_profile,
            submitted_by=collector,
            test_date='2026-11-18',
            test_type='Purity',
            status=LabTest.Status.APPROVED,
        )
        event = TransferEvent.objects.create(
            batch=self.batch,
            from_party=collector,
            to_party=self.factory_user,
            from_organization=self.organization,
            to_organization=self.organization,
            quantity=self.batch.available_quantity,
            transfer_date='2026-11-19',
            transfer_location='Factory',
            status=TransferEvent.Status.INITIATED,
            recorded_by=collector,
        )

        response = self.client.post(
            '/api/factories/receive-batch/',
            {'event_id': str(event.event_id)},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.current_owner, self.factory_user)
        self.assertEqual(self.batch.status, HerbBatch.Status.SENT_TO_FACTORY)

    def test_rejects_manufacturing_unit_mismatch(self):
        response = self.client.post('/api/factories/manufacturing/create/', {
            'product_name': 'Herb Powder',
            'process_date': '2026-11-19',
            'process_description': 'Powder processing',
            'output_quantity': '8.000',
            'unit': 'liters',
            'input_batches': [{'batch_id': self.batch.batch_id, 'quantity_used': '2.000'}],
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_collector_cannot_send_unapproved_batch_to_factory(self):
        collector = User.objects.create_user(
            email='collector@example.com', password='StrongPass123',
            name='Collector', role='COLLECTOR',
            organization=self.organization, is_email_verified=True,
        )
        CollectorProfile.objects.create(
            user=collector,
            organization=self.organization,
            collector_name='Collector',
            phone_number='123',
            address='Depot',
            verification_status='VERIFIED',
        )
        self.batch.current_owner = collector
        self.batch.status = HerbBatch.Status.WITH_COLLECTOR
        self.batch.save(update_fields=['current_owner', 'status'])

        client = APIClient()
        client.force_authenticate(collector)
        response = client.post('/api/collectors/transfer/initiate/', {
            'batch_id': self.batch.batch_id,
            'to_party': self.factory_user.pk,
            'quantity': '10.000',
            'transfer_location': 'Factory',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_manufacturing_draft_does_not_consume_stock_until_completed(self):
        draft = self.client.post('/api/factories/manufacturing/create/', {
            'product_name': 'Herb Extract',
            'process_date': '2026-11-19',
            'process_description': 'Hydro-ethanolic extraction',
            'facility_line': 'Extraction line 2',
            'shift': 'Morning',
            'standard_operating_procedure': 'SOP-04',
            'solvent_method': 'Water and ethanol',
            'target_yield_ratio': '5:1',
            'process_parameters': {'temperature_c': '45.2'},
            'quality_control_lead': 'Dr. Example',
            'output_quantity': '8.000',
            'unit': 'kg',
            'save_as_draft': True,
            'input_batches': [{
                'batch_id': self.batch.batch_id,
                'quantity_used': '4.000',
            }],
        }, format='json')
        self.assertEqual(draft.status_code, 201)
        self.assertEqual(draft.data['status'], 'PLANNED')
        self.assertEqual(draft.data['input_batches'][0]['batch_id'], self.batch.batch_id)
        self.batch.refresh_from_db()
        self.assertEqual(str(self.batch.available_quantity), '10.000')

        complete = self.client.post('/api/factories/manufacturing/complete/', {
            'manufacturing_id': draft.data['manufacturing_id'],
        }, format='json')
        self.assertEqual(complete.status_code, 200)
        self.assertEqual(complete.data['status'], 'COMPLETED')
        self.batch.refresh_from_db()
        self.assertEqual(str(self.batch.available_quantity), '6.000')

    def test_manufacturing_draft_can_be_cancelled_without_consuming_stock(self):
        draft = self.client.post('/api/factories/manufacturing/create/', {
            'product_name': 'Herb Extract',
            'process_date': '2026-11-19',
            'process_description': 'Extraction',
            'output_quantity': '8.000',
            'unit': 'kg',
            'save_as_draft': True,
            'input_batches': [{
                'batch_id': self.batch.batch_id,
                'quantity_used': '4.000',
            }],
        }, format='json')
        self.assertEqual(draft.status_code, 201)

        cancelled = self.client.post('/api/factories/manufacturing/cancel/', {
            'manufacturing_id': draft.data['manufacturing_id'],
        }, format='json')
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.data['status'], 'CANCELLED')
        self.batch.refresh_from_db()
        self.assertEqual(str(self.batch.available_quantity), '10.000')
