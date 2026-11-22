from rest_framework.permissions import BasePermission


class IsAdminUserRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or getattr(request.user, 'role', None) == 'ADMIN')
        )


class IsVerifiedActiveUser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_email_verified
        )


class IsApprovedOrganizationUser(IsVerifiedActiveUser):
    def has_permission(self, request, view):
        return has_approved_business_identity(request.user) and super().has_permission(
            request, view
        )


def has_approved_business_identity(user):
    if not user or not user.is_authenticated or not user.is_active or not user.is_email_verified:
        return False
    organization = getattr(user, 'organization', None)
    if not organization or organization.verification_status != 'VERIFIED':
        return False
    profile_relation = {
        'FARMER': 'farmer_profile',
        'COLLECTOR': 'collector_profile',
        'LAB': 'lab_profile',
        'FACTORY': 'factory_profile',
    }.get(user.role)
    if profile_relation is None:
        return False
    profile = getattr(user, profile_relation, None)
    return bool(profile and profile.verification_status == 'VERIFIED')
