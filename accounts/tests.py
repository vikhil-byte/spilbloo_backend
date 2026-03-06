from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User


class AdminLoginAPITestCase(TestCase):
    """Tests for POST /api/user/admin-login/ (frontend admin login)."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("admin_login")
        self.admin_password = "adminpass123"
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password=self.admin_password,
            full_name="Admin User",
            role_id=User.ROLE_ADMIN,
        )
        self.staff_user = User.objects.create_user(
            email="staff@test.com",
            password="staffpass123",
            full_name="Staff User",
            role_id=User.ROLE_USER,
        )
        self.staff_user.is_staff = True
        self.staff_user.save()
        self.patient = User.objects.create_user(
            email="patient@test.com",
            password="patientpass123",
            full_name="Patient User",
            role_id=User.ROLE_PATIENT,
        )

    def test_admin_login_success_with_role_admin(self):
        """Admin user (role_id=0) gets tokens."""
        res = self.client.post(
            self.url,
            {"email": "admin@test.com", "password": self.admin_password},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn("access-token", data)
        self.assertIn("refresh-token", data)
        self.assertIn("detail", data)
        self.assertEqual(data["detail"]["email"], "admin@test.com")

    def test_admin_login_success_with_staff(self):
        """Staff user (is_staff=True) gets tokens."""
        res = self.client.post(
            self.url,
            {"email": "staff@test.com", "password": "staffpass123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn("access-token", data)
        self.assertEqual(data["detail"]["email"], "staff@test.com")

    def test_admin_login_accepts_username_key_as_email(self):
        """Backend accepts 'username' in body as email."""
        res = self.client.post(
            self.url,
            {"username": "admin@test.com", "password": self.admin_password},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access-token", res.json())

    def test_admin_login_fails_invalid_password(self):
        """Wrong password returns 401."""
        res = self.client.post(
            self.url,
            {"email": "admin@test.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res.json().get("error"), "Invalid email or password.")

    def test_admin_login_fails_nonexistent_email(self):
        """Unknown email returns 401."""
        res = self.client.post(
            self.url,
            {"email": "nobody@test.com", "password": "any"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res.json().get("error"), "Invalid email or password.")

    def test_admin_login_fails_non_admin_user(self):
        """Patient/non-admin user gets 403."""
        res = self.client.post(
            self.url,
            {"email": "patient@test.com", "password": "patientpass123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("not allowed", res.json().get("error", "").lower())

    def test_admin_login_fails_missing_email(self):
        """Missing email returns 400."""
        res = self.client.post(
            self.url,
            {"password": "somepass"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.json().get("error", "").lower())

    def test_admin_login_fails_missing_password(self):
        """Missing password returns 400."""
        res = self.client.post(
            self.url,
            {"email": "admin@test.com"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", res.json().get("error", "").lower())

    def test_admin_login_fails_empty_strings(self):
        """Empty email or password returns 400."""
        res = self.client.post(
            self.url,
            {"email": "", "password": "pass"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_method_not_allowed(self):
        """GET returns 405 (frontend uses POST)."""
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
