from datetime import date

from django.db import transaction
from rest_framework import filters, generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsVerifiedActiveUser

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
    permission_classes = (IsVerifiedActiveUser,)

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
        if getattr(self.request.user, 'is_staff', False):
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

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
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


class BatchHistoryView(generics.ListAPIView):
    serializer_class = HerbBatchSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def get_queryset(self):
        batch_id = self.kwargs['batch_id']
        return HerbBatch.objects.filter(
            batch_id=batch_id,
            farmer__user=self.request.user,
        )
