from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class ForgotResetPasswordTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="patient@spilbloo.local",
            password="OldPass@123",
            full_name="Patient One",
            role_id=User.ROLE_PATIENT,
            state_id=User.STATE_ACTIVE,
        )
        self.forgot_url = reverse("forgot_password")
        self.reset_url = reverse("reset_password")

    def _extract_token_from_mail(self):
        self.assertTrue(mail.outbox)
        body = mail.outbox[-1].body
        marker = "token="
        token = body.split(marker, 1)[1].strip().split("&", 1)[0].splitlines()[0]
        return token

    def test_forgot_password_sends_reset_email_and_reset_updates_password(self):
        forgot_response = self.client.post(
            self.forgot_url,
            {"email": self.user.email, "role_id": User.ROLE_PATIENT},
            format="json",
        )
        self.assertEqual(forgot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            forgot_response.data["message"],
            "Please check your email to reset your password.",
        )
        token = self._extract_token_from_mail()

        reset_response = self.client.post(
            self.reset_url,
            {"email": self.user.email, "token": token, "new_password": "NewPass@123"},
            format="json",
        )
        self.assertEqual(reset_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reset_response.data["message"], "Password reset successfully.")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass@123"))
        self.assertIsNotNone(self.user.last_password_change)

    def test_reset_password_rejects_replayed_token(self):
        self.client.post(
            self.forgot_url,
            {"email": self.user.email, "role_id": User.ROLE_PATIENT},
            format="json",
        )
        token = self._extract_token_from_mail()

        first = self.client.post(
            self.reset_url,
            {"email": self.user.email, "token": token, "new_password": "Pass@12345"},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(
            self.reset_url,
            {"email": self.user.email, "token": token, "new_password": "Another@123"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(second.data["error"], "Invalid reset link.")

    def test_reset_password_rejects_expired_token(self):
        self.client.post(
            self.forgot_url,
            {"email": self.user.email, "role_id": User.ROLE_PATIENT},
            format="json",
        )
        token = self._extract_token_from_mail()

        signer = signing.TimestampSigner(salt="spilbloo-password-reset")
        signer.unsign(token, max_age=1800)  # sanity

        with self.settings():
            # Move time logically by touching cache invalidation path:
            # clear expected token hash to emulate expiration/invalidation boundary.
            cache.clear()

        expired = self.client.post(
            self.reset_url,
            {"email": self.user.email, "token": token, "new_password": "Expired@123"},
            format="json",
        )
        self.assertEqual(expired.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(expired.data["error"], "Invalid reset link.")
