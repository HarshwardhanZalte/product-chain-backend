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
            verification_status='VERIFIED',
        )
        lab_user = User.objects.create_user(
            email='lab@example.com', password='StrongPass123',
            name='Lab', role='LAB', organization=org, is_email_verified=True,
        )
        self.lab_profile = LabProfile.objects.create(
            user=lab_user, organization=org, laboratory_name='Lab',
            registration_number='LAB-TEST', address='Address', contact_number='123',
            verification_status='VERIFIED',
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
            status=HerbBatch.Status.SENT_TO_LAB,
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

    def test_certificate_upload_rejects_unsupported_extension(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post('/api/labs/submit-result/', {
            'test_id': str(self.test.test_id),
            'certificate_file': SimpleUploadedFile('certificate.exe', b'not a certificate'),
        }, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_certificate_upload_rejects_mismatched_file_content(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post('/api/labs/submit-result/', {
            'test_id': str(self.test.test_id),
            'certificate_file': SimpleUploadedFile('certificate.pdf', b'not a PDF'),
        }, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_lab_approval_requires_a_recorded_result(self):
        approval = self.client.post('/api/labs/approve-test/', {
            'test_id': str(self.test.test_id),
        }, format='json')
        self.assertEqual(approval.status_code, 400)

        result = self.client.post('/api/labs/submit-result/', {
            'test_id': str(self.test.test_id),
            'test_result': 'Passed',
        }, format='json')
        self.assertEqual(result.status_code, 200)
        approval = self.client.post('/api/labs/approve-test/', {
            'test_id': str(self.test.test_id),
        }, format='json')
        self.assertEqual(approval.status_code, 200)

    def test_rejected_batch_cannot_be_submitted_for_retesting(self):
        self.batch.status = HerbBatch.Status.REJECTED
        self.batch.save(update_fields=['status'])
        response = self.client.post('/api/labs/submit-batch/', {
            'batch_id': self.batch.batch_id,
            'laboratory_id': str(self.lab_profile.lab_id),
            'test_type': 'Repeat purity test',
            'test_date': '2026-11-20',
        }, format='json')
        self.assertEqual(response.status_code, 400)
