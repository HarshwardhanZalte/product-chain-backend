from rest_framework import filters, generics, permissions
from rest_framework.response import Response

from users.permissions import IsAdminUserRole

from .models import Organization
from .serializers import OrganizationSerializer


class OrganizationCreateView(generics.CreateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(verification_status=Organization.VerificationStatus.PENDING)


class OrganizationListView(generics.ListAPIView):
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ('organization_name', 'registration_number', 'district')
    ordering_fields = ('organization_name', 'created_at')

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            return Organization.objects.all()
        return Organization.objects.filter(users=self.request.user)


class OrganizationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OrganizationSerializer
    lookup_field = 'organization_id'

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            return Organization.objects.all()
        return Organization.objects.filter(users=self.request.user)


class MyOrganizationView(generics.RetrieveAPIView):
    serializer_class = OrganizationSerializer

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
