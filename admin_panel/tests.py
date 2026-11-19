from django.test import TestCase

from users.models import User


class AdminPanelTests(TestCase):
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
