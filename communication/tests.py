from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from communication.models import CommunicationGateway, CommunicationTemplate, CommunicationLog
from communication.services.dispatcher import CommunicationService, send_communication

User = get_user_model()


class CommunicationServiceTests(TestCase):
    def setUp(self):
        CommunicationLog.objects.all().delete()
        CommunicationTemplate.objects.all().delete()
        CommunicationGateway.objects.all().delete()

        # Create test mock gateway
        self.gateway = CommunicationGateway.objects.create(
            name="Mock Console Gateway",
            channel="sms",
            provider_type="console",
            priority=1,
            is_active=True,
            credentials={"sender_id": "SPBLOO"}
        )

        # Create test template
        self.template = CommunicationTemplate.objects.create(
            event_code="AUTH_OTP",
            channel="sms",
            title="User Auth OTP",
            external_template_id="mock_otp_template_123",
            sender_override="SPBLOO",
            body_template="Dear User, your Spilbloo verification OTP is {{otp}}. Valid for 10 minutes. - SPBLOO",
            is_active=True
        )

    def test_render_content_placeholders(self):
        ctx = {"otp": "4521", "name": "Vikhil"}
        rendered1 = CommunicationService.render_content("Code: {{otp}} for {{name}}", ctx)
        self.assertEqual(rendered1, "Code: 4521 for Vikhil")

        rendered2 = CommunicationService.render_content("Code: ##otp##", ctx)
        self.assertEqual(rendered2, "Code: 4521")

    def test_send_communication_creates_log(self):
        success, log = CommunicationService.send(
            event_code="AUTH_OTP",
            recipient="917506229401",
            context={"otp": "8888"},
            channel="sms"
        )
        self.assertTrue(success)
        self.assertIsNotNone(log)
        self.assertEqual(log.status, CommunicationLog.STATUS_SENT)
        self.assertEqual(log.recipient, "917506229401")
        self.assertEqual(log.event_code, "AUTH_OTP")
        self.assertIn("8888", log.rendered_body)
        self.assertEqual(log.gateway, self.gateway)
        self.assertEqual(log.template, self.template)

    def test_gateway_failover(self):
        # Secondary fallback gateway
        fallback_gw = CommunicationGateway.objects.create(
            name="Fallback Mock Gateway",
            channel="sms",
            provider_type="console",
            priority=2,
            is_active=True
        )

        # Primary gateway with invalid provider that will fail
        primary_gw = CommunicationGateway.objects.create(
            name="Failing Primary Gateway",
            channel="sms",
            provider_type="msg91",
            priority=1,
            is_active=True,
            credentials={"auth_key": "bad_key"},
            fallback_gateway=fallback_gw
        )

        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.content = b'{"type": "error", "message": "Unauthorized"}'
            mock_resp.json.return_value = {"type": "error", "message": "Unauthorized"}
            mock_post.return_value = mock_resp

            success, log = CommunicationService.send(
                event_code="AUTH_OTP",
                recipient="919999999999",
                context={"otp": "1234"},
                channel="sms",
                override_gateway=primary_gw
            )

            # Failover to fallback_gw succeeded!
            self.assertTrue(success)
            self.assertEqual(log.gateway, fallback_gw)
            self.assertEqual(log.status, CommunicationLog.STATUS_SENT)

    def test_convenience_send_communication(self):
        result = send_communication(
            event_code="AUTH_OTP",
            recipient="917506229401",
            context={"otp": "7777"}
        )
        self.assertTrue(result)
        latest_log = CommunicationLog.objects.filter(recipient="917506229401").first()
        self.assertIsNotNone(latest_log)
        self.assertEqual(latest_log.status, CommunicationLog.STATUS_SENT)
