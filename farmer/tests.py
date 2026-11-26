from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from rest_framework.test import APIClient

from organization.models import Organization
from users.models import ActivityLog, User

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

    def test_batch_registration_requires_approved_profile_but_not_organization(self):
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
        self.profile.organization = None
        self.profile.save(update_fields=['verification_status', 'organization'])
        self.user.organization = None
        self.user.save(update_fields=['organization'])
        no_organization = self.client.post(
            '/api/farmers/batches/register/',
            response_data,
            format='json',
        )
        self.assertEqual(no_organization.status_code, 201)
        self.assertNotIn('organization', no_organization.data)

    def test_profile_is_created_without_organization(self):
        user = User.objects.create_user(
            email='profile-no-org@example.com',
            password='StrongPass123',
            name='Profile Without Organization',
            role='FARMER',
            is_email_verified=True,
        )
        client = APIClient()
        client.force_authenticate(user)

        response = client.get('/api/farmers/profile/')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('organization', response.data)

    def test_editing_approved_profile_returns_it_to_pending_review(self):
        response = self.client.patch(
            '/api/farmers/profile/',
            {'address': 'Updated Farm Road'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.verification_status, 'PENDING')
        self.assertTrue(
            ActivityLog.objects.filter(
                action='BUSINESS_PROFILE_UPDATED_REQUIRES_REVIEW',
                user=self.user,
            ).exists()
        )

    def test_batch_registration_persists_stitch_harvest_fields(self):
        response = self.client.post('/api/farmers/batches/register/', {
            'herb_name': 'Ashwagandha',
            'botanical_name': 'Withania somnifera',
            'plant_part': 'ROOTS',
            'cultivar': 'Nagori',
            'quality_grade': 'Grade A',
            'packaging_details': '18 sealed bags',
            'drying_notes': 'Shade dried',
            'gacp_attested': True,
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
        self.assertEqual(response.data['plant_part'], 'ROOTS')
        self.assertEqual(response.data['cultivar'], 'Nagori')
        self.assertTrue(response.data['gacp_attested'])

    def test_field_evidence_upload_is_validated_and_listed_for_batch(self):
        batch = HerbBatch.objects.create(
            batch_id='ASH-2026-EVIDENCE',
            herb_name='Ashwagandha',
            botanical_name='Withania somnifera',
            quantity=10,
            unit='kg',
            available_quantity=10,
            source_type='CULTIVATED',
            collection_date='2026-11-19',
            collection_time='10:30',
            collection_address='Farm',
            village='Village',
            district='District',
            state='State',
            farmer=self.profile,
            current_owner=self.user,
            organization=self.organization,
        )
        image_buffer = BytesIO()
        Image.new('RGB', (2, 2), color='green').save(image_buffer, format='PNG')
        upload = SimpleUploadedFile(
            'field-photo.png',
            image_buffer.getvalue(),
            content_type='image/png',
        )
        url = f'/api/farmers/batches/detail/{batch.batch_id}/evidence/'
        response = self.client.post(
            url,
            {'kind': 'PHOTO', 'file': upload, 'label': 'Harvest plot'},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['kind'], 'PHOTO')

        listed = self.client.get(url)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]['label'], 'Harvest plot')
