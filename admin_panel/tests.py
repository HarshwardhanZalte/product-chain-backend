from django.test import TestCase

from farmer.models import FarmerProfile
from users.models import ActivityLog, User


class AdminPanelTests(TestCase):
    def create_farmer(self, email='farmer@example.com', is_email_verified=True):
        user = User.objects.create_user(
            email=email,
            password='StrongUserPass123',
            name='Test Farmer',
            role=User.Role.FARMER,
            is_email_verified=is_email_verified,
        )
        profile = FarmerProfile.objects.create(
            user=user,
            farmer_name='Test Farmer',
            phone_number='9000000000',
            address='Farm Road',
            village='Sample Village',
            district='Sample District',
            state='Sample State',
            pincode='123456',
        )
        return user, profile

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get('/panel/')
        self.assertRedirects(
            response,
            '/panel/login/?next=/panel/',
            fetch_redirect_response=False,
        )

    def test_staff_user_can_open_dashboard(self):
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='StrongAdminPass123',
        )
        self.client.force_login(user)
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 200)

    def test_user_review_list_filters_pending_role_profiles(self):
        admin = User.objects.create_superuser(
            email='reviewer@example.com',
            password='StrongAdminPass123',
        )
        farmer, _ = self.create_farmer()
        self.client.force_login(admin)

        response = self.client.get('/panel/users/?status=PENDING')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, farmer.email)
        self.assertContains(response, 'Pending role reviews')
        self.assertContains(response, 'Review')

    def test_admin_can_approve_profile_and_action_is_audited(self):
        admin = User.objects.create_superuser(
            email='reviewer@example.com',
            password='StrongAdminPass123',
        )
        farmer, profile = self.create_farmer()
        self.client.force_login(admin)

        response = self.client.post(
            f'/panel/users/{farmer.user_id}/',
            {'action': 'approve_profile', 'note': 'Identity details reviewed.'},
        )

        self.assertRedirects(response, f'/panel/users/{farmer.user_id}/')
        profile.refresh_from_db()
        self.assertEqual(profile.verification_status, 'VERIFIED')
        activity = ActivityLog.objects.get(action='BUSINESS_PROFILE_APPROVED')
        self.assertEqual(activity.user, admin)
        self.assertIn('Identity details reviewed.', activity.description)

    def test_admin_can_reject_profile_and_audit_the_reason(self):
        admin = User.objects.create_superuser(
            email='reviewer@example.com',
            password='StrongAdminPass123',
        )
        farmer, profile = self.create_farmer()
        self.client.force_login(admin)

        response = self.client.post(
            f'/panel/users/{farmer.user_id}/',
            {'action': 'reject_profile', 'note': 'Registration details do not match.'},
        )

        self.assertRedirects(response, f'/panel/users/{farmer.user_id}/')
        profile.refresh_from_db()
        self.assertEqual(profile.verification_status, 'REJECTED')
        activity = ActivityLog.objects.get(action='BUSINESS_PROFILE_REJECTED')
        self.assertIn('Registration details do not match.', activity.description)

    def test_admin_cannot_review_profile_before_email_is_verified(self):
        admin = User.objects.create_superuser(
            email='reviewer@example.com',
            password='StrongAdminPass123',
        )
        farmer, profile = self.create_farmer(is_email_verified=False)
        self.client.force_login(admin)

        response = self.client.post(
            f'/panel/users/{farmer.user_id}/',
            {'action': 'approve_profile'},
        )

        self.assertRedirects(response, f'/panel/users/{farmer.user_id}/')
        profile.refresh_from_db()
        self.assertEqual(profile.verification_status, 'PENDING')
        self.assertFalse(ActivityLog.objects.filter(
            action='BUSINESS_PROFILE_APPROVED'
        ).exists())

    def test_profile_detail_explains_when_a_role_profile_is_missing(self):
        admin = User.objects.create_superuser(
            email='reviewer@example.com',
            password='StrongAdminPass123',
        )
        farmer = User.objects.create_user(
            email='no-profile@example.com',
            password='StrongUserPass123',
            name='No Profile',
            role=User.Role.FARMER,
        )
        self.client.force_login(admin)

        response = self.client.get(f'/panel/users/{farmer.user_id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Role profile not submitted')
        self.assertNotContains(response, 'Approve profile')

    def test_logout_requires_post(self):
        admin = User.objects.create_superuser(
            email='reviewer@example.com',
            password='StrongAdminPass123',
        )
        self.client.force_login(admin)

        response = self.client.get('/panel/logout/')

        self.assertEqual(response.status_code, 405)

    def test_builtin_admin_uses_django_admin_templates(self):
        user = User.objects.create_superuser(
            email='django-admin@example.com',
            password='StrongAdminPass123',
        )
        self.client.force_login(user)

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django administration')
        self.assertNotContains(response, 'Traceability Admin')
