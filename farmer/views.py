from datetime import date

from django.db import transaction
from django.db import models
from rest_framework import filters, generics, status
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsApprovedBusinessUser, IsExpectedRole, IsVerifiedActiveUser
from users.services import update_profile_for_review

from collector.models import TransferEvent
from .models import FarmerProfile, FieldEvidence, HerbBatch
from .serializers import (
    FarmerProfileSerializer,
    FieldEvidenceSerializer,
    FieldEvidenceUploadSerializer,
    HerbBatchSerializer,
)


def generate_batch_id():
    year = date.today().year
    prefix = f'ASH-{year}-'
    count = HerbBatch.objects.filter(batch_id__startswith=prefix).count() + 1
    while HerbBatch.objects.filter(batch_id=f'{prefix}{count:05d}').exists():
        count += 1
    return f'{prefix}{count:05d}'


class FarmerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = FarmerProfileSerializer
    permission_classes = (IsVerifiedActiveUser, IsExpectedRole)
    expected_role = 'FARMER'

    def get_object(self):
        profile, _ = FarmerProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'farmer_name': self.request.user.name,
                'phone_number': self.request.user.phone_number,
                'address': '',
                'village': '',
                'district': '',
                'state': '',
                'pincode': '',
            },
        )
        return profile

    def perform_update(self, serializer):
        update_profile_for_review(serializer, self.request.user)


class FarmerDashboardView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        if request.user.role != 'FARMER':
            return Response({'detail': 'Only farmers can access this dashboard.'}, status=403)
        profile = getattr(request.user, 'farmer_profile', None)
        if not profile:
            return Response({'detail': 'Farmer profile is not configured.'}, status=404)
        batches = HerbBatch.objects.filter(farmer=profile)
        return Response({
            'total_batches': batches.count(),
            'registered': batches.filter(status='REGISTERED').count(),
            'approved': batches.filter(status='APPROVED').count(),
            'rejected': batches.filter(status='REJECTED').count(),
        })


class BatchRegisterView(generics.CreateAPIView):
    serializer_class = HerbBatchSerializer
    permission_classes = (IsApprovedBusinessUser,)

    @transaction.atomic
    def perform_create(self, serializer):
        if self.request.user.role != 'FARMER':
            raise permissions.PermissionDenied('Only farmers can register batches.')
        profile = getattr(self.request.user, 'farmer_profile', None)
        if not profile:
            raise permissions.PermissionDenied('Farmer profile is required.')
        quantity = serializer.validated_data['quantity']
        serializer.save(
            batch_id=generate_batch_id(),
            farmer=profile,
            current_owner=self.request.user,
            organization=self.request.user.organization,
            available_quantity=quantity,
        )


