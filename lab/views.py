import hashlib

from django.db import models, transaction
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import OpenApiTypes, extend_schema

from farmer.models import HerbBatch
from users.permissions import IsApprovedBusinessUser, IsExpectedRole, IsVerifiedActiveUser
from users.services import log_activity, update_profile_for_review

from .models import LabMeasurement, LabProfile, LabTest
from .serializers import (
    LabTestActionSerializer,
    LabTestCreateSerializer,
    LabTestDetailSerializer,
    LabTestResultSerializer,
    LabTestSerializer,
    LabProfileSerializer,
)

def is_current_test(test):
    return (
        test.status in (LabTest.Status.PENDING, LabTest.Status.UNDER_TESTING)
        and test.batch.status in (HerbBatch.Status.SENT_TO_LAB, HerbBatch.Status.UNDER_TESTING)
        and test.batch.current_owner_id == test.submitted_by_id
    )


class LabProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsVerifiedActiveUser, IsExpectedRole)
    expected_role = 'LAB'
    serializer_class = LabProfileSerializer

    def get_object(self):
        profile, _ = LabProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'laboratory_name': self.request.user.name,
                'registration_number': f'LAB-{self.request.user.user_id}',
                'address': '',
                'contact_number': self.request.user.phone_number,
            },
        )
        return profile

    def perform_update(self, serializer):
        update_profile_for_review(serializer, self.request.user)


class LabDashboardView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        if request.user.role != 'LAB':
            return Response({'detail': 'Only laboratory users can access this dashboard.'}, status=403)
        profile = getattr(request.user, 'lab_profile', None)
        if not profile:
            return Response({'detail': 'Laboratory profile is not configured.'}, status=404)
        tests = LabTest.objects.filter(laboratory=profile)
        return Response({
            'pending': tests.filter(status='PENDING').count(),
            'under_testing': tests.filter(status='UNDER_TESTING').count(),
            'approved': tests.filter(status='APPROVED').count(),
            'rejected': tests.filter(status='REJECTED').count(),
        })


class SubmitForTestingView(APIView):
    permission_classes = (IsApprovedBusinessUser,)

    @extend_schema(request=LabTestCreateSerializer, responses={201: LabTestSerializer})
    @transaction.atomic
    def post(self, request):
        serializer = LabTestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        batch = HerbBatch.objects.select_for_update().filter(
            batch_id=data['batch_id'],
            current_owner=request.user,
        ).first()
        if not batch:
            return Response({'detail': 'Owned batch not found.'}, status=404)
        if batch.status not in (
            HerbBatch.Status.REGISTERED,
            HerbBatch.Status.COLLECTED,
            HerbBatch.Status.WITH_COLLECTOR,
            HerbBatch.Status.APPROVED,
        ):
            return Response({'detail': 'This batch is not eligible for laboratory testing.'}, status=400)
        laboratory = LabProfile.objects.filter(lab_id=data['laboratory_id']).first()
        if not laboratory:
            return Response({'detail': 'Laboratory not found.'}, status=404)
        if laboratory.verification_status != 'VERIFIED':
            return Response({'detail': 'The laboratory is not approved to receive samples.'}, status=400)
        test = LabTest.objects.create(
            batch=batch,
            laboratory=laboratory,
            submitted_by=request.user,
            test_date=data['test_date'],
            test_type=data['test_type'],
            test_parameters=data.get('test_parameters', {}),
        )
        batch.status = HerbBatch.Status.SENT_TO_LAB
        batch.save(update_fields=['status', 'updated_at'])
        return Response(LabTestSerializer(test).data, status=201)


