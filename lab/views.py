import hashlib

from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import OpenApiTypes, extend_schema

from farmer.models import HerbBatch
from users.permissions import IsVerifiedActiveUser
from users.services import log_activity

from .models import LabProfile, LabTest
from .serializers import (
    LabTestActionSerializer,
    LabTestCreateSerializer,
    LabTestResultSerializer,
    LabTestSerializer,
    LabProfileSerializer,
)


class LabProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsVerifiedActiveUser,)
    serializer_class = LabProfileSerializer

    def get_object(self):
        if not self.request.user.organization:
            raise NotFound('Organization is required for a laboratory profile.')
        profile, _ = LabProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'organization': self.request.user.organization,
                'laboratory_name': self.request.user.name,
                'registration_number': f'LAB-{self.request.user.user_id}',
                'address': '',
                'contact_number': self.request.user.phone_number,
            },
        )
        return profile



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
    permission_classes = (IsVerifiedActiveUser,)

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
        laboratory = LabProfile.objects.filter(lab_id=data['laboratory_id']).first()
        if not laboratory:
            return Response({'detail': 'Laboratory not found.'}, status=404)
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

    def get_queryset(self):
        profile = getattr(self.request.user, 'lab_profile', None)
        if not profile:
            return LabTest.objects.none()
        return LabTest.objects.filter(laboratory=profile)


class RecordTestResultView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

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
        for field in ('test_parameters', 'test_result', 'result_summary', 'remarks'):
            if field in data:
                setattr(test, field, data[field])
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
    permission_classes = (IsVerifiedActiveUser,)

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
    permission_classes = (IsVerifiedActiveUser,)

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
            return LabTest.objects.filter(laboratory=profile)
        return LabTest.objects.filter(batch__farmer__user=self.request.user)
