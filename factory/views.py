from decimal import Decimal

from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import OpenApiTypes, extend_schema

from farmer.models import HerbBatch
from users.permissions import IsApprovedBusinessUser, IsExpectedRole, IsVerifiedActiveUser
from users.services import log_activity, update_profile_for_review

from collector.models import TransferEvent
from collector.services import accept_transfer
from .models import ManufacturingBatch, ManufacturingRecord
from .serializers import (
    ManufacturingCreateSerializer,
    ManufacturingActionSerializer,
    ManufacturingRecordSerializer,
    ReceiveBatchSerializer,
    FactoryProfileSerializer,
)


class FactoryProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsVerifiedActiveUser, IsExpectedRole)
    expected_role = 'FACTORY'
    serializer_class = FactoryProfileSerializer

    def get_object(self):
        from .models import FactoryProfile
        profile, _ = FactoryProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'factory_name': self.request.user.name,
                'registration_number': f'FAC-{self.request.user.user_id}',
                'address': '',
                'contact_number': self.request.user.phone_number,
            },
        )
        return profile

    def perform_update(self, serializer):
        update_profile_for_review(serializer, self.request.user)


class FactoryDashboardView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        if request.user.role != 'FACTORY':
            return Response({'detail': 'Only factory users can access this dashboard.'}, status=403)
        profile = getattr(request.user, 'factory_profile', None)
        if not profile:
            return Response({'detail': 'Factory profile is not configured.'}, status=404)
        records = ManufacturingRecord.objects.filter(factory=profile)
        return Response({
            'manufacturing_records': records.count(),
            'completed': records.filter(status='COMPLETED').count(),
            'in_progress': records.filter(status='IN_PROGRESS').count(),
        })


class AvailableApprovedBatchesView(generics.ListAPIView):
    permission_classes = (IsVerifiedActiveUser,)

    def get_serializer_class(self):
        from farmer.serializers import HerbBatchSerializer
        return HerbBatchSerializer

    def get_queryset(self):
        if getattr(self.request.user, 'role', None) != 'FACTORY':
            return HerbBatch.objects.none()
        return HerbBatch.objects.filter(
            current_owner=self.request.user,
            status=HerbBatch.Status.SENT_TO_FACTORY,
            available_quantity__gt=0,
        )


class ReceiveBatchView(APIView):
    permission_classes = (IsApprovedBusinessUser,)

    @extend_schema(request=ReceiveBatchSerializer, responses={200: ReceiveBatchSerializer})
    @transaction.atomic
    def post(self, request):
        if request.user.role != 'FACTORY':
            return Response({'detail': 'Only factory users can receive batches.'}, status=403)
        serializer = ReceiveBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = TransferEvent.objects.select_for_update().filter(
            event_id=serializer.validated_data['event_id'],
            to_party=request.user,
            status=TransferEvent.Status.INITIATED,
        ).select_related('batch').first()
        if not event:
            return Response({'detail': 'Pending transfer not found.'}, status=404)
        if not accept_transfer(event, request.user, serializer.validated_data.get('remarks', event.remarks)):
            return Response(
                {'detail': 'The batch changed after this transfer was initiated; the transfer was cancelled.'},
                status=409,
            )
        return Response({'detail': 'Batch received by factory.', 'batch_id': event.batch.batch_id})


class ManufacturingCreateView(APIView):
    permission_classes = (IsApprovedBusinessUser,)

    @extend_schema(request=ManufacturingCreateSerializer, responses={201: ManufacturingRecordSerializer})
    @transaction.atomic
    def post(self, request):
        if request.user.role != 'FACTORY':
            return Response({'detail': 'Only factory users can create manufacturing records.'}, status=403)
        profile = getattr(request.user, 'factory_profile', None)
        if not profile:
            return Response({'detail': 'Factory profile is not configured.'}, status=404)
        serializer = ManufacturingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not data['input_batches']:
            return Response({'detail': 'At least one input batch is required.'}, status=400)
        total_input = Decimal('0')
        locked_batches = {}
        for item in data['input_batches']:
            batch = HerbBatch.objects.select_for_update().filter(
                batch_id=item['batch_id'],
                current_owner=request.user,
                status=HerbBatch.Status.SENT_TO_FACTORY,
            ).first()
            if not batch:
                return Response(
                    {'detail': f"Batch {item['batch_id']} is not eligible."},
                    status=400,
                )
            if item['quantity_used'] > batch.available_quantity:
                return Response(
                    {'detail': f"Quantity exceeds available quantity for {batch.batch_id}."},
                    status=400,
                )
            if item['quantity_used'] > 0 and batch.unit != data['unit']:
                return Response(
                    {'detail': f'Unit mismatch for batch {batch.batch_id}.'},
                    status=400,
                )
            total_input += item['quantity_used']
            locked_batches[batch.batch_id] = (batch, item['quantity_used'])

        record = ManufacturingRecord.objects.create(
            factory=profile,
            created_by=request.user,
            product_name=data['product_name'],
            process_date=data['process_date'],
            process_description=data['process_description'],
            facility_line=data.get('facility_line', ''),
            shift=data.get('shift', ''),
            standard_operating_procedure=data.get(
                'standard_operating_procedure',
                '',
            ),
            solvent_method=data.get('solvent_method', ''),
            target_yield_ratio=data.get('target_yield_ratio', ''),
            process_parameters=data.get('process_parameters', {}),
            quality_control_lead=data.get('quality_control_lead', ''),
            input_quantity=total_input,
            output_quantity=data['output_quantity'],
            unit=data['unit'],
            status=(
                ManufacturingRecord.Status.PLANNED
                if data['save_as_draft']
                else ManufacturingRecord.Status.COMPLETED
            ),
            remarks=data.get('remarks', ''),
        )
        for batch_id, (batch, quantity) in locked_batches.items():
            ManufacturingBatch.objects.create(
                manufacturing_record=record,
                herb_batch=batch,
                quantity_used=quantity,
                unit=data['unit'],
            )
            if not data['save_as_draft']:
                batch.available_quantity -= quantity
                batch.status = (
                    HerbBatch.Status.CONSUMED
                    if batch.available_quantity == 0
                    else HerbBatch.Status.IN_PROCESSING
                )
                batch.save(update_fields=['available_quantity', 'status', 'updated_at'])
        log_activity(
            request.user,
            'MANUFACTURING_CREATED',
            'ManufacturingRecord',
            record.manufacturing_id,
            f'Completed manufacturing record {record.product_name}',
        )
        return Response(ManufacturingRecordSerializer(record).data, status=201)


