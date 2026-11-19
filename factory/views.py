from decimal import Decimal

from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import OpenApiTypes, extend_schema

from farmer.models import HerbBatch
from users.permissions import IsVerifiedActiveUser
from users.services import log_activity

from .models import ManufacturingBatch, ManufacturingRecord
from .serializers import (
    ManufacturingCreateSerializer,
    ManufacturingRecordSerializer,
    ReceiveBatchSerializer,
    FactoryProfileSerializer,
)


class FactoryProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsVerifiedActiveUser,)
    serializer_class = FactoryProfileSerializer

    def get_object(self):
        if not self.request.user.organization:
            raise NotFound('Organization is required for a factory profile.')
        from .models import FactoryProfile
        profile, _ = FactoryProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'organization': self.request.user.organization,
                'factory_name': self.request.user.name,
                'registration_number': f'FAC-{self.request.user.user_id}',
                'address': '',
                'contact_number': self.request.user.phone_number,
            },
        )
        return profile



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
        return HerbBatch.objects.filter(status=HerbBatch.Status.APPROVED, available_quantity__gt=0)


class ReceiveBatchView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

    @extend_schema(request=ReceiveBatchSerializer, responses={200: ReceiveBatchSerializer})
    @transaction.atomic
    def post(self, request):
        if request.user.role != 'FACTORY':
            return Response({'detail': 'Only factory users can receive batches.'}, status=403)
        batch = HerbBatch.objects.select_for_update().filter(
            batch_id=request.data.get('batch_id'),
            status=HerbBatch.Status.APPROVED,
        ).first()
        if not batch:
            return Response({'detail': 'Approved batch not found.'}, status=404)
        batch.current_owner = request.user
        batch.status = HerbBatch.Status.SENT_TO_FACTORY
        batch.save(update_fields=['current_owner', 'status', 'updated_at'])
        return Response({'detail': 'Batch received by factory.', 'batch_id': batch.batch_id})


class ManufacturingCreateView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

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
                status__in=(HerbBatch.Status.APPROVED, HerbBatch.Status.SENT_TO_FACTORY),
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
            total_input += item['quantity_used']
            locked_batches[batch.batch_id] = (batch, item['quantity_used'])

        record = ManufacturingRecord.objects.create(
            factory=profile,
            created_by=request.user,
            product_name=data['product_name'],
            process_date=data['process_date'],
            process_description=data['process_description'],
            input_quantity=total_input,
            output_quantity=data['output_quantity'],
            unit=data['unit'],
            status=ManufacturingRecord.Status.IN_PROGRESS,
            remarks=data.get('remarks', ''),
        )
        for batch_id, (batch, quantity) in locked_batches.items():
            ManufacturingBatch.objects.create(
                manufacturing_record=record,
                herb_batch=batch,
                quantity_used=quantity,
                unit=data['unit'],
            )
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
            'MANUFACTURING_CREATED',
            'ManufacturingRecord',
            record.manufacturing_id,
            f'Completed manufacturing record {record.product_name}',
        )
        return Response(ManufacturingRecordSerializer(record).data, status=201)


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