class LabRequestsView(generics.ListAPIView):
    serializer_class = LabTestSerializer
    permission_classes = (IsVerifiedActiveUser,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ('test_type', 'batch__batch_id', 'batch__herb_name')
    ordering_fields = ('status', 'test_date', 'created_at')

    def get_queryset(self):
        profile = getattr(self.request.user, 'lab_profile', None)
        if not profile:
            return LabTest.objects.none()
        return LabTest.objects.filter(laboratory=profile)


class RecordTestResultView(APIView):
    permission_classes = (IsApprovedBusinessUser,)

    @extend_schema(request=LabTestResultSerializer, responses={200: LabTestSerializer})
    @transaction.atomic
    def post(self, request):
        if request.user.role != 'LAB':
            return Response({'detail': 'Only laboratory users can submit results.'}, status=403)
        serializer = LabTestResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        profile = getattr(request.user, 'lab_profile', None)
        test = LabTest.objects.select_for_update().filter(
            test_id=data['test_id'],
            laboratory=profile,
        ).select_related('batch').first()
        if not test:
            return Response({'detail': 'Assigned test not found.'}, status=404)
        if not is_current_test(test):
            return Response({'detail': 'This test is no longer active for the current batch owner.'}, status=400)
        for field in ('test_parameters', 'test_result', 'result_summary', 'remarks'):
            if field in data:
                setattr(test, field, data[field])
        if 'measurements' in data:
            test.measurements.all().delete()
            LabMeasurement.objects.bulk_create([
                LabMeasurement(test=test, **measurement)
                for measurement in data['measurements']
            ])
        if 'certificate_file' in data:
            uploaded = data['certificate_file']
            uploaded.seek(0)
            test.certificate_file = uploaded
            test.certificate_hash = hashlib.sha256(uploaded.read()).hexdigest()
            uploaded.seek(0)
        test.status = LabTest.Status.UNDER_TESTING
        test.save()
        test.batch.status = HerbBatch.Status.UNDER_TESTING
        test.batch.save(update_fields=['status', 'updated_at'])
        return Response(LabTestSerializer(test).data)


class ApproveTestView(APIView):
    permission_classes = (IsApprovedBusinessUser,)

    @extend_schema(request=LabTestActionSerializer, responses={200: LabTestSerializer})
    @transaction.atomic
    def post(self, request):
        if request.user.role != 'LAB':
            return Response({'detail': 'Only laboratory users can approve tests.'}, status=403)
        serializer = LabTestActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = getattr(request.user, 'lab_profile', None)
        test = LabTest.objects.select_for_update().filter(
            test_id=serializer.validated_data['test_id'],
            laboratory=profile,
        ).select_related('batch').first()
        if not test:
            return Response({'detail': 'Assigned test not found.'}, status=404)
        if (
            not is_current_test(test)
            or test.status != LabTest.Status.UNDER_TESTING
            or not (test.test_result.strip() or test.measurements.exists())
        ):
            return Response(
                {'detail': 'An active test with a recorded result is required for approval.'},
                status=400,
            )
        test.status = LabTest.Status.APPROVED
        test.reviewed_by = request.user
        test.remarks = serializer.validated_data.get('remarks', test.remarks)
        test.save(update_fields=['status', 'reviewed_by', 'remarks', 'updated_at'])
        test.batch.status = HerbBatch.Status.APPROVED
        test.batch.save(update_fields=['status', 'updated_at'])
        log_activity(
            request.user,
            'LAB_TEST_APPROVED',
            'LabTest',
            test.test_id,
            f'Approved test for batch {test.batch.batch_id}',
        )
        return Response(LabTestSerializer(test).data)


class RejectTestView(APIView):
    permission_classes = (IsApprovedBusinessUser,)

    @extend_schema(request=LabTestActionSerializer, responses={200: LabTestSerializer})
    @transaction.atomic
    def post(self, request):
        if request.user.role != 'LAB':
            return Response({'detail': 'Only laboratory users can reject tests.'}, status=403)
        serializer = LabTestActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = getattr(request.user, 'lab_profile', None)
        test = LabTest.objects.select_for_update().filter(
            test_id=serializer.validated_data['test_id'],
            laboratory=profile,
        ).select_related('batch').first()
        if not test:
            return Response({'detail': 'Assigned test not found.'}, status=404)
        if not is_current_test(test):
            return Response({'detail': 'This test is no longer active for the current batch owner.'}, status=400)
        test.status = LabTest.Status.REJECTED
        test.reviewed_by = request.user
        test.remarks = serializer.validated_data.get('remarks', test.remarks)
        test.save(update_fields=['status', 'reviewed_by', 'remarks', 'updated_at'])
        test.batch.status = HerbBatch.Status.REJECTED
        test.batch.save(update_fields=['status', 'updated_at'])
        return Response(LabTestSerializer(test).data)


class LabTestHistoryView(generics.ListAPIView):
    serializer_class = LabTestSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def get_queryset(self):
        profile = getattr(self.request.user, 'lab_profile', None)
        if profile:
            return LabTest.objects.filter(laboratory=profile).select_related(
                'batch',
                'laboratory',
            ).prefetch_related('measurements')
        return LabTest.objects.filter(
            batch__farmer__user=self.request.user
        ).select_related(
            'batch',
            'laboratory',
        ).prefetch_related('measurements')


class LabTestDetailView(generics.RetrieveAPIView):
    serializer_class = LabTestDetailSerializer
    permission_classes = (IsVerifiedActiveUser,)
    lookup_field = 'test_id'

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'ADMIN':
            return LabTest.objects.select_related(
                'batch',
                'laboratory',
                'submitted_by',
                'reviewed_by',
            ).prefetch_related('measurements')
        return LabTest.objects.filter(
            models.Q(laboratory__user=user) | models.Q(submitted_by=user)
        ).select_related(
            'batch',
            'laboratory',
            'submitted_by',
            'reviewed_by',
        ).prefetch_related('measurements')
