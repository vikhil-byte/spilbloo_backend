from django.test import TestCase, override_settings
from django.core import mail
from core.email_service.factory import get_email_client
from core.email_service.smtp_adapter import SMTPEmailAdapter
from core.email_service.console_adapter import ConsoleEmailAdapter
from core.email_service.ses_adapter import SESEmailAdapter

class EmailServiceTests(TestCase):
    
    @override_settings(EMAIL_SERVICE_PROVIDER='smtp')
    def test_factory_returns_smtp_adapter(self):
        client = get_email_client()
        self.assertIsInstance(client, SMTPEmailAdapter)

    @override_settings(EMAIL_SERVICE_PROVIDER='console')
    def test_factory_returns_console_adapter(self):
        client = get_email_client()
        self.assertIsInstance(client, ConsoleEmailAdapter)

    @override_settings(EMAIL_SERVICE_PROVIDER='ses')
    def test_factory_returns_ses_adapter(self):
        client = get_email_client()
        self.assertIsInstance(client, SESEmailAdapter)

    @override_settings(EMAIL_SERVICE_PROVIDER='smtp', DEFAULT_FROM_EMAIL='test-sender@spilbloo.com')
    def test_smtp_adapter_sends_email_via_django_mail(self):
        client = get_email_client()
        result = client.send_email(
            subject="Test Subject",
            body="Test Body",
            to_email="test-recipient@spilbloo.com"
        )
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Test Subject")
        self.assertEqual(mail.outbox[0].body, "Test Body")
        self.assertEqual(mail.outbox[0].to, ["test-recipient@spilbloo.com"])
        self.assertEqual(mail.outbox[0].from_email, "test-sender@spilbloo.com")

    @override_settings(EMAIL_SERVICE_PROVIDER='console')
    def test_console_adapter_always_returns_true(self):
        client = get_email_client()
        result = client.send_email(
            subject="Console Subject",
            body="Console Body",
            to_email="test-console@spilbloo.com"
        )
        self.assertTrue(result)
