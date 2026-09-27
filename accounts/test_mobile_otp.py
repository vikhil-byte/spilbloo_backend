import json
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.sms_service.base import BaseSMSAdapter
from core.sms_service.msg91_adapter import MSG91SMSAdapter
from core.sms_service.console_adapter import ConsoleSMSAdapter
from core.sms_service.factory import get_sms_client
from accounts.views import _set_phone_otp, _get_phone_otp

User = get_user_model()


class SMSAdapterPatternTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_phone_number_normalization(self):
        adapter = ConsoleSMSAdapter()
        self.assertEqual(adapter.normalize_phone_number("9876543210"), "919876543210")
        self.assertEqual(adapter.normalize_phone_number("+91 98765-43210"), "919876543210")
        self.assertEqual(adapter.normalize_phone_number("919876543210"), "919876543210")
        self.assertEqual(adapter.format_e164("9876543210"), "+919876543210")
        self.assertEqual(adapter.format_e164("+919876543210"), "+919876543210")

    def test_console_adapter(self):
        adapter = ConsoleSMSAdapter()
        self.assertTrue(adapter.send_otp("9876543210", "4321"))
        self.assertTrue(adapter.send_sms("9876543210", "Test message"))

    @override_settings(SMS_SERVICE_PROVIDER="console")
    def test_factory_returns_console_adapter(self):
        client = get_sms_client()
        self.assertIsInstance(client, ConsoleSMSAdapter)

    @override_settings(SMS_SERVICE_PROVIDER="msg91", MSG91_AUTH_KEY="test_key_123", MSG91_OTP_TEMPLATE_ID="tpl_otp_123")
    def test_factory_returns_msg91_adapter(self):
        client = get_sms_client()
        self.assertIsInstance(client, MSG91SMSAdapter)
        self.assertEqual(client.auth_key, "test_key_123")
        self.assertEqual(client.otp_template_id, "tpl_otp_123")

    @patch("requests.post")
    def test_msg91_adapter_send_otp_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"type": "success", "message": "OTP sent successfully"}'
        mock_response.json.return_value = {"type": "success", "message": "OTP sent successfully"}
        mock_post.return_value = mock_response

        adapter = MSG91SMSAdapter(auth_key="test_auth_key", otp_template_id="template_123")
        result = adapter.send_otp("9876543210", "5678")

        self.assertTrue(result)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["params"]["mobile"], "919876543210")
        self.assertEqual(call_kwargs["params"]["otp"], "5678")
        self.assertEqual(call_kwargs["params"]["template_id"], "template_123")
        self.assertEqual(call_kwargs["headers"]["authkey"], "test_auth_key")

    @patch("requests.post")
    def test_msg91_adapter_send_otp_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"type": "error", "message": "Invalid Template ID"}'
        mock_response.json.return_value = {"type": "error", "message": "Invalid Template ID"}
        mock_post.return_value = mock_response

        adapter = MSG91SMSAdapter(auth_key="test_auth_key", otp_template_id="bad_template")
        result = adapter.send_otp("9876543210", "5678")

        self.assertFalse(result)


class MobileOTPAuthAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.signup_url = reverse("auth_register")
        self.login_url = reverse("token_obtain_pair")
        self.verify_otp_url = reverse("verify_otp")
        self.resend_otp_url = reverse("resend_otp")

    def test_signup_via_mobile_number(self):
        response = self.client.post(
            self.signup_url,
            {"contact_no": "9876543210", "full_name": "Test Mobile User"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Please verify your OTP.")

        # Verify cached OTP exists
        stored_otp = _get_phone_otp("919876543210")
        self.assertIsNotNone(stored_otp)
        self.assertEqual(len(str(stored_otp)), 4)

    def test_login_otp_challenge_via_mobile_number(self):
        phone = "9876544445"
        normalized_phone = "919876544445"

        # Calling existing /api/user/login/ with contact_no initiates OTP challenge
        response = self.client.post(
            self.login_url,
            {"contact_no": phone},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Please verify your OTP.")
        self.assertEqual(response.data["contact_no"], normalized_phone)

        # Confirm OTP was set in cache
        stored_otp = _get_phone_otp(normalized_phone)
        self.assertIsNotNone(stored_otp)

    def test_verify_otp_auto_provisions_new_user_and_issues_jwt(self):
        phone = "9876500001"
        normalized_phone = "919876500001"
        _set_phone_otp(normalized_phone, "8899")

        response = self.client.post(
            self.verify_otp_url,
            {"contact_no": phone, "otp": "8899"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access-token", response.data)
        self.assertIn("refresh-token", response.data)
        self.assertEqual(response.data["detail"]["contact_no"], normalized_phone)

        # Verify user created in DB without placeholder email
        created_user = User.objects.filter(contact_no=normalized_phone).first()
        self.assertIsNotNone(created_user)
        self.assertIsNone(created_user.email)
        self.assertEqual(created_user.state_id, User.STATE_ACTIVE)
        self.assertEqual(created_user.otp_verified, 1)


    def test_verify_otp_existing_user_login(self):
        phone = "9876511112"
        normalized_phone = "919876511112"
        existing_user = User.objects.create_user(
            email="existing_mobile_user@spilbloo.com",
            full_name="Existing Mobile User",
            contact_no=normalized_phone,
            role_id=User.ROLE_PATIENT,
            state_id=User.STATE_ACTIVE
        )
        _set_phone_otp(normalized_phone, "4455")

        response = self.client.post(
            self.verify_otp_url,
            {"contact_no": phone, "otp": "4455"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access-token", response.data)
        self.assertEqual(response.data["detail"]["id"], existing_user.id)
        self.assertEqual(response.data["detail"]["full_name"], "Existing Mobile User")

    def test_verify_otp_rejects_incorrect_otp(self):
        phone = "9876522223"
        normalized_phone = "919876522223"
        _set_phone_otp(normalized_phone, "9999")

        response = self.client.post(
            self.verify_otp_url,
            {"contact_no": phone, "otp": "0000"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Incorrect OTP")

    def test_verify_otp_brute_force_lockout(self):
        phone = "9876599999"
        normalized_phone = "919876599999"
        _set_phone_otp(normalized_phone, "8888")

        for _ in range(5):
            self.client.post(
                self.verify_otp_url,
                {"contact_no": phone, "otp": "0000"},
                format="json"
            )

        # 6th attempt is locked
        response = self.client.post(
            self.verify_otp_url,
            {"contact_no": phone, "otp": "8888"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Too many failed attempts. Please request a new OTP.")


    def test_resend_otp_via_mobile_number(self):
        phone = "9876533334"
        response = self.client.post(
            self.resend_otp_url,
            {"contact_no": phone},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Verification code sent successfully")
        self.assertEqual(response.data["contact_no"], "919876533334")

        stored_otp = _get_phone_otp("919876533334")
        self.assertIsNotNone(stored_otp)
