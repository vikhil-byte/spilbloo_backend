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
from accounts.phone_utils import normalize_phone_e164, resolve_country_hint, extract_country_code

User = get_user_model()


class PhoneUtilsTests(TestCase):
    """Tests for the phonenumbers-based phone_utils module."""

    def test_10_digit_indian_number(self):
        self.assertEqual(normalize_phone_e164("9876543210"), "+919876543210")

    def test_10_digit_starting_with_91(self):
        """Regression: 9187299381 is a 10-digit Indian number, not 91 + 87299381."""
        self.assertEqual(normalize_phone_e164("9187299381", "IN"), "+919187299381")

    def test_12_digit_with_country_code(self):
        self.assertEqual(normalize_phone_e164("919876543210"), "+919876543210")

    def test_e164_passthrough(self):
        self.assertEqual(normalize_phone_e164("+919876543210"), "+919876543210")

    def test_us_number(self):
        self.assertEqual(normalize_phone_e164("4155552671", "US"), "+14155552671")

    def test_us_number_with_country_code(self):
        self.assertEqual(normalize_phone_e164("14155552671"), "+14155552671")

    def test_empty_returns_none(self):
        self.assertIsNone(normalize_phone_e164(""))
        self.assertIsNone(normalize_phone_e164(None))

    def test_invalid_number_returns_none(self):
        self.assertIsNone(normalize_phone_e164("123"))

    def test_resolve_country_hint_dial_code(self):
        self.assertEqual(resolve_country_hint("+91"), "IN")
        self.assertEqual(resolve_country_hint("91"), "IN")
        self.assertEqual(resolve_country_hint("+1"), "US")
        self.assertEqual(resolve_country_hint("44"), "GB")

    def test_resolve_country_hint_iso_code(self):
        self.assertEqual(resolve_country_hint("IN"), "IN")
        self.assertEqual(resolve_country_hint("US"), "US")

    def test_resolve_country_hint_default(self):
        self.assertEqual(resolve_country_hint(None), "IN")
        self.assertEqual(resolve_country_hint(""), "IN")

    def test_extract_country_code(self):
        self.assertEqual(extract_country_code("+919876543210"), "+91")
        self.assertEqual(extract_country_code("4155552671", "US"), "+1")
        self.assertEqual(extract_country_code(""), "+91")


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

    @patch("requests.post")
    def test_msg91_adapter_send_otp_flow_template(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"type": "success", "message": "366969766a6a6c6934394d69"}'
        mock_response.json.return_value = {"type": "success", "message": "366969766a6a6c6934394d69"}
        mock_post.return_value = mock_response

        # 24-character hex template ID
        adapter = MSG91SMSAdapter(auth_key="test_auth_key", otp_template_id="6a9d6a75b3e1cb31640825e3")
        result = adapter.send_otp("7506229401", "4819")

        self.assertTrue(result)
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args[0][0], adapter.FLOW_API_URL)
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["json"]["template_id"], "6a9d6a75b3e1cb31640825e3")
        self.assertEqual(call_kwargs["json"]["recipients"][0]["mobiles"], "917506229401")
        self.assertEqual(call_kwargs["json"]["recipients"][0]["otp"], "4819")
        self.assertEqual(adapter.last_response.get("request_id"), "366969766a6a6c6934394d69")


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

        # Verify cached OTP exists (E.164 format)
        stored_otp = _get_phone_otp("+919876543210")
        self.assertIsNotNone(stored_otp)
        self.assertEqual(len(str(stored_otp)), 4)

    def test_login_otp_challenge_via_mobile_number(self):
        phone = "9876544445"
        e164_phone = "+919876544445"

        # Calling existing /api/user/login/ with contact_no initiates OTP challenge
        response = self.client.post(
            self.login_url,
            {"contact_no": phone},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Please verify your OTP.")
        self.assertEqual(response.data["contact_no"], e164_phone)

        # Confirm OTP was set in cache
        stored_otp = _get_phone_otp(e164_phone)
        self.assertIsNotNone(stored_otp)

    def test_verify_otp_auto_provisions_new_user_and_issues_jwt(self):
        phone = "9876500001"
        e164_phone = "+919876500001"
        _set_phone_otp(e164_phone, "8899")

        response = self.client.post(
            self.verify_otp_url,
            {"contact_no": phone, "otp": "8899"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access-token", response.data)
        self.assertIn("refresh-token", response.data)
        self.assertEqual(response.data["detail"]["contact_no"], e164_phone)

        # Verify user created in DB with E.164 contact_no
        created_user = User.objects.filter(contact_no=e164_phone).first()
        self.assertIsNotNone(created_user)
        self.assertIsNone(created_user.email)
        self.assertEqual(created_user.state_id, User.STATE_ACTIVE)
        self.assertEqual(created_user.otp_verified, 1)


    def test_verify_otp_existing_user_login(self):
        phone = "9876511112"
        e164_phone = "+919876511112"
        existing_user = User.objects.create_user(
            email="existing_mobile_user@spilbloo.com",
            full_name="Existing Mobile User",
            contact_no=e164_phone,
            role_id=User.ROLE_PATIENT,
            state_id=User.STATE_ACTIVE
        )
        _set_phone_otp(e164_phone, "4455")

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
        e164_phone = "+919876522223"
        _set_phone_otp(e164_phone, "9999")

        response = self.client.post(
            self.verify_otp_url,
            {"contact_no": phone, "otp": "0000"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Incorrect OTP")

    def test_verify_otp_brute_force_lockout(self):
        phone = "9876599999"
        e164_phone = "+919876599999"
        _set_phone_otp(e164_phone, "8888")

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
        self.assertEqual(response.data["contact_no"], "+919876533334")

        stored_otp = _get_phone_otp("+919876533334")
        self.assertIsNotNone(stored_otp)

    def test_resend_and_verify_with_international_country_code(self):
        # US phone number with +1
        response = self.client.post(
            self.resend_otp_url,
            {"contact_no": "4155552671", "country_code": "+1"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["contact_no"], "+14155552671")

        stored_otp = _get_phone_otp("+14155552671")
        self.assertIsNotNone(stored_otp)

        # Verify OTP
        verify_res = self.client.post(
            self.verify_otp_url,
            {"contact_no": "4155552671", "country_code": "+1", "otp": stored_otp},
            format="json"
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)
        self.assertIn("access-token", verify_res.data)
        self.assertEqual(verify_res.data["detail"]["country_code"], "+1")
        self.assertEqual(verify_res.data["detail"]["contact_no"], "+14155552671")

        user = User.objects.get(contact_no="+14155552671")
        self.assertEqual(user.country_code, "+1")

    def test_default_country_code_for_10_digit_number(self):
        phone = "9876544445"
        stored_otp = "8899"
        _set_phone_otp("+919876544445", stored_otp)

        verify_res = self.client.post(
            self.verify_otp_url,
            {"contact_no": phone, "otp": stored_otp},
            format="json"
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_res.data["detail"]["country_code"], "+91")

        user = User.objects.get(contact_no="+919876544445")
        self.assertEqual(user.country_code, "+91")

    def test_autoprovision_with_custom_name(self):
        phone = "9876599991"
        stored_otp = "1122"
        _set_phone_otp("+919876599991", stored_otp)

        verify_res = self.client.post(
            self.verify_otp_url,
            {"contact_no": phone, "otp": stored_otp, "full_name": "Rohan Sharma"},
            format="json"
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_res.data["detail"]["full_name"], "Rohan Sharma")

        user = User.objects.get(contact_no="+919876599991")
        self.assertEqual(user.full_name, "Rohan Sharma")
        self.assertIsNone(user.email)

    def test_autoprovision_fallback_name_when_not_provided(self):
        phone = "9876599992"
        stored_otp = "3344"
        _set_phone_otp("+919876599992", stored_otp)

        verify_res = self.client.post(
            self.verify_otp_url,
            {"contact_no": phone, "otp": stored_otp},
            format="json"
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_res.data["detail"]["full_name"], "")

        user = User.objects.get(contact_no="+919876599992")
        self.assertEqual(user.full_name, "")
        self.assertIsNone(user.email)

    def test_10_digit_phone_starting_with_91_does_not_create_duplicate(self):
        # Specific regression test for Indian mobile numbers starting with '91' (e.g. 9187299381)
        phone = "9187299381"
        stored_otp = "7711"
        _set_phone_otp("+919187299381", stored_otp)

        verify_res = self.client.post(
            self.verify_otp_url,
            {"contact_no": phone, "country_code": "+91", "otp": stored_otp},
            format="json"
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_res.data["detail"]["contact_no"], "+919187299381")
        self.assertEqual(verify_res.data["detail"]["full_name"], "")

        # Verify second login with same number returns same user without creating duplicate
        _set_phone_otp("+919187299381", stored_otp)
        verify_res2 = self.client.post(
            self.verify_otp_url,
            {"contact_no": "919187299381", "country_code": "+91", "otp": stored_otp},
            format="json"
        )
        # Account should be found (not duplicated)
        matching_users = User.objects.filter(contact_no="+919187299381")
        self.assertEqual(matching_users.count(), 1)

    def test_autoprovision_multiple_users_empty_email_no_integrity_error(self):
        # Verify that auto-provisioning multiple users without email never causes
        # IntegrityError: Key (email)=() already exists
        for idx, phone in enumerate(["9876599993", "9876599994"], start=5):
            otp = f"{idx}{idx}{idx}{idx}"
            _set_phone_otp(f"+91{phone}", otp)
            res = self.client.post(
                self.verify_otp_url,
                {"contact_no": phone, "otp": otp, "email": ""},
                format="json"
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["detail"]["email"], "")
            u = User.objects.get(contact_no=f"+91{phone}")
            self.assertIsNone(u.email)
