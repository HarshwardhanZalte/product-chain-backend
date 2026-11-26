from django.db.models import Q
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from collector.serializers import BusinessParticipantSerializer
from users.models import User
from users.permissions import IsVerifiedActiveUser


class BusinessParticipantListView(generics.ListAPIView):
    serializer_class = BusinessParticipantSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def get_queryset(self):
        role = self.request.query_params.get('role', '').upper()
        profile_specs = {
            User.Role.COLLECTOR: ('collector_profile', 'collector_name', None),
            User.Role.FACTORY: (
                'factory_profile',
                'factory_name',
                'registration_number',
            ),
            User.Role.LAB: (
                'lab_profile',
                'laboratory_name',
                'registration_number',
            ),
        }
        profile_spec = profile_specs.get(role)
        if not profile_spec:
            raise ValidationError({
                'role': 'Choose one of COLLECTOR, FACTORY, or LAB.'
            })

        profile_relation, name_field, registration_field = profile_spec
        queryset = User.objects.filter(
            role=role,
            is_active=True,
            is_email_verified=True,
            **{f'{profile_relation}__verification_status': 'VERIFIED'},
        ).exclude(pk=self.request.user.pk).select_related(profile_relation)

        search = self.request.query_params.get('search', '').strip()
        if search:
            search_filter = Q(name__icontains=search) | Q(
                **{f'{profile_relation}__{name_field}__icontains': search}
            )
            if registration_field:
                search_filter |= Q(
                    **{f'{profile_relation}__{registration_field}__icontains': search}
                )
            queryset = queryset.filter(search_filter)

        return queryset.order_by('name', 'pk')
