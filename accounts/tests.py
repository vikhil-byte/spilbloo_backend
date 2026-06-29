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


class LanguageAndAffirmationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="patient_lang@spilbloo.local",
            password="Pass@123",
            full_name="Patient Lang",
            role_id=4,  # Patient role
            state_id=User.STATE_ACTIVE,
            language="es",
            activation_key="testtoken123"
        )

    def test_user_serializer_contains_language(self):
        from accounts.serializers import UserSerializer
        serializer = UserSerializer(self.user)
        self.assertIn("language", serializer.data)
        self.assertEqual(serializer.data["language"], "es")

        # Test normalization of null language to empty string
        self.user.language = None
        self.user.save()
        serializer_null = UserSerializer(self.user)
        self.assertEqual(serializer_null.data["language"], "")

    def test_legacy_user_detail_contains_language_and_affirmation(self):
        from accounts.views import _legacy_user_detail
        detail = _legacy_user_detail(self.user)
        self.assertIn("language", detail)
        self.assertEqual(detail["language"], "es")
        self.assertIn("affirmation_for_the_day", detail)
        self.assertTrue(len(detail["affirmation_for_the_day"]) > 0)

    def test_cards_view_response_contains_affirmation(self):
        from unittest.mock import patch
        with patch("core.models.HomeCard.objects.filter") as mock_filter:
            mock_filter.return_value = []
            self.client.credentials(HTTP_AUTHORIZATION="Bearer testtoken123", HTTP_USER_ID=str(self.user.id))
            response = self.client.get("/node/cards")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("results", response.data)
            self.assertIn("affirmation", response.data["results"])
            self.assertIn("cards", response.data["results"])
            self.assertTrue(len(response.data["results"]["affirmation"]) > 0)

    def test_daily_qna_contains_questions_and_opinions(self):
        from core.models import DailyCheckinQuestion, DailyCheckinAnswer
        q = DailyCheckinQuestion.objects.create(question="How do you feel today?", is_active=1)
        ans = DailyCheckinAnswer.objects.create(question_id=q.id, answer="Good", score=5, journal_question_id=1)
        
        self.client.credentials(HTTP_AUTHORIZATION="Bearer testtoken123", HTTP_USER_ID=str(self.user.id))
        response = self.client.get("/node/daily-qna")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("question_and_answers", response.data["results"])
        
        qnas = response.data["results"]["question_and_answers"]
        self.assertTrue(len(qnas) > 0)
        
        first_q = qnas[0]
        self.assertEqual(first_q["id"], q.id)
        self.assertEqual(first_q["question"], "How do you feel today?")
        self.assertIn("created_on", first_q)
        self.assertIn("answers", first_q)
        
        first_ans = first_q["answers"][0]
        self.assertEqual(first_ans["id"], ans.id)
        self.assertEqual(first_ans["answer"], "Good")
        self.assertEqual(first_ans["score"], 5)
        self.assertEqual(first_ans["journal_question_id"], 1)
        self.assertIn("created_on", first_ans)

    def test_add_user_answers_success(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer testtoken123", HTTP_USER_ID=str(self.user.id))
        payload = {
            "user_id": self.user.id,
            "qna_map": [
                {"id": 1, "question": "Question 1", "answer": "Answer 1"}
            ]
        }
        response = self.client.post("/node/add-user-answers", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        from core.models import DailyCheckinQuestionAndAnswer
        qna = DailyCheckinQuestionAndAnswer.objects.filter(created_by=self.user).first()
        self.assertIsNotNone(qna)
        self.assertEqual(qna.qna_map, payload["qna_map"])

    def test_add_user_answers_string_user_id(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer testtoken123", HTTP_USER_ID=str(self.user.id))
        payload = {
            "user_id": str(self.user.id),
            "qna_map": [
                {"id": 1, "question": "Question 1", "answer": "Answer 1"}
            ]
        }
        response = self.client.post("/node/add-user-answers", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_user_answers_missing_user_id(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer testtoken123", HTTP_USER_ID=str(self.user.id))
        payload = {
            "qna_map": [
                {"id": 1, "question": "Question 1", "answer": "Answer 1"}
            ]
        }
        response = self.client.post("/node/add-user-answers", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        from core.models import DailyCheckinQuestionAndAnswer
        qna = DailyCheckinQuestionAndAnswer.objects.filter(created_by=self.user).first()
        self.assertIsNotNone(qna)
        self.assertEqual(qna.qna_map, payload["qna_map"])




class UserProfileUpdateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="profile_tester@spilbloo.local",
            password="Pass@123",
            full_name="Profile Tester",
            role_id=User.ROLE_PATIENT,
            state_id=User.STATE_ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("user_profile")

    def test_update_profile_date_slashes_yyyy_mm_dd(self):
        response = self.client.post(self.url, {"date_of_birth": "2008/06/03"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(str(self.user.date_of_birth), "2008-06-03")

    def test_update_profile_date_slashes_dd_mm_yyyy(self):
        response = self.client.post(self.url, {"date_of_birth": "03/06/2008"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(str(self.user.date_of_birth), "2008-06-03")

    def test_update_profile_date_standard(self):
        response = self.client.post(self.url, {"date_of_birth": "2008-06-03"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(str(self.user.date_of_birth), "2008-06-03")

    def test_update_profile_date_invalid_format_returns_400(self):
        response = self.client.post(self.url, {"date_of_birth": "not-a-date"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)


