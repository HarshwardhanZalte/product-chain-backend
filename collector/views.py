from datetime import date

from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import OpenApiTypes, extend_schema

from farmer.models import HerbBatch
from users.permissions import IsVerifiedActiveUser
from users.services import log_activity

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
    permission_classes = (IsVerifiedActiveUser,)

    @extend_schema(request=TransferCreateSerializer, responses={201: TransferEventSerializer})
    @transaction.atomic
    def post(self, request):
        serializer = TransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        batch = data['batch']
        if request.user.role != 'FARMER' or batch.current_owner_id != request.user.id:
            return Response({'detail': 'You do not own this batch.'}, status=403)
        if data['to_party'].role != 'COLLECTOR':
            return Response({'detail': 'Transfer target must be a collector.'}, status=400)
        if not data['to_party'].organization:
            return Response({'detail': 'Collector organization is required.'}, status=400)
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
    permission_classes = (IsVerifiedActiveUser,)

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
        event.status = TransferEvent.Status.ACCEPTED
        event.remarks = serializer.validated_data.get('remarks', event.remarks)
        event.save(update_fields=['status', 'remarks', 'updated_at'])
        batch = event.batch
        batch.current_owner = request.user
        batch.status = HerbBatch.Status.WITH_COLLECTOR
        batch.save(update_fields=['current_owner', 'status', 'updated_at'])
        log_activity(
            request.user,
            'TRANSFER_ACCEPTED',
            'TransferEvent',
            event.event_id,
            f'Collector accepted batch {batch.batch_id}',
            request.META.get('REMOTE_ADDR'),
        )
        return Response(TransferEventSerializer(event).data)


class RejectTransferView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

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
