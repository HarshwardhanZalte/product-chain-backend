from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from collector.models import CollectorProfile, TransferEvent
from factory.models import FactoryProfile, ManufacturingBatch, ManufacturingRecord
from farmer.models import FarmerProfile, HerbBatch
from lab.models import LabProfile, LabTest
from organization.models import BlockchainEvent, Organization
from product.models import Product, ProductBatch
from users.models import ActivityLog, EmailOTP, User


class Command(BaseCommand):
    help = 'Seed repeatable test data for all application models.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing test data created by this command before reseeding.',
        )
        parser.add_argument(
            '--password',
            default='TestPass123',
            help='Password for seeded users (default: TestPass123).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']

        if options['clear']:
            self._clear_test_data()

        organizations = {
            'farmer': self._organization(
                'Seed Farmer Cooperative',
                'FARMER_GROUP',
                'SEED-FARM-001',
            ),
            'collector': self._organization(
                'Seed Herb Collector',
                'COLLECTOR',
                'SEED-COLL-001',
            ),
            'lab': self._organization(
                'Seed Testing Laboratory',
                'TESTING_LAB',
                'SEED-LAB-001',
            ),
            'factory': self._organization(
                'Seed Ayurvedic Factory',
                'MANUFACTURER',
                'SEED-FAC-001',
            ),
        }

        users = {
            'farmer': self._user(
                'seed.farmer@example.com',
                'Seed Farmer',
                'FARMER',
                organizations['farmer'],
                password,
            ),
            'collector': self._user(
                'seed.collector@example.com',
                'Seed Collector',
                'COLLECTOR',
                organizations['collector'],
                password,
            ),
            'lab': self._user(
                'seed.lab@example.com',
                'Seed Laboratory User',
                'LAB',
                organizations['lab'],
                password,
            ),
            'factory': self._user(
                'seed.factory@example.com',
                'Seed Factory User',
                'FACTORY',
                organizations['factory'],
                password,
            ),
        }

        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                email='seed.admin@example.com',
                password=password,
                name='Seed Administrator',
                phone_number='9999999999',
            )
        users['admin'] = admin_user

        farmer_profile, _ = FarmerProfile.objects.update_or_create(
            user=users['farmer'],
            defaults={
                'organization': organizations['farmer'],
                'farmer_name': 'Seed Farmer',
                'phone_number': '9000000001',
                'address': 'Seed Farm Road',
                'village': 'Seed Village',
                'district': 'Pune',
                'state': 'Maharashtra',
                'pincode': '411001',
                'land_area': Decimal('12.50'),
                'land_record_reference': 'SEED-LAND-001',
                'verification_status': 'VERIFIED',
            },
        )

        collector_profile, _ = CollectorProfile.objects.update_or_create(
            user=users['collector'],
            defaults={
                'organization': organizations['collector'],
                'collector_name': 'Seed Collector',
                'phone_number': '9000000002',
                'address': 'Seed Collector Depot',
                'verification_status': 'VERIFIED',
            },
        )

        lab_profile, _ = LabProfile.objects.update_or_create(
            user=users['lab'],
            defaults={
                'organization': organizations['lab'],
                'laboratory_name': 'Seed Testing Laboratory',
                'registration_number': 'SEED-LAB-REG-001',
                'address': 'Seed Laboratory Campus',
                'contact_number': '9000000003',
                'verification_status': 'VERIFIED',
            },
        )

        factory_profile, _ = FactoryProfile.objects.update_or_create(
            user=users['factory'],
            defaults={
                'organization': organizations['factory'],
                'factory_name': 'Seed Ayurvedic Factory',
                'registration_number': 'SEED-FAC-REG-001',
                'address': 'Seed Factory Industrial Area',
                'contact_number': '9000000004',
                'verification_status': 'VERIFIED',
            },
        )

        approved_batch, _ = HerbBatch.objects.update_or_create(
            batch_id='ASH-2026-00001',
            defaults={
                'herb_name': 'Ashwagandha',
                'botanical_name': 'Withania somnifera',
                'description': 'Seed traceability batch',
                'quantity': Decimal('100.000'),
                'unit': 'kg',
                'available_quantity': Decimal('100.000'),
                'source_type': 'CULTIVATED',
                'collection_date': date(2026, 10, 1),
                'collection_time': time(8, 30),
                'latitude': Decimal('18.520430'),
                'longitude': Decimal('73.856743'),
                'collection_address': 'Seed Collection Field',
                'village': 'Seed Village',
                'district': 'Pune',
                'state': 'Maharashtra',
                'farmer': farmer_profile,
                'current_owner': users['factory'],
                'organization': organizations['farmer'],
                'status': 'APPROVED',
                'remarks': 'Approved seed batch',
            },
        )

        rejected_batch, _ = HerbBatch.objects.update_or_create(
            batch_id='ASH-2026-00002',
            defaults={
                'herb_name': 'Tulsi',
                'botanical_name': 'Ocimum tenuiflorum',
                'description': 'Rejected seed traceability batch',
                'quantity': Decimal('40.000'),
                'unit': 'kg',
                'available_quantity': Decimal('40.000'),
                'source_type': 'CULTIVATED',
                'collection_date': date(2026, 10, 2),
                'collection_time': time(9, 15),
                'collection_address': 'Seed Tulsi Field',
                'village': 'Seed Village',
                'district': 'Pune',
                'state': 'Maharashtra',
                'farmer': farmer_profile,
                'current_owner': users['lab'],
                'organization': organizations['farmer'],
                'status': 'REJECTED',
                'remarks': 'Rejected seed batch',
            },
        )

        transfer, _ = TransferEvent.objects.update_or_create(
            event_id='00000000-0000-0000-0000-000000000001',
            defaults={
                'batch': approved_batch,
                'from_party': users['farmer'],
                'to_party': users['collector'],
                'from_organization': organizations['farmer'],
                'to_organization': organizations['collector'],
                'quantity': Decimal('100.000'),
                'transfer_date': date(2026, 10, 3),
                'transfer_location': 'Seed Collector Depot',
                'remarks': 'Seed transfer accepted',
                'status': 'ACCEPTED',
                'recorded_by': users['farmer'],
            },
        )

        approved_test, _ = LabTest.objects.update_or_create(
            test_id='00000000-0000-0000-0000-000000000002',
            defaults={
                'batch': approved_batch,
                'laboratory': lab_profile,
                'submitted_by': users['lab'],
                'reviewed_by': users['lab'],
                'test_date': date(2026, 10, 4),
                'test_type': 'Purity and pesticide screening',
                'test_parameters': {
                    'purity_percent': 99.2,
                    'pesticide_detected': False,
                },
                'test_result': 'Passed all configured seed tests',
                'result_summary': 'Approved',
                'remarks': 'Seed laboratory approval',
                'certificate_hash': 'seed-certificate-reference',
                'status': 'APPROVED',
            },
        )

        LabTest.objects.update_or_create(
            test_id='00000000-0000-0000-0000-000000000003',
            defaults={
                'batch': rejected_batch,
                'laboratory': lab_profile,
                'submitted_by': users['lab'],
                'reviewed_by': users['lab'],
                'test_date': date(2026, 10, 5),
                'test_type': 'Contamination screening',
                'test_parameters': {
                    'contamination_detected': True,
                },
                'test_result': 'Failed contamination screening',
                'result_summary': 'Rejected',
                'remarks': 'Seed laboratory rejection',
                'status': 'REJECTED',
            },
        )

        manufacturing_record, _ = ManufacturingRecord.objects.update_or_create(
            manufacturing_id='00000000-0000-0000-0000-000000000004',
            defaults={
                'factory': factory_profile,
                'created_by': users['factory'],
                'product_name': 'Ashwagandha Root Powder',
                'process_date': date(2026, 10, 6),
                'process_description': 'Clean, dry, grind, and sieve the approved herb batch.',
                'input_quantity': Decimal('100.000'),
                'output_quantity': Decimal('80.000'),
                'unit': 'kg',
                'status': 'COMPLETED',
                'remarks': 'Seed manufacturing record',
            },
        )

        manufacturing_batch, _ = ManufacturingBatch.objects.update_or_create(
            manufacturing_record=manufacturing_record,
            herb_batch=approved_batch,
            defaults={
                'quantity_used': Decimal('100.000'),
                'unit': 'kg',
            },
        )

        product, _ = Product.objects.update_or_create(
            batch_number='SEED-PRODUCT-001',
            defaults={
                'product_name': 'Ashwagandha Root Powder',
                'description': 'Seed finished-product traceability record',
                'product_type': 'Herbal powder',
                'manufacturer': factory_profile,
                'manufacturing_record': manufacturing_record,
                'manufacture_date': date(2026, 10, 6),
                'expiry_date': date(2027, 10, 6),
                'total_quantity': Decimal('80.000'),
                'unit': 'kg',
                'status': 'ACTIVE',
            },
        )

        ProductBatch.objects.update_or_create(
            product=product,
            herb_batch=approved_batch,
            defaults={
                'quantity_used': Decimal('100.000'),
                'unit': 'kg',
            },
        )

        now = timezone.now()
        EmailOTP.objects.filter(
            user=users['farmer'],
            purpose='VERIFY_EMAIL',
            used_at__isnull=True,
        ).update(used_at=now)
        EmailOTP.objects.create(
            user=users['farmer'],
            purpose='VERIFY_EMAIL',
            otp_hash=EmailOTP.hash_otp('098765'),
            expires_at=now + timedelta(minutes=10),
            attempts=0,
            resend_available_at=now,
        )

        BlockchainEvent.objects.update_or_create(
            blockchain_event_id='00000000-0000-0000-0000-000000000005',
            defaults={
                'entity_type': 'HerbBatch',
                'entity_id': approved_batch.batch_id,
                'event_type': 'SEED_PLACEHOLDER',
                'transaction_hash': None,
                'block_number': None,
                'network_name': None,
                'contract_address': None,
                'data_hash': None,
                'transaction_status': None,
                'recorded_at': None,
            },
        )

        log_items = [
            ('USER_REGISTERED', 'User', users['farmer'].user_id, 'Seed farmer created'),
            ('BATCH_REGISTERED', 'HerbBatch', approved_batch.batch_id, 'Seed batch registered'),
            ('TRANSFER_ACCEPTED', 'TransferEvent', transfer.event_id, 'Seed transfer accepted'),
            ('LAB_TEST_APPROVED', 'LabTest', approved_test.test_id, 'Seed test approved'),
            ('MANUFACTURING_CREATED', 'ManufacturingRecord', manufacturing_record.manufacturing_id, 'Seed manufacturing created'),
            ('PRODUCT_CREATED', 'Product', product.product_id, 'Seed product created'),
        ]
        for action, entity_type, entity_id, description in log_items:
            ActivityLog.objects.get_or_create(
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id),
                defaults={
                    'user': users['admin'],
                    'description': description,
                    'ip_address': '127.0.0.1',
                },
            )

        self.stdout.write(self.style.SUCCESS(
            'Seed test data created successfully.\n'
            f'Password for seeded users: {password}\n'
            'Seed administrator: seed.admin@example.com (only created when no superuser exists)'
        ))

    def _organization(self, name, organization_type, registration_number):
        organization, _ = Organization.objects.update_or_create(
            registration_number=registration_number,
            defaults={
                'organization_name': name,
                'organization_type': organization_type,
                'email': f"{registration_number.lower()}@example.com",
                'phone_number': '9000000010',
                'address': f'{name} Address',
                'state': 'Maharashtra',
                'district': 'Pune',
                'pincode': '411001',
                'verification_status': 'VERIFIED',
            },
        )
        return organization

    def _user(self, email, name, role, organization, password):
        user, _ = User.objects.update_or_create(
            email=email,
            defaults={
                'name': name,
                'phone_number': '9000000020',
                'role': role,
                'organization': organization,
                'is_active': True,
                'is_email_verified': True,
                'is_staff': False,
                'is_superuser': False,
            },
        )
        user.set_password(password)
        user.save(update_fields=['password'])
        return user

    def _clear_test_data(self):
        test_emails = [
            'seed.farmer@example.com',
            'seed.collector@example.com',
            'seed.lab@example.com',
            'seed.factory@example.com',
        ]
        test_user_ids = list(User.objects.filter(email__in=test_emails).values_list('pk', flat=True))

        Product.objects.filter(batch_number='SEED-PRODUCT-001').delete()
        ManufacturingRecord.objects.filter(
            manufacturing_id='00000000-0000-0000-0000-000000000004'
        ).delete()
        LabTest.objects.filter(
            test_id__in=[
                '00000000-0000-0000-0000-000000000002',
                '00000000-0000-0000-0000-000000000003',
            ]
        ).delete()
        TransferEvent.objects.filter(
            event_id='00000000-0000-0000-0000-000000000001'
        ).delete()
        HerbBatch.objects.filter(batch_id__in=['ASH-2026-00001', 'ASH-2026-00002']).delete()
        User.objects.filter(pk__in=test_user_ids).delete()
        Organization.objects.filter(
            registration_number__startswith='SEED-'
        ).delete()
