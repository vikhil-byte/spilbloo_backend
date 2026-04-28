from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from plans.models import Plan, SubscribedPlan
from core.models import VideoPlan, SubscribedVideo, VideoCoupon, CouponUser


User = get_user_model()


class CreateSubscriptionViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="tester@spilbloo.local",
            password="Test@1234",
            full_name="Tester",
            role_id=User.ROLE_PATIENT,
            state_id=User.STATE_ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("create_subscription")

    def _create_plan(self, plan_id: str) -> Plan:
        return Plan.objects.create(
            title="Test Plan",
            description="Subscription test plan",
            plan_id=plan_id,
            no_of_video_session=4,
            no_of_free_trial_days=3,
            currency_code="INR",
            total_price=Decimal("999.00"),
            tax_price=Decimal("179.82"),
            final_price=Decimal("1178.82"),
            doctor_price=Decimal("700.00"),
            duration=30,
            plan_type=1,
            type_id=1,
            state_id=1,
            is_recommended=1,
            incentive_days=0,
        )

    def test_create_subscription_supports_query_param_plan_id(self):
        plan = self._create_plan("seed_plan_query_param_001")
        response = self.client.post(f"{self.url}?plan_id={plan.plan_id}", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Subscription created successfully.")
        self.assertTrue(str(response.data["subscription_id"]).startswith("sub_mock_"))
        self.assertTrue(
            SubscribedPlan.objects.filter(
                created_by=self.user,
                plan=plan,
                subscription_id=response.data["subscription_id"],
            ).exists()
        )

    @override_settings(RAZORPAY_KEY_ID="test_key", RAZORPAY_KEY_SECRET="test_secret")
    @patch("plans.views.razorpay_client.subscription.create")
    def test_create_subscription_uses_razorpay_for_real_plan_ids(self, mock_create):
        plan = self._create_plan("plan_real_123")
        mock_create.return_value = {"id": "sub_real_123"}

        response = self.client.post(f"{self.url}?plan_id={plan.plan_id}", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["subscription_id"], "sub_real_123")
        self.assertTrue(
            SubscribedPlan.objects.filter(
                created_by=self.user,
                plan=plan,
                subscription_id="sub_real_123",
            ).exists()
        )
        mock_create.assert_called_once()

    def test_create_subscription_rejects_when_user_already_has_active_paid_plan(self):
        plan = self._create_plan("seed_plan_existing_001")
        SubscribedPlan.objects.create(
            plan=plan,
            created_by=self.user,
            plan_type=1,
            state_id=1,
            subscription_id="sub_existing_001",
            start_date=timezone.now(),
            final_price=Decimal("1178.82"),
        )

        response = self.client.post(f"{self.url}?plan_id={plan.plan_id}", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "You are already on a plan.")


class AuthenticateSubscriptionSecurityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="auth@spilbloo.local",
            password="Test@1234",
            full_name="Auth Tester",
            role_id=User.ROLE_PATIENT,
            state_id=User.STATE_ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("authenticate_subscription")
        self.plan = Plan.objects.create(
            title="Auth Plan",
            description="Auth test plan",
            plan_id="plan_auth_001",
            total_price=Decimal("999.00"),
            tax_price=Decimal("179.00"),
            final_price=Decimal("1178.00"),
            duration=30,
            plan_type=1,
            type_id=1,
            state_id=1,
        )

    @override_settings(RAZORPAY_KEY_ID="test_key", RAZORPAY_KEY_SECRET="test_secret")
    @patch("plans.views.razorpay_client.utility.verify_payment_signature")
    def test_authenticate_subscription_rejects_invalid_signature(self, mock_verify):
        mock_verify.side_effect = Exception("bad sig")
        SubscribedPlan.objects.create(
            plan=self.plan,
            created_by=self.user,
            plan_type=1,
            state_id=0,
            subscription_id="sub_live_001",
            start_date=timezone.now(),
        )
        response = self.client.post(
            self.url,
            {
                "plan_id": self.plan.plan_id,
                "sub_id": "sub_live_001",
                "transaction_id": "txn_001",
                "razorpay_payment_id": "pay_001",
                "razorpay_signature": "sig_bad",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Payment verification failed.")

    @override_settings(RAZORPAY_KEY_ID="test_key", RAZORPAY_KEY_SECRET="test_secret")
    @patch("plans.views.razorpay_client.utility.verify_payment_signature")
    def test_authenticate_subscription_idempotent_success(self, mock_verify):
        mock_verify.return_value = None
        sub = SubscribedPlan.objects.create(
            plan=self.plan,
            created_by=self.user,
            plan_type=1,
            state_id=0,
            subscription_id="sub_live_002",
            start_date=timezone.now(),
        )
        payload = {
            "plan_id": self.plan.plan_id,
            "sub_id": "sub_live_002",
            "transaction_id": "txn_same",
            "razorpay_payment_id": "pay_002",
            "razorpay_signature": "sig_ok",
        }
        first = self.client.post(self.url, payload, format="json")
        second = self.client.post(self.url, payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        sub.refresh_from_db()
        self.assertEqual(sub.state_id, 1)
        self.assertEqual(sub.transaction_id, "txn_same")


class VideoPlanPurchaseFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="video@spilbloo.local",
            password="Test@1234",
            full_name="Video Tester",
            role_id=User.ROLE_PATIENT,
            state_id=User.STATE_ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        self.buy_url = reverse("buy_video_plan")
        self.check_url = reverse("check_buy_video_plan")
        self.plan = VideoPlan.objects.create(
            title="Video Pack",
            description="Pack",
            discounted_price="1000",
            total_price="1000",
            tax_price="180",
            final_price="1180",
            gross_price_per_video="100",
            net_price_per_video="82",
            credit=5,
            state_id=VideoPlan.STATE_ACTIVE,
            type_id=1,
        )

    def test_check_and_buy_video_plan_have_parity_without_coupon(self):
        check = self.client.post(self.check_url, {"plan_id": self.plan.id}, format="json")
        self.assertEqual(check.status_code, status.HTTP_200_OK)
        self.assertTrue(check.data["status"])

        buy = self.client.post(
            self.buy_url,
            {"plan_id": self.plan.id, "transaction_id": "video_txn_1"},
            format="json",
        )
        self.assertEqual(buy.status_code, status.HTTP_200_OK)
        self.assertEqual(float(check.data["plan_amount"]), float(buy.data["plan_amount"]))
        self.assertEqual(float(check.data["gst_amount"]), float(buy.data["gst_amount"]))
        self.assertEqual(float(check.data["final_amount"]), float(buy.data["final_amount"]))
        self.assertTrue(SubscribedVideo.objects.filter(created_by=self.user, plan=self.plan).exists())
        self.user.refresh_from_db()
        self.assertEqual(self.user.video_credit, 5)

    def test_buy_video_plan_with_coupon_persists_coupon_user(self):
        coupon = VideoCoupon.objects.create(
            code="VID10",
            amount="10",
            plan_id=str(self.plan.id),
            type_id=VideoCoupon.TYPE_PERCENTAGE,
            limit=10,
            user_limit=1,
            state_id=VideoCoupon.STATE_ACTIVE,
            created_by=self.user,
        )
        response = self.client.post(
            self.buy_url,
            {"plan_id": self.plan.id, "coupon": coupon.code, "transaction_id": "video_txn_2"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            CouponUser.objects.filter(coupon=coupon, created_by=self.user).exists()
        )
