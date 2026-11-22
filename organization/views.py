from django.db import transaction
from rest_framework import filters, generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from users.permissions import IsAdminUserRole, IsVerifiedActiveUser
from users.models import User

from .models import Organization
from .serializers import OrganizationSerializer


class OrganizationCreateView(generics.CreateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def perform_create(self, serializer):
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=self.request.user.pk)
            if user.organization_id:
                raise ValidationError({'detail': 'You already belong to an organization.'})
            expected_type = {
                User.Role.FARMER: Organization.OrganizationType.FARMER_GROUP,
                User.Role.COLLECTOR: Organization.OrganizationType.COLLECTOR,
                User.Role.LAB: Organization.OrganizationType.TESTING_LAB,
                User.Role.FACTORY: Organization.OrganizationType.MANUFACTURER,
            }.get(user.role)
            if not expected_type or serializer.validated_data['organization_type'] != expected_type:
                raise ValidationError({
                    'organization_type': 'Organization type must match the account role.'
                })
            organization = serializer.save(
                verification_status=Organization.VerificationStatus.PENDING
            )
            user.organization = organization
            user.save(update_fields=['organization', 'updated_at'])


class OrganizationListView(generics.ListAPIView):
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ('organization_name', 'registration_number', 'district')
    ordering_fields = ('organization_name', 'created_at')
    permission_classes = (IsVerifiedActiveUser,)

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.role == User.Role.ADMIN:
            return Organization.objects.all()
        return Organization.objects.filter(users=self.request.user)


class OrganizationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OrganizationSerializer
    lookup_field = 'organization_id'

    def get_permissions(self):
        permission_class = IsAdminUserRole if self.request.method not in permissions.SAFE_METHODS else IsVerifiedActiveUser
        return [permission_class()]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.role == User.Role.ADMIN:
            return Organization.objects.all()
        return Organization.objects.filter(users=self.request.user)


class MyOrganizationView(generics.RetrieveAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def get_object(self):
        organization = getattr(self.request.user, 'organization', None)
        if organization is None:
            return None
        return organization

    def retrieve(self, request, *args, **kwargs):
        organization = self.get_object()
        if organization is None:
            return Response({'detail': 'No organization is assigned.'}, status=404)
        return Response(self.get_serializer(organization).data)
