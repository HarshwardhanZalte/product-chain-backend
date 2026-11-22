from datetime import date

from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import OpenApiTypes, extend_schema

from farmer.models import HerbBatch
from users.permissions import (
    IsApprovedOrganizationUser,
    IsVerifiedActiveUser,
    has_approved_business_identity,
)
from users.services import log_activity
from .services import accept_transfer

from .models import CollectorProfile, TransferEvent
from .serializers import (
    TransferActionSerializer,
    TransferCreateSerializer,
    TransferEventSerializer,
    CollectorProfileSerializer,
)


class CollectorProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsVerifiedActiveUser,)
    serializer_class = CollectorProfileSerializer

    def get_object(self):
        if not self.request.user.organization:
            raise NotFound('Organization is required for a collector profile.')
        profile, _ = CollectorProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'organization': self.request.user.organization,
                'collector_name': self.request.user.name,
                'phone_number': self.request.user.phone_number,
                'address': '',
            },
        )
        return profile



class AvailableBatchesView(generics.ListAPIView):
    serializer_class = __import__('farmer.serializers', fromlist=['HerbBatchSerializer']).HerbBatchSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def get_queryset(self):
        if getattr(self.request.user, 'collector_profile', None) is None:
            return HerbBatch.objects.none()
        return HerbBatch.objects.exclude(status='REJECTED').exclude(status='CONSUMED')


class InitiateTransferView(APIView):
    permission_classes = (IsApprovedOrganizationUser,)

    @extend_schema(request=TransferCreateSerializer, responses={201: TransferEventSerializer})
    @transaction.atomic
    def post(self, request):
        serializer = TransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        batch = HerbBatch.objects.select_for_update().filter(
            pk=data['batch'].pk,
        ).first()
        if not batch or batch.current_owner_id != request.user.id:
            return Response({'detail': 'You do not own this batch.'}, status=403)
        recipient_role = {
            'FARMER': 'COLLECTOR',
            'COLLECTOR': 'FACTORY',
        }.get(request.user.role)
        if not recipient_role or data['to_party'].role != recipient_role:
            return Response({'detail': 'Transfer target role is not allowed.'}, status=400)
        if data['to_party'].pk == request.user.pk:
            return Response({'detail': 'A user cannot transfer a batch to themselves.'}, status=400)
        if not has_approved_business_identity(data['to_party']):
            return Response({'detail': 'Transfer target must be an approved, active business user.'}, status=400)
        if data['quantity'] != batch.available_quantity:
            return Response(
                {'detail': 'Transfers must include the full available batch quantity until batch splitting is supported.'},
                status=400,
            )
        allowed_statuses = {
            'FARMER': (
                HerbBatch.Status.REGISTERED,
                HerbBatch.Status.COLLECTED,
                HerbBatch.Status.APPROVED,
            ),
            'COLLECTOR': (
                HerbBatch.Status.WITH_COLLECTOR,
                HerbBatch.Status.APPROVED,
            ),
        }.get(request.user.role, ())
        if batch.status not in allowed_statuses:
            return Response({'detail': 'This batch cannot be transferred.'}, status=400)
        if recipient_role == 'FACTORY':
            latest_test = batch.laboratory_tests.order_by('-created_at').first()
            if not latest_test or latest_test.status != 'APPROVED':
                return Response(
                    {'detail': 'A batch requires an approved latest laboratory test before factory transfer.'},
                    status=400,
                )
        event = TransferEvent.objects.create(
            batch=batch,
            from_party=request.user,
            to_party=data['to_party'],
            from_organization=request.user.organization,
            to_organization=data['to_party'].organization,
            quantity=data['quantity'],
            transfer_date=date.today(),
            transfer_location=data['transfer_location'],
            remarks=data.get('remarks', ''),
            status=TransferEvent.Status.INITIATED,
            recorded_by=request.user,
        )
        return Response(TransferEventSerializer(event).data, status=201)


class PendingTransferView(generics.ListAPIView):
    serializer_class = TransferEventSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def get_queryset(self):
        return TransferEvent.objects.filter(
            to_party=self.request.user,
            status=TransferEvent.Status.INITIATED,
        )


class AcceptTransferView(APIView):
    permission_classes = (IsApprovedOrganizationUser,)

    @extend_schema(request=TransferActionSerializer, responses={200: TransferEventSerializer})
    @transaction.atomic
    def post(self, request):
        serializer = TransferActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = TransferEvent.objects.select_for_update().filter(
            event_id=serializer.validated_data['event_id'],
            to_party=request.user,
            status=TransferEvent.Status.INITIATED,
        ).select_related('batch').first()
        if not event:
            return Response({'detail': 'Pending transfer not found.'}, status=404)
        if not accept_transfer(
            event,
            request.user,
            serializer.validated_data.get('remarks', event.remarks),
        ):
            return Response(
                {'detail': 'The batch changed after this transfer was initiated; the transfer was cancelled.'},
                status=409,
            )
        log_activity(
            request.user,
            'TRANSFER_ACCEPTED',
            'TransferEvent',
            event.event_id,
            f'{request.user.role.title()} accepted batch {event.batch.batch_id}',
            request.META.get('REMOTE_ADDR'),
        )
        return Response(TransferEventSerializer(event).data)


class RejectTransferView(APIView):
    permission_classes = (IsApprovedOrganizationUser,)

    @extend_schema(request=TransferActionSerializer, responses={200: TransferEventSerializer})
    @transaction.atomic
    def post(self, request):
        serializer = TransferActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = TransferEvent.objects.select_for_update().filter(
            event_id=serializer.validated_data['event_id'],
            to_party=request.user,
            status=TransferEvent.Status.INITIATED,
        ).first()
        if not event:
            return Response({'detail': 'Pending transfer not found.'}, status=404)
        event.status = TransferEvent.Status.REJECTED
        event.remarks = serializer.validated_data.get('remarks', event.remarks)
        event.save(update_fields=['status', 'remarks', 'updated_at'])
        return Response(TransferEventSerializer(event).data)


class TransferHistoryView(generics.ListAPIView):
    serializer_class = TransferEventSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def get_queryset(self):
        return TransferEvent.objects.filter(
            from_party=self.request.user
        ) | TransferEvent.objects.filter(to_party=self.request.user)


class CollectorDashboardView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        if request.user.role != 'COLLECTOR':
            return Response({'detail': 'Only collectors can access this dashboard.'}, status=403)
        return Response({
            'pending_transfers': TransferEvent.objects.filter(
                to_party=request.user,
                status=TransferEvent.Status.INITIATED,
            ).count(),
            'accepted_transfers': TransferEvent.objects.filter(
                to_party=request.user,
                status=TransferEvent.Status.ACCEPTED,
            ).count(),
        })
