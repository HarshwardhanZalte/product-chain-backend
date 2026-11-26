from django.test import TestCase
from rest_framework.test import APIClient

from farmer.models import FarmerProfile, HerbBatch
from organization.models import Organization
from users.models import User

from .models import CollectorProfile, TransferEvent


class TransferWorkflowTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Org',
            organization_type='COLLECTOR',
            registration_number='ORG-TRANSFER',
            email='org@example.com',
            phone_number='123',
            address='Address',
            state='State',
            district='District',
            pincode='123456',
            verification_status='VERIFIED',
        )
        self.farmer = User.objects.create_user(
            email='farmer@example.com', password='StrongPass123',
            name='Farmer', role='FARMER', organization=self.organization,
            is_email_verified=True,
        )
        self.collector = User.objects.create_user(
            email='collector@example.com', password='StrongPass123',
            name='Collector', role='COLLECTOR', organization=self.organization,
            is_email_verified=True,
        )
        profile = FarmerProfile.objects.create(
            user=self.farmer, organization=self.organization, farmer_name='Farmer',
            phone_number='123', address='Address', village='Village',
            district='District', state='State', pincode='123456',
            verification_status='VERIFIED',
        )
        self.batch = HerbBatch.objects.create(
            batch_id='ASH-2026-00001', herb_name='Ashwagandha',
            botanical_name='Withania somnifera', quantity=10,
            unit='kg', available_quantity=10, source_type='CULTIVATED',
            collection_date='2026-11-19', collection_time='10:30',
            collection_address='Farm', village='Village', district='District',
            state='State', farmer=profile, current_owner=self.farmer,
            organization=self.organization,
        )
        CollectorProfile.objects.create(
            user=self.collector, organization=self.organization,
            collector_name='Collector', phone_number='123', address='Address',
            verification_status='VERIFIED',
        )

    def test_accept_updates_owner_only_after_acceptance(self):
        client = APIClient()
        client.force_authenticate(self.farmer)
        initiate = client.post('/api/collectors/transfer/initiate/', {
            'batch_id': self.batch.batch_id,
            'to_party': self.collector.pk,
            'quantity': '10.000',
            'transfer_location': 'Collector depot',
        }, format='json')
        self.assertEqual(initiate.status_code, 201)
        event_id = initiate.json()['event_id']
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.current_owner, self.farmer)
        client.force_authenticate(self.collector)
        accept = client.post('/api/collectors/transfer/accept/', {
            'event_id': event_id,
        }, format='json')
        self.assertEqual(accept.status_code, 200)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.current_owner, self.collector)

    def test_transfer_workflow_works_without_organization_records(self):
        self.farmer.organization = None
        self.farmer.save(update_fields=['organization'])
        self.collector.organization = None
        self.collector.save(update_fields=['organization'])
        self.batch.organization = None
        self.batch.save(update_fields=['organization'])
        self.batch.farmer.organization = None
        self.batch.farmer.save(update_fields=['organization'])
        self.collector.collector_profile.organization = None
        self.collector.collector_profile.save(update_fields=['organization'])

        client = APIClient()
        client.force_authenticate(self.farmer)
        response = client.post('/api/collectors/transfer/initiate/', {
            'batch_id': self.batch.batch_id,
            'to_party': self.collector.pk,
            'quantity': '10.000',
            'transfer_location': 'Collector depot',
        }, format='json')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn('from_organization', response.data)
        self.assertNotIn('to_organization', response.data)
        event = TransferEvent.objects.get(event_id=response.data['event_id'])
        self.assertIsNone(event.from_organization)
        self.assertIsNone(event.to_organization)

    def test_partial_batch_transfer_is_rejected(self):
        client = APIClient()
        client.force_authenticate(self.farmer)
        response = client.post('/api/collectors/transfer/initiate/', {
            'batch_id': self.batch.batch_id,
            'to_party': self.collector.pk,
            'quantity': '5.000',
            'transfer_location': 'Collector depot',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_batch_history_includes_transfer_timeline(self):
        client = APIClient()
        client.force_authenticate(self.farmer)
        create = client.post('/api/collectors/transfer/initiate/', {
            'batch_id': self.batch.batch_id,
            'to_party': self.collector.pk,
            'quantity': '10.000',
            'transfer_location': 'Collector depot',
        }, format='json')
        self.assertEqual(create.status_code, 201)
        client.force_authenticate(self.collector)
        accept = client.post('/api/collectors/transfer/accept/', {
            'event_id': create.json()['event_id'],
        }, format='json')
        self.assertEqual(accept.status_code, 200)

        client.force_authenticate(self.farmer)
        history = client.get(f'/api/batches/batches/history/{self.batch.batch_id}/')
        self.assertEqual(history.status_code, 200)
        self.assertEqual(
            [entry['event_type'] for entry in history.json()['history']],
            ['BATCH_REGISTERED', 'TRANSFER'],
        )
        self.assertEqual(history.json()['history'][1]['status'], 'ACCEPTED')

    def test_stale_transfer_is_cancelled_instead_of_changing_owner(self):
        client = APIClient()
        client.force_authenticate(self.farmer)
        create = client.post('/api/collectors/transfer/initiate/', {
            'batch_id': self.batch.batch_id,
            'to_party': self.collector.pk,
            'quantity': '10.000',
            'transfer_location': 'Collector depot',
        }, format='json')
        event_id = create.json()['event_id']
        self.batch.current_owner = self.collector
        self.batch.save(update_fields=['current_owner'])

        client.force_authenticate(self.collector)
        accept = client.post(
            '/api/collectors/transfer/accept/',
            {'event_id': event_id},
            format='json',
        )
        self.assertEqual(accept.status_code, 409)
        self.assertEqual(
            TransferEvent.objects.get(event_id=event_id).status,
            TransferEvent.Status.CANCELLED,
        )

    def test_available_batches_only_contains_batches_owned_by_collector(self):
        self.batch.current_owner = self.collector
        self.batch.status = HerbBatch.Status.WITH_COLLECTOR
        self.batch.save(update_fields=['current_owner', 'status'])

        other_batch = HerbBatch.objects.create(
            batch_id='ASH-2026-OTHER',
            herb_name='Brahmi',
            botanical_name='Bacopa monnieri',
            quantity=5,
            unit='kg',
            available_quantity=5,
            source_type='CULTIVATED',
            collection_date='2026-11-19',
            collection_time='10:30',
            collection_address='Farm',
            village='Village',
            district='District',
            state='State',
            farmer=self.batch.farmer,
            current_owner=self.farmer,
            organization=self.organization,
            status=HerbBatch.Status.REGISTERED,
        )

        client = APIClient()
        client.force_authenticate(self.collector)
        response = client.get('/api/collectors/available-batches/')

        self.assertEqual(response.status_code, 200)
        identifiers = {
            entry['batch_id'] for entry in response.data['results']
        }
        self.assertIn(self.batch.batch_id, identifiers)
        self.assertNotIn(other_batch.batch_id, identifiers)

    def test_transfer_response_includes_display_safe_batch_and_parties(self):
        client = APIClient()
        client.force_authenticate(self.farmer)
        response = client.post('/api/collectors/transfer/initiate/', {
            'batch_id': self.batch.batch_id,
            'to_party': self.collector.pk,
            'quantity': '10.000',
            'transfer_location': 'Collector depot',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['batch_identifier'], self.batch.batch_id)
        self.assertEqual(response.data['from_party_name'], self.farmer.name)
        self.assertEqual(response.data['to_party_name'], self.collector.name)
