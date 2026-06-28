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


from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from core.models import DailyJournal

User = get_user_model()

class FetchJournalsViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="journal_tester@spilbloo.local",
            password="Pass@123",
            full_name="Journal Tester",
            role_id=4,  # Patient role
            state_id=1,  # Active
        )
        self.client.force_authenticate(user=self.user)

    def test_fetch_journals_formatting(self):
        journal = DailyJournal.objects.create(
            journal="Hello World Entry",
            question_id=2,
            created_by=self.user
        )
        self.assertIsNotNone(journal.created_on)

        response = self.client.get(f"/node/fetch-journals?userId={self.user.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        res_data = response.json()
        self.assertEqual(res_data["code"], 200)
        self.assertEqual(res_data["message"], "OK")
        self.assertFalse(res_data["error"])
        
        journals = res_data["results"]["journals"]
        self.assertEqual(len(journals), 1)
        
        first_journal = journals[0]
        self.assertEqual(first_journal["id"], journal.id)
        self.assertEqual(first_journal["journal"], "Hello World Entry")
        self.assertEqual(first_journal["question_id"], 2)
        
        self.assertTrue(first_journal["entry_date"].endswith("T00:00:00.000Z"))
        self.assertTrue(first_journal["created_on"].endswith(".000Z"))
        self.assertEqual(first_journal["created_by_id"], self.user.id)
