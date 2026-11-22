from datetime import date

from django.db import transaction
from django.db import models
from rest_framework import filters, generics, permissions, status
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsApprovedOrganizationUser, IsVerifiedActiveUser

from .models import FarmerProfile, HerbBatch
from .serializers import FarmerProfileSerializer, HerbBatchSerializer


def generate_batch_id():
    year = date.today().year
    prefix = f'ASH-{year}-'
    count = HerbBatch.objects.filter(batch_id__startswith=prefix).count() + 1
    while HerbBatch.objects.filter(batch_id=f'{prefix}{count:05d}').exists():
        count += 1
    return f'{prefix}{count:05d}'


class FarmerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = FarmerProfileSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def get_object(self):
        if not self.request.user.organization:
            raise NotFound('Organization is required for a farmer profile.')
        profile, _ = FarmerProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'organization': self.request.user.organization,
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
        if getattr(self.request.user, 'role', None) != 'FARMER':
            raise permissions.PermissionDenied('Only farmers can update this profile.')
        serializer.save()


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
    permission_classes = (IsApprovedOrganizationUser,)

    @transaction.atomic
    def perform_create(self, serializer):
        if self.request.user.role != 'FARMER':
            raise permissions.PermissionDenied('Only farmers can register batches.')
        profile = getattr(self.request.user, 'farmer_profile', None)
        if not profile:
            raise permissions.PermissionDenied('Farmer profile is required.')
        if not self.request.user.organization:
            raise permissions.PermissionDenied('Organization is required.')
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
        if self.request.user.organization:
            return HerbBatch.objects.filter(organization=self.request.user.organization)
        return HerbBatch.objects.none()


class BatchDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = HerbBatchSerializer
    permission_classes = (IsVerifiedActiveUser,)
    lookup_field = 'batch_id'

    def get_permissions(self):
        permission_class = (
            IsApprovedOrganizationUser
            if self.request.method not in permissions.SAFE_METHODS
            else IsVerifiedActiveUser
        )
        return [permission_class()]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.role == 'ADMIN':
            return HerbBatch.objects.all()
        if self.request.user.role == 'FARMER':
            return HerbBatch.objects.filter(farmer__user=self.request.user)
        return HerbBatch.objects.filter(organization=self.request.user.organization)

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