class BatchListView(generics.ListAPIView):
    serializer_class = HerbBatchSerializer
    permission_classes = (IsVerifiedActiveUser,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ('batch_id', 'herb_name', 'district', 'state')
    ordering_fields = ('created_at', 'quantity', 'status')

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.role == 'ADMIN':
            return HerbBatch.objects.all()
        if self.request.user.role == 'FARMER':
            return HerbBatch.objects.filter(farmer__user=self.request.user)
        return HerbBatch.objects.filter(current_owner=self.request.user)


class BatchDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = HerbBatchSerializer
    permission_classes = (IsVerifiedActiveUser,)
    lookup_field = 'batch_id'

    def get_permissions(self):
        permission_class = (
            IsApprovedBusinessUser
            if self.request.method not in permissions.SAFE_METHODS
            else IsVerifiedActiveUser
        )
        return [permission_class()]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.role == 'ADMIN':
            return HerbBatch.objects.all()
        if self.request.user.role == 'FARMER':
            return HerbBatch.objects.filter(farmer__user=self.request.user)
        return HerbBatch.objects.filter(current_owner=self.request.user)

    def perform_update(self, serializer):
        if self.request.user.role != 'FARMER':
            raise permissions.PermissionDenied('Only the farmer can update batch information.')
        if serializer.instance.status not in ('REGISTERED', 'COLLECTED'):
            raise permissions.PermissionDenied('Registered source information cannot be changed after transfer.')
        serializer.save()


class BatchHistoryView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

    @extend_schema(responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def get(self, request, batch_id):
        from collector.models import TransferEvent
        from factory.models import ManufacturingBatch
        from lab.models import LabTest
        from product.models import ProductBatch

        batch = HerbBatch.objects.filter(batch_id=batch_id).first()
        if not batch:
            return Response({'detail': 'Batch not found.'}, status=404)
        user = request.user
        is_admin = user.is_staff or user.role == 'ADMIN'
        is_participant = (
            batch.current_owner_id == user.pk
            or batch.farmer.user_id == user.pk
            or TransferEvent.objects.filter(batch=batch).filter(
                models.Q(from_party=user) | models.Q(to_party=user)
            ).exists()
            or LabTest.objects.filter(batch=batch, laboratory__user=user).exists()
            or ManufacturingBatch.objects.filter(
                herb_batch=batch,
                manufacturing_record__factory__user=user,
            ).exists()
            or ProductBatch.objects.filter(
                herb_batch=batch,
                product__manufacturer__user=user,
            ).exists()
        )
        if not (is_admin or is_participant):
            return Response({'detail': 'Batch not found.'}, status=404)

        history = [{
            'event_type': 'BATCH_REGISTERED',
            'event_id': batch.batch_id,
            'status': batch.status,
            'occurred_at': batch.created_at.isoformat(),
        }]
        history.extend({
            'event_type': 'TRANSFER',
            'event_id': str(event.event_id),
            'status': event.status,
            'from': event.from_party.name,
            'to': event.to_party.name,
            'quantity': str(event.quantity),
            'unit': batch.unit,
            'occurred_at': event.created_at.isoformat(),
        } for event in TransferEvent.objects.filter(batch=batch).select_related('from_party', 'to_party'))
        history.extend({
            'event_type': 'LAB_TEST',
            'event_id': str(test.test_id),
            'status': test.status,
            'laboratory': test.laboratory.laboratory_name,
            'occurred_at': test.created_at.isoformat(),
        } for test in LabTest.objects.filter(batch=batch).select_related('laboratory'))
        history.extend({
            'event_type': 'MANUFACTURING',
            'event_id': str(link.manufacturing_record.manufacturing_id),
            'status': link.manufacturing_record.status,
            'quantity_used': str(link.quantity_used),
            'unit': link.unit,
            'occurred_at': link.created_at.isoformat(),
        } for link in ManufacturingBatch.objects.filter(herb_batch=batch).select_related('manufacturing_record'))
        history.extend({
            'event_type': 'PRODUCT',
            'event_id': str(link.product.product_id),
            'status': link.product.status,
            'product_name': link.product.product_name,
            'occurred_at': link.created_at.isoformat(),
        } for link in ProductBatch.objects.filter(herb_batch=batch).select_related('product'))
        history.sort(key=lambda event: event['occurred_at'])
        return Response({
            'batch': HerbBatchSerializer(batch).data,
            'history': history,
        })


class BatchEvidenceView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def get_permissions(self):
        permission_class = (
            IsApprovedBusinessUser
            if self.request.method == 'POST'
            else IsVerifiedActiveUser
        )
        return [permission_class()]

    def get_batch(self, request, batch_id):
        batch = HerbBatch.objects.filter(batch_id=batch_id).first()
        if not batch:
            raise NotFound('Batch not found.')
        user = request.user
        if user.is_staff or user.role == 'ADMIN':
            return batch
        is_participant = (
            batch.current_owner_id == user.pk
            or batch.farmer.user_id == user.pk
            or TransferEvent.objects.filter(batch=batch).filter(
                models.Q(from_party=user) | models.Q(to_party=user)
            ).exists()
            or batch.laboratory_tests.filter(laboratory__user=user).exists()
            or batch.manufacturing_links.filter(
                manufacturing_record__factory__user=user
            ).exists()
        )
        if not is_participant:
            raise NotFound('Batch not found.')
        return batch

    @extend_schema(responses={200: FieldEvidenceSerializer(many=True)})
    def get(self, request, batch_id):
        batch = self.get_batch(request, batch_id)
        evidence = batch.field_evidence.all()
        return Response(
            FieldEvidenceSerializer(
                evidence,
                many=True,
                context={'request': request},
            ).data
        )

    @extend_schema(
        request=FieldEvidenceUploadSerializer,
        responses={201: FieldEvidenceSerializer},
    )
    @transaction.atomic
    def post(self, request, batch_id):
        batch = self.get_batch(request, batch_id)
        if request.user.role != 'FARMER' or batch.farmer.user_id != request.user.pk:
            raise permissions.PermissionDenied(
                'Only the batch farmer can upload field evidence.'
            )
        if batch.status not in (
            HerbBatch.Status.REGISTERED,
            HerbBatch.Status.COLLECTED,
        ):
            raise permissions.PermissionDenied(
                'Field evidence cannot be changed after the batch is transferred.'
            )
        if batch.field_evidence.count() >= 8:
            return Response(
                {'detail': 'A batch can have at most 8 evidence files.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = FieldEvidenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evidence = FieldEvidence.objects.create(
            batch=batch,
            **serializer.validated_data,
        )
        return Response(
            FieldEvidenceSerializer(
                evidence,
                context={'request': request},
            ).data,
            status=status.HTTP_201_CREATED,
        )