class CompleteManufacturingDraftView(APIView):
    permission_classes = (IsApprovedBusinessUser,)

    @extend_schema(
        request=ManufacturingActionSerializer,
        responses={200: ManufacturingRecordSerializer},
    )
    @transaction.atomic
    def post(self, request):
        if request.user.role != 'FACTORY':
            return Response({'detail': 'Only factory users can complete manufacturing.'}, status=403)
        serializer = ManufacturingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = getattr(request.user, 'factory_profile', None)
        record = ManufacturingRecord.objects.select_for_update().filter(
            manufacturing_id=serializer.validated_data['manufacturing_id'],
            factory=profile,
            status=ManufacturingRecord.Status.PLANNED,
        ).first()
        if not record:
            return Response({'detail': 'Planned manufacturing record not found.'}, status=404)

        links = list(
            record.input_batches.select_related('herb_batch').all()
        )
        batches = []
        for link in links:
            batch = HerbBatch.objects.select_for_update().filter(
                pk=link.herb_batch_id,
                current_owner=request.user,
                status=HerbBatch.Status.SENT_TO_FACTORY,
            ).first()
            if (
                not batch
                or batch.available_quantity < link.quantity_used
                or batch.unit != link.unit
                or link.unit != record.unit
            ):
                return Response(
                    {
                        'detail': (
                            f'Input batch {link.herb_batch.batch_id} is no longer '
                            'available in the required quantity and unit.'
                        )
                    },
                    status=409,
                )
            batches.append((batch, link.quantity_used))

        for batch, quantity in batches:
            batch.available_quantity -= quantity
            batch.status = (
                HerbBatch.Status.CONSUMED
                if batch.available_quantity == 0
                else HerbBatch.Status.IN_PROCESSING
            )
            batch.save(update_fields=['available_quantity', 'status', 'updated_at'])
        record.status = ManufacturingRecord.Status.COMPLETED
        record.save(update_fields=['status', 'updated_at'])
        log_activity(
            request.user,
            'MANUFACTURING_COMPLETED',
            'ManufacturingRecord',
            record.manufacturing_id,
            f'Completed manufacturing record {record.product_name}',
        )
        return Response(ManufacturingRecordSerializer(record).data)


class CancelManufacturingDraftView(APIView):
    permission_classes = (IsApprovedBusinessUser,)

    @extend_schema(
        request=ManufacturingActionSerializer,
        responses={200: ManufacturingRecordSerializer},
    )
    @transaction.atomic
    def post(self, request):
        if request.user.role != 'FACTORY':
            return Response({'detail': 'Only factory users can cancel manufacturing.'}, status=403)
        serializer = ManufacturingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = getattr(request.user, 'factory_profile', None)
        record = ManufacturingRecord.objects.select_for_update().filter(
            manufacturing_id=serializer.validated_data['manufacturing_id'],
            factory=profile,
            status=ManufacturingRecord.Status.PLANNED,
        ).first()
        if not record:
            return Response({'detail': 'Planned manufacturing record not found.'}, status=404)
        record.status = ManufacturingRecord.Status.CANCELLED
        record.save(update_fields=['status', 'updated_at'])
        return Response(ManufacturingRecordSerializer(record).data)


class ManufacturingListView(generics.ListAPIView):
    serializer_class = ManufacturingRecordSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            return ManufacturingRecord.objects.all()
        profile = getattr(self.request.user, 'factory_profile', None)
        if profile:
            return ManufacturingRecord.objects.filter(factory=profile)
        return ManufacturingRecord.objects.none()


class ManufacturingDetailView(generics.RetrieveAPIView):
    serializer_class = ManufacturingRecordSerializer
    permission_classes = (IsVerifiedActiveUser,)
    lookup_field = 'manufacturing_id'

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            return ManufacturingRecord.objects.all()
        profile = getattr(self.request.user, 'factory_profile', None)
        return ManufacturingRecord.objects.filter(factory=profile) if profile else ManufacturingRecord.objects.none()
