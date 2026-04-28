from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import Plan, SubscribedPlan, Coupon
from core.models import VideoPlan, SubscribedVideo, VideoCoupon, CouponUser, Currency
from .serializers import (
    PlanSerializer, SubscribedPlanSerializer, VideoPlanSerializer, 
    SubscribedVideoSerializer, CouponSerializer, VideoCouponSerializer
)
from accounts.serializers import UserSerializer
from accounts.views import _legacy_user_detail
import json
import logging
import random
from decimal import Decimal, InvalidOperation
import base64
import urllib.request
import urllib.error
import razorpay
from razorpay.errors import BadRequestError
from django.conf import settings
from company.models import Company, CompanyCoupon

logger = logging.getLogger(__name__)

UPCOMING_STATE_UPCOMING = 2
UPCOMING_STATE_CANCELED = 4
UPCOMING_STATE_IMMEDIATE_CANCELED = 5


def _to_decimal(value, default="0"):
    try:
        if value in (None, ""):
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _is_coupon_valid_now(coupon):
    if not getattr(coupon, "valid_till", None):
        return True
    return coupon.valid_till >= timezone.now()


def _is_plan_allowed(plan_token: str, plan_id: str) -> bool:
    if not plan_token:
        return True
    allowed = [p.strip() for p in str(plan_token).split(",") if p.strip()]
    return str(plan_id) in allowed


def _coupon_discount_amount(base_amount: Decimal, discount_value: Decimal, type_id: int) -> Decimal:
    # Legacy coupons are typically flat(1) or percentage(2).
    if type_id == 2:
        return (base_amount * discount_value) / Decimal("100")
    return discount_value

# Initialize Razorpay Client (ensure keys are in settings)
razorpay_client = razorpay.Client(auth=(
    getattr(settings, 'RAZORPAY_KEY_ID', ''), 
    getattr(settings, 'RAZORPAY_KEY_SECRET', '')
))


def _is_live_razorpay_subscription(subscription_id: str) -> bool:
    return bool(subscription_id and str(subscription_id).startswith("sub_") and not str(subscription_id).startswith("sub_mock_"))


def _is_free_trial_subscription(subscription) -> bool:
    if not subscription:
        return False
    free_trial_days = int(getattr(subscription, "coupon_free_trial_days", 0) or 0)
    if free_trial_days <= 0:
        return False
    if subscription.start_date:
        return timezone.now() < (subscription.start_date + timedelta(days=free_trial_days))
    return subscription.state_id == 0


def _cancel_razorpay_subscription(subscription_id: str, cancel_at_cycle_end: int):
    razorpay_client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": int(cancel_at_cycle_end)})


def _patch_razorpay_subscription_plan(subscription_id: str, plan_id: str, schedule_change_at: str):
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        raise ValueError("Razorpay credentials are not configured.")

    token = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("ascii")
    payload = json.dumps(
        {
            "plan_id": plan_id,
            "schedule_change_at": schedule_change_at,  # "now" or "cycle_end"
            "remaining_count": 12,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url=f"https://api.razorpay.com/v1/subscriptions/{subscription_id}",
        data=payload,
        method="PATCH",
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8") if resp else "{}"
    return json.loads(body or "{}")


def _calculate_video_plan_purchase(user, plan_id, coupon_code=None, coupon_discount_input=Decimal("0")):
    if not plan_id:
        return {"ok": False, "status": 400, "error": "plan_id is required."}

    plan = VideoPlan.objects.filter(id=plan_id, state_id=VideoPlan.STATE_ACTIVE).first()
    if not plan:
        return {"ok": False, "status": 404, "error": "Video Plan not found"}

    plan_amount = _to_decimal(plan.total_price)
    default_gst_amount = _to_decimal(plan.tax_price)
    gst_percent = _to_decimal(getattr(plan, "tax_percentage", None), "0")
    if gst_percent <= 0 and plan_amount > 0 and default_gst_amount > 0:
        gst_percent = (default_gst_amount * Decimal("100")) / plan_amount

    coupon_model = None
    coupon_discount = Decimal("0")
    gst_amount = default_gst_amount
    final_amount = _to_decimal(plan.final_price)
    purchase_type = SubscribedVideo.TYPE_COUPON_NOT_APPLIED

    if coupon_code:
        coupon_model = VideoCoupon.objects.filter(code=coupon_code, state_id=VideoCoupon.STATE_ACTIVE).first()
        if not coupon_model:
            return {"ok": False, "status": 400, "error": "coupon not found"}
        if not _is_coupon_valid_now(coupon_model) or not _is_plan_allowed(coupon_model.plan_id, str(plan.id)):
            return {"ok": False, "status": 400, "error": "Invalid coupon code"}
        if coupon_model.limit and CouponUser.objects.filter(coupon=coupon_model).count() >= coupon_model.limit:
            return {"ok": False, "status": 400, "error": "Coupon usage limit exceeded."}
        if coupon_model.user_limit and CouponUser.objects.filter(coupon=coupon_model, created_by=user).count() >= coupon_model.user_limit:
            return {"ok": False, "status": 400, "error": "You have already used this coupon"}

        coupon_discount = _coupon_discount_amount(
            plan_amount,
            _to_decimal(coupon_model.amount),
            int(coupon_model.type_id or 0),
        )
        if coupon_discount_input > 0:
            coupon_discount = coupon_discount_input
        if coupon_discount <= 0 or coupon_discount >= plan_amount:
            return {"ok": False, "status": 400, "error": "Invalid coupon code"}

        discounted_subtotal = plan_amount - coupon_discount
        gst_amount = ((discounted_subtotal * gst_percent) / Decimal("100")) if gst_percent > 0 else default_gst_amount
        final_amount = discounted_subtotal + gst_amount
        purchase_type = SubscribedVideo.TYPE_COUPON_APPLIED

    return {
        "ok": True,
        "plan": plan,
        "coupon_model": coupon_model,
        "coupon_discount": coupon_discount,
        "plan_amount": plan_amount,
        "gst_amount": gst_amount,
        "final_amount": final_amount,
        "purchase_type": purchase_type,
    }

class PlanListView(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = PlanSerializer

    def get_queryset(self):
        type_id = self.request.query_params.get('type_id', 0)
        currency = self.request.query_params.get('currency', 'INR')
        qs = Plan.objects.filter(state_id=1, plan_type=1, type_id=1, currency_code=currency) # 1=Paid, 1=Visible
        
        if str(type_id) == '1': # PLAN_VIDEO_AND_TEXT
            qs = qs.filter(no_of_video_session__gt=0)
        elif str(type_id) == '2': # PLAN_TEXT
            qs = qs.filter(no_of_video_session=0)
            
        return qs.order_by('-is_recommended')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        # Legacy iOS expects an object containing `list`, not a bare JSON array.
        return Response({"list": serializer.data}, status=status.HTTP_200_OK)

class CompanyUserPlanListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PlanSerializer

    def get_queryset(self):
        user = self.request.user
        email = getattr(user, "email", "") or ""
        domain = email.split("@")[-1].lower() if "@" in email else ""
        if not domain:
            return Plan.objects.filter(state_id=1, plan_type=1, type_id=1).order_by("-is_recommended")

        company = Company.objects.filter(state_id=Company.STATE_ACTIVE, email_domain__iexact=domain).first()
        if not company:
            return Plan.objects.filter(state_id=1, plan_type=1, type_id=1).order_by("-is_recommended")

        coupon_plan_ids = CompanyCoupon.objects.filter(
            company=company,
            state_id=CompanyCoupon.STATE_ACTIVE,
        ).values_list("plan_id", flat=True)
        return Plan.objects.filter(state_id=1, id__in=coupon_plan_ids).order_by("-is_recommended")

class MyPlansView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SubscribedPlanSerializer

    def get_queryset(self):
        return SubscribedPlan.objects.filter(
            created_by=self.request.user,
            state_id__in=[1, 2] # ACTIVE, UPCOMING
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "video_credits": request.user.video_credit if hasattr(request.user, 'video_credit') else 0,
            "list": serializer.data
        })

class CreateSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def handle_exception(self, exc):
        if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            auth_header = self.request.headers.get("Authorization", "")
            auth_preview = ""
            if auth_header:
                parts = auth_header.split(" ", 1)
                if len(parts) == 2:
                    scheme, token = parts
                    auth_preview = f"{scheme} {token[:12]}..."
                else:
                    auth_preview = f"{auth_header[:20]}..."
            logger.warning(
                "create-subscription auth failed: reason=%s has_auth=%s auth_preview=%s method=%s path=%s",
                str(exc),
                bool(auth_header),
                auth_preview,
                self.request.method,
                self.request.path,
            )
        return super().handle_exception(exc)

    def post(self, request):
        # iOS legacy sends plan_id in query params.
        plan_id = request.data.get('plan_id') or request.query_params.get('plan_id')
        user = request.user
        logger.info(
            "create-subscription start: user_id=%s plan_id=%s has_coupon=%s",
            getattr(user, "id", None),
            plan_id,
            bool(request.data.get("coupon")),
        )
        
        try:
            with transaction.atomic():
                plan_obj = Plan.objects.get(plan_id=plan_id)
                
                # Check if already on a paid plan (actionCreateSubscription 427-432)
                if SubscribedPlan.objects.filter(created_by=user, state_id=1, plan_type=1).exists():
                     logger.warning("create-subscription blocked: active paid plan exists user_id=%s", getattr(user, "id", None))
                     return Response(
                         {
                             "error": "You are already on a plan.",
                             "message": "You are already on a plan.",
                         },
                         status=status.HTTP_400_BAD_REQUEST,
                     )

                # 1. Address Persistence (actionCreateSubscription 441-461)
                # If user doesn't have address, save it. Otherwise use user's address.
                user_address = request.data.get('address')
                if user_address:
                     user.address = user_address
                     user.city = request.data.get('city', user.city)
                     user.country = request.data.get('country', user.country)
                     user.contact_no = request.data.get('contact', user.contact_no)
                     user.save()

                # 2. Trial Day Calculation (actionCreateSubscription 480-500)
                trial_days = plan_obj.no_of_free_trial_days or 0
                coupon_code = request.data.get('coupon')
                coupon_trial_days = 0
                if coupon_code:
                     coupon = Coupon.objects.filter(code=coupon_code, state_id=1).first()
                     if coupon:
                          coupon_trial_days = coupon.no_of_free_trial_days or 0
                
                total_trial_days = trial_days + coupon_trial_days
                
                # Calculate start_at
                # If user has free plan, next plan starts from current end date
                # For simplicity, using timezone.now()
                start_time = timezone.now()
                rezorpay_start_at = start_time + timedelta(days=total_trial_days)
                start_at_timestamp = int(rezorpay_start_at.timestamp())

                # 3. Create Razorpay Subscription
                params = {
                    'plan_id': plan_id,
                    'customer_notify': 1,
                    'total_count': 12, # BILLING_CYCLE equivalent
                }
                if total_trial_days > 0:
                    params['start_at'] = start_at_timestamp
                
                if plan_id and str(plan_id).startswith("seed_"):
                    # Local/test seed plans are not present in Razorpay; keep flow testable.
                    subscription_id = "sub_mock_" + str(random.randint(1000, 9999))
                    logger.info("create-subscription mock mode: user_id=%s plan_id=%s sub_id=%s", getattr(user, "id", None), plan_id, subscription_id)
                else:
                    if not getattr(settings, "RAZORPAY_KEY_ID", "") or not getattr(settings, "RAZORPAY_KEY_SECRET", ""):
                        return Response({"error": "Razorpay credentials are not configured."}, status=status.HTTP_400_BAD_REQUEST)
                    try:
                        subscription = razorpay_client.subscription.create(params)
                    except BadRequestError as exc:
                        logger.warning("create-subscription razorpay rejected plan_id=%s error=%s", plan_id, str(exc))
                        return Response({"error": "Unable to create subscription for this plan."}, status=status.HTTP_400_BAD_REQUEST)
                    subscription_id = subscription.get("id")
                    if not subscription_id:
                        return Response({"error": "Unable to create Razorpay subscription."}, status=status.HTTP_400_BAD_REQUEST)
                    logger.info("create-subscription razorpay success: user_id=%s plan_id=%s sub_id=%s", getattr(user, "id", None), plan_id, subscription_id)
                
                # 4. Save SubscribedPlan record
                SubscribedPlan.objects.create(
                    plan=plan_obj,
                    subscription_id=subscription_id,
                    created_by=user,
                    state_id=0, # STATE_CREATED
                    plan_type=1, # PLAN_TYPE_PAID
                    start_date=timezone.now(),
                    renewal_date=rezorpay_start_at,
                    plan_price=plan_obj.total_price,
                    gst_price=plan_obj.tax_price,
                    final_price=plan_obj.final_price,
                )
                logger.info("create-subscription saved: user_id=%s plan_id=%s sub_id=%s", getattr(user, "id", None), plan_id, subscription_id)
                
                return Response({
                    "message": "Subscription created successfully.",
                    "subscription_id": subscription_id,
                }, status=status.HTTP_200_OK)
            
        except Plan.DoesNotExist:
            logger.warning("create-subscription failed: plan not found plan_id=%s user_id=%s", plan_id, getattr(user, "id", None))
            return Response({"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception(
                "create-subscription failed: plan_id=%s user_id=%s",
                plan_id,
                getattr(user, "id", None),
            )
            return Response({"error": "Unable to create subscription right now."}, status=status.HTTP_400_BAD_REQUEST)

class AuthenticateSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        # iOS legacy sends these in query params.
        plan_id_str = request.data.get('plan_id') or request.query_params.get('plan_id')
        sub_id = request.data.get('sub_id') or request.query_params.get('sub_id')
        transaction_id = request.data.get('transaction_id') or request.data.get('SubscribedPlan[transaction_id]')
        logger.info(
            "authenticate-subscription start: user_id=%s plan_id=%s sub_id=%s has_transaction_id=%s",
            getattr(user, "id", None),
            plan_id_str,
            sub_id,
            bool(transaction_id),
        )
        
        try:
            plan = Plan.objects.get(plan_id=plan_id_str)
            with transaction.atomic():
                subscribed_plan = (
                    SubscribedPlan.objects.select_for_update()
                    .get(created_by=user, plan=plan, subscription_id=sub_id)
                )

                # Idempotent success path: same subscription already active with same transaction.
                if subscribed_plan.state_id == 1 and transaction_id and subscribed_plan.transaction_id == transaction_id:
                    logger.info(
                        "authenticate-subscription idempotent success: user_id=%s plan_id=%s sub_id=%s",
                        getattr(user, "id", None),
                        plan_id_str,
                        sub_id,
                    )
                    return Response(
                        {"message": "Plan bought successfully.", "detail": _legacy_user_detail(user)},
                        status=status.HTTP_200_OK,
                    )

                # Do not allow mutation to a different transaction once plan is already active.
                if subscribed_plan.state_id == 1 and subscribed_plan.transaction_id and transaction_id and subscribed_plan.transaction_id != transaction_id:
                    logger.warning(
                        "authenticate-subscription rejected conflicting transaction: user_id=%s plan_id=%s sub_id=%s",
                        getattr(user, "id", None),
                        plan_id_str,
                        sub_id,
                    )
                    return Response({"error": "Subscription is already authenticated."}, status=status.HTTP_400_BAD_REQUEST)

                subscribed_plan.state_id = 1  # STATE_ACTIVE
                if transaction_id:
                    subscribed_plan.transaction_id = transaction_id
                subscribed_plan.save(update_fields=["state_id", "transaction_id"])
            logger.info(
                "authenticate-subscription success: user_id=%s plan_id=%s sub_id=%s",
                getattr(user, "id", None),
                plan_id_str,
                sub_id,
            )
            
            return Response({
                "message": "Plan bought successfully.",
                "detail": _legacy_user_detail(user)
            }, status=status.HTTP_200_OK)
            
        except (Plan.DoesNotExist, SubscribedPlan.DoesNotExist):
            logger.warning(
                "authenticate-subscription failed: subscription/plan not found user_id=%s plan_id=%s sub_id=%s",
                getattr(user, "id", None),
                plan_id_str,
                sub_id,
            )
            return Response({"error": "Subscription or Plan not found."}, status=status.HTTP_400_BAD_REQUEST)

class AuthenticateOneTimeSubView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        plan_id = request.data.get("plan_id") or request.query_params.get("plan_id")
        sub_id = request.data.get("sub_id") or request.query_params.get("sub_id")
        transaction_id = request.data.get("transaction_id") or request.data.get("SubscribedPlan[transaction_id]")
        logger.info(
            "authenticate-one-time-sub start: user_id=%s plan_id=%s sub_id=%s has_transaction_id=%s",
            getattr(request.user, "id", None),
            plan_id,
            sub_id,
            bool(transaction_id),
        )
        user = request.user
        try:
            plan = Plan.objects.get(plan_id=plan_id)
        except Plan.DoesNotExist:
            logger.warning(
                "authenticate-one-time-sub failed: plan not found user_id=%s plan_id=%s",
                getattr(user, "id", None),
                plan_id,
            )
            return Response({"error": "Plan not found."}, status=status.HTTP_400_BAD_REQUEST)

        # PHP one-time flow historically searched by local id.
        # iOS flow in this project passes Razorpay sub_id; support both.
        with transaction.atomic():
            subscribed_plan = (
                SubscribedPlan.objects.select_for_update().filter(created_by=user, plan=plan, id=sub_id).first()
                or SubscribedPlan.objects.select_for_update().filter(created_by=user, plan=plan, subscription_id=sub_id).first()
            )
            if not subscribed_plan:
                logger.warning(
                    "authenticate-one-time-sub failed: subscription not found user_id=%s plan_id=%s sub_id=%s",
                    getattr(user, "id", None),
                    plan_id,
                    sub_id,
                )
                return Response({"error": "Subscription not found."}, status=status.HTTP_400_BAD_REQUEST)

            if subscribed_plan.state_id == (subscribed_plan.upcoming_state or 1) and transaction_id and subscribed_plan.transaction_id == transaction_id:
                logger.info(
                    "authenticate-one-time-sub idempotent success: user_id=%s plan_id=%s sub_id=%s",
                    getattr(user, "id", None),
                    plan_id,
                    sub_id,
                )
                return Response(
                    {"message": "Plan bought successfully.", "detail": _legacy_user_detail(user)},
                    status=status.HTTP_200_OK,
                )

            if subscribed_plan.state_id == (subscribed_plan.upcoming_state or 1) and subscribed_plan.transaction_id and transaction_id and subscribed_plan.transaction_id != transaction_id:
                logger.warning(
                    "authenticate-one-time-sub rejected conflicting transaction: user_id=%s plan_id=%s sub_id=%s",
                    getattr(user, "id", None),
                    plan_id,
                    sub_id,
                )
                return Response({"error": "Subscription is already authenticated."}, status=status.HTTP_400_BAD_REQUEST)

            subscribed_plan.state_id = subscribed_plan.upcoming_state or 1
            if transaction_id:
                subscribed_plan.transaction_id = transaction_id
            subscribed_plan.save(update_fields=["state_id", "transaction_id"])
        logger.info(
            "authenticate-one-time-sub success: user_id=%s plan_id=%s sub_id=%s state_id=%s",
            getattr(user, "id", None),
            plan_id,
            sub_id,
            subscribed_plan.state_id,
        )
        return Response(
            {
                "message": "Plan bought successfully.",
                "detail": _legacy_user_detail(user),
            },
            status=status.HTTP_200_OK,
        )

class CancelCompanyView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, subscription_id=None):
        subscription_id = (
            subscription_id
            or request.data.get("subscription_id")
            or request.query_params.get("subscription_id")
        )
        if not subscription_id:
            return Response({"error": "subscription_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        cancel_reason = request.data.get("cancel_reason") or "Cancelled by user"
        subscription = SubscribedPlan.objects.filter(
            created_by=request.user,
            subscription_id=str(subscription_id),
        ).order_by("-id").first()
        if not subscription:
            subscription = SubscribedPlan.objects.filter(
                created_by=request.user,
                id=subscription_id,
            ).first()
        if not subscription:
            return Response({"error": "Subscription not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Keep cancellation state mapping consistent with existing code paths.
        subscription.state_id = 3
        subscription.cancel_reason = cancel_reason
        subscription.save(update_fields=["state_id", "cancel_reason"])
        return Response({"message": "Subscription cancelled successfully."}, status=status.HTTP_200_OK)

class CancelView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, plan_id=None):
        plan_id = plan_id or request.data.get("plan_id") or request.query_params.get("plan_id")
        if not plan_id:
            return Response({"error": "plan_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        cancel_reason = request.data.get("cancel_reason") or "Cancelled by user"
        plan = Plan.objects.filter(plan_id=plan_id).first()
        if not plan:
            return Response({"error": "Plan not found."}, status=status.HTTP_400_BAD_REQUEST)

        subscription = (
            SubscribedPlan.objects.filter(
                created_by=request.user,
                plan=plan,
                state_id__in=[0, 1, 2],
            )
            .order_by("-id")
            .first()
        )
        if not subscription:
            return Response({"error": "Subscription not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                subscription = SubscribedPlan.objects.select_for_update().get(id=subscription.id)

                # Mirror legacy behavior:
                # - free-trial -> immediate cancel
                # - otherwise cancel at cycle end
                immediate_cancel = _is_free_trial_subscription(subscription)
                next_upcoming_state = (
                    UPCOMING_STATE_IMMEDIATE_CANCELED if immediate_cancel else UPCOMING_STATE_CANCELED
                )

                if _is_live_razorpay_subscription(subscription.subscription_id):
                    _cancel_razorpay_subscription(
                        subscription.subscription_id,
                        cancel_at_cycle_end=0 if immediate_cancel else 1,
                    )

                SubscribedPlan.objects.filter(created_by=request.user).update(upcoming_state=next_upcoming_state)
                subscription.cancel_reason = cancel_reason
                subscription.save(update_fields=["cancel_reason"])

            return Response({"message": "Subscription cancelled successfully."}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception(
                "cancel-subscription failed user_id=%s plan_id=%s sub_id=%s",
                getattr(request.user, "id", None),
                plan_id,
                getattr(subscription, "subscription_id", None),
            )
            return Response({"error": "Unable to cancel subscription right now."}, status=status.HTTP_400_BAD_REQUEST)

class BuyVideoPlanView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # iOS legacy sends plan_id/final_price in query params.
        user = request.user
        plan_id = request.data.get("plan_id") or request.query_params.get("plan_id")
        coupon_code = request.data.get("coupon") or request.data.get("coupon_code")
        coupon_discount_input = _to_decimal(request.data.get("coupon_discount"), "0")
        transaction_id = request.data.get("transaction_id") or request.data.get("SubscribedVideo[transaction_id]")
        logger.info(
            "buy-video-plan start: user_id=%s plan_id=%s has_coupon=%s has_transaction_id=%s",
            getattr(user, "id", None),
            plan_id,
            bool(coupon_code),
            bool(transaction_id),
        )

        if not plan_id:
            return Response({"error": "plan_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        calc = _calculate_video_plan_purchase(
            user=user,
            plan_id=plan_id,
            coupon_code=coupon_code,
            coupon_discount_input=coupon_discount_input,
        )
        if not calc["ok"]:
            if calc["status"] == 404:
                logger.warning("buy-video-plan failed: plan not found user_id=%s plan_id=%s", getattr(user, "id", None), plan_id)
            return Response({"error": calc["error"]}, status=calc["status"])
        plan = calc["plan"]

        # Persist address if passed, else fallback to user profile fields.
        address = request.data.get("address") or getattr(user, "address", None)
        city = request.data.get("city") or getattr(user, "city", None)
        country = request.data.get("country") or getattr(user, "country", None)
        contact = request.data.get("contact") or getattr(user, "contact_no", None)

        coupon_model = calc["coupon_model"]
        coupon_discount = calc["coupon_discount"]
        plan_amount = calc["plan_amount"]
        gst_amount = calc["gst_amount"]
        final_amount = calc["final_amount"]
        purchase_type = calc["purchase_type"]

        try:
            with transaction.atomic():
                purchase = SubscribedVideo.objects.create(
                    plan=plan,
                    transaction_id=transaction_id,
                    doctor_price=_to_decimal(plan.doctor_price),
                    coupon=coupon_code or None,
                    coupon_discount=coupon_discount if purchase_type == SubscribedVideo.TYPE_COUPON_APPLIED else Decimal("0"),
                    plan_price=plan_amount,
                    gst_price=gst_amount,
                    final_price=final_amount,
                    address=address,
                    country=country,
                    city=city,
                    contact=contact,
                    state_id=SubscribedVideo.STATE_ACTIVE,
                    type_id=purchase_type,
                    created_by=user,
                )

                user.video_credit = int(getattr(user, "video_credit", 0) or 0) + int(getattr(plan, "credit", 0) or 0)
                user.save(update_fields=["video_credit"])

                if purchase_type == SubscribedVideo.TYPE_COUPON_APPLIED and coupon_model:
                    CouponUser.objects.create(
                        coupon=coupon_model,
                        plan=plan,
                        subscribed_video_id=purchase.id,
                        coupon_code=coupon_code,
                        state_id=CouponUser.STATE_ACTIVE,
                        created_by=user,
                    )

            logger.info(
                "buy-video-plan success: user_id=%s plan_id=%s purchase_id=%s",
                getattr(user, "id", None),
                plan_id,
                purchase.id,
            )
            return Response(
                {
                    "message": "Plan bought successfully.",
                    "purchase_id": purchase.id,
                    "detail": _legacy_user_detail(user),
                    "plan_amount": float(plan_amount),
                    "gst_amount": float(gst_amount),
                    "final_amount": float(final_amount),
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception(
                "buy-video-plan failed user_id=%s plan_id=%s",
                getattr(user, "id", None),
                plan_id,
            )
            return Response({"error": "Unable to buy video plan right now."}, status=status.HTTP_400_BAD_REQUEST)

class CheckBuyVideoPlanView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        plan_id = request.data.get("plan_id") or request.query_params.get("plan_id")
        coupon_code = request.data.get("coupon") or request.data.get("coupon_code")
        coupon_discount = _to_decimal(request.data.get("coupon_discount"), "0")

        calc = _calculate_video_plan_purchase(
            user=request.user,
            plan_id=plan_id,
            coupon_code=coupon_code,
            coupon_discount_input=coupon_discount,
        )
        if not calc["ok"]:
            return Response({"status": False, "error": calc["error"]}, status=status.HTTP_400_BAD_REQUEST)
        plan_amount = calc["plan_amount"]
        gst_amount = calc["gst_amount"]
        final_amount = calc["final_amount"]

        return Response(
            {
                "status": True,
                "message": "Plan bought successfully.",
                "plan_amount": float(plan_amount),
                "gst_amount": float(gst_amount),
                "final_amount": float(final_amount),
            },
            status=status.HTTP_200_OK,
        )

class VideoPlanListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoPlanSerializer

    def get_queryset(self):
        currency = self.request.query_params.get('currency', 'INR')
        return VideoPlan.objects.filter(state_id=1, currency_code=currency).order_by('-id')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        # Legacy iOS expects `data["list"]` contract.
        return Response({"list": serializer.data}, status=status.HTTP_200_OK)

class ApplyCouponView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        code = request.data.get("code") or request.data.get("coupon")
        plan_id = request.data.get("plan_id") or request.query_params.get("plan_id")
        if not code or not plan_id:
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)

        plan = Plan.objects.filter(plan_id=plan_id, state_id=1).first()
        coupon = Coupon.objects.filter(code=code, state_id=1).first()
        if not plan or not coupon:
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)
        if not _is_coupon_valid_now(coupon) or not _is_plan_allowed(coupon.plan_id, plan_id):
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)

        if coupon.limit and SubscribedPlan.objects.filter(coupon=code).count() >= coupon.limit:
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)
        if coupon.user_limit and SubscribedPlan.objects.filter(coupon=code, created_by=request.user).count() >= coupon.user_limit:
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)

        plan_amount = _to_decimal(plan.total_price)
        discount_amount = _coupon_discount_amount(plan_amount, _to_decimal(coupon.discount), int(coupon.type_id or 0))
        if discount_amount <= 0 or discount_amount >= plan_amount:
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)

        sub_total = plan_amount - discount_amount
        gst_amount = _to_decimal(plan.tax_price)
        final_amount = sub_total + gst_amount
        return Response(
            {
                "status": 1,
                "message": "Coupon code successfully applied!",
                "plan_amount": float(plan_amount),
                "gst_amount": float(gst_amount.quantize(Decimal("1"))),
                "coupon_discount": float(discount_amount.quantize(Decimal("1"))),
                "final_amount": float(final_amount.quantize(Decimal("1"))),
            },
            status=status.HTTP_200_OK,
        )

class ApplyVideoCouponView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        code = request.data.get("code") or request.data.get("coupon")
        plan_id = request.data.get("plan_id") or request.query_params.get("plan_id")
        if not code or not plan_id:
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)

        plan = VideoPlan.objects.filter(id=plan_id, state_id=VideoPlan.STATE_ACTIVE).first()
        coupon = VideoCoupon.objects.filter(code=code, state_id=VideoCoupon.STATE_ACTIVE).first()
        if not plan or not coupon:
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)
        if not _is_coupon_valid_now(coupon) or not _is_plan_allowed(coupon.plan_id, str(plan_id)):
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)

        if coupon.limit and CouponUser.objects.filter(coupon=coupon).count() >= coupon.limit:
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)
        if coupon.user_limit and CouponUser.objects.filter(coupon=coupon, created_by=request.user).count() >= coupon.user_limit:
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)

        plan_amount = _to_decimal(plan.total_price)
        discount_amount = _coupon_discount_amount(plan_amount, _to_decimal(coupon.amount), int(coupon.type_id or 0))
        if discount_amount <= 0 or discount_amount >= plan_amount:
            return Response({"status": 0, "message": "Invalid coupon code"}, status=status.HTTP_200_OK)

        sub_total = plan_amount - discount_amount
        gst_amount = _to_decimal(plan.tax_price)
        final_amount = sub_total + gst_amount
        return Response(
            {
                "status": 1,
                "message": "Coupon code successfully applied!",
                "plan_amount": float(plan_amount),
                "gst_amount": float(gst_amount.quantize(Decimal("1"))),
                "coupon_discount": float(discount_amount.quantize(Decimal("1"))),
                "final_amount": float(final_amount.quantize(Decimal("1"))),
            },
            status=status.HTTP_200_OK,
        )

class UpdateSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        plan_id = request.data.get("plan_id") or request.query_params.get("plan_id")
        if not plan_id:
            return Response({"error": "plan_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        plan = Plan.objects.filter(plan_id=plan_id).first()
        if not plan:
            return Response({"error": "Plan not found."}, status=status.HTTP_400_BAD_REQUEST)

        subscribed_plan = (
            SubscribedPlan.objects.filter(created_by=request.user, state_id__in=[1, 2])
            .order_by("-id")
            .first()
        )
        if not subscribed_plan or not subscribed_plan.subscription_id:
            return Response({"error": "Subscription not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                subscribed_plan = SubscribedPlan.objects.select_for_update().get(id=subscribed_plan.id)
                subscribed_plan.upcoming_plan_id = plan.id
                subscribed_plan.upcoming_state = UPCOMING_STATE_UPCOMING
                subscribed_plan.save(update_fields=["upcoming_plan_id", "upcoming_state"])

                if _is_live_razorpay_subscription(subscribed_plan.subscription_id):
                    schedule_change_at = "now" if _is_free_trial_subscription(subscribed_plan) else "cycle_end"
                    api_response = _patch_razorpay_subscription_plan(
                        subscription_id=subscribed_plan.subscription_id,
                        plan_id=plan_id,
                        schedule_change_at=schedule_change_at,
                    )
                    if isinstance(api_response, dict) and api_response.get("error"):
                        raise ValueError(api_response["error"].get("description") or "Razorpay update failed.")

            return Response({"detail": "Subscription updated successfully."}, status=status.HTTP_200_OK)
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
            logger.exception(
                "update-subscription failed user_id=%s plan_id=%s sub_id=%s",
                getattr(request.user, "id", None),
                plan_id,
                getattr(subscribed_plan, "subscription_id", None),
            )
            return Response({"error": "Unable to update subscription right now."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception(
                "update-subscription unexpected failure user_id=%s plan_id=%s sub_id=%s",
                getattr(request.user, "id", None),
                plan_id,
                getattr(subscribed_plan, "subscription_id", None),
            )
            return Response({"error": "Unable to update subscription right now."}, status=status.HTTP_400_BAD_REQUEST)

class FreeSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        plan_id = request.data.get("plan_id") or request.query_params.get("plan_id")
        coupon_code = request.data.get("coupon") or request.data.get("code")
        if not plan_id:
            return Response({"error": "plan_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not coupon_code:
            return Response({"error": "coupon code is required"}, status=status.HTTP_400_BAD_REQUEST)

        plan = Plan.objects.filter(plan_id=plan_id).first()
        if not plan:
            return Response({"error": "Plan not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Mirror PHP guard: block if user already has non-free active plan.
        has_paid = SubscribedPlan.objects.filter(created_by=user, state_id=1).exclude(plan_type=0).exists()
        if has_paid:
            return Response({"error": "You are already on a plan."}, status=status.HTTP_400_BAD_REQUEST)

        coupon = Coupon.objects.filter(code=coupon_code, state_id=1).first()
        if not coupon:
            return Response({"error": "coupon not found"}, status=status.HTTP_400_BAD_REQUEST)

        address = request.data.get("address") or getattr(user, "address", None)
        city = request.data.get("city") or getattr(user, "city", None)
        country = request.data.get("country") or getattr(user, "country", None)
        contact = request.data.get("contact") or getattr(user, "contact_no", None)

        with transaction.atomic():
            free_plan = SubscribedPlan.objects.filter(created_by=user, plan_type=0, state_id=1).order_by("-id").first()
            start_date = free_plan.end_date if free_plan and free_plan.end_date else timezone.now()
            end_date = start_date + timedelta(days=int(plan.duration or 0))

            subscribed = SubscribedPlan.objects.create(
                plan=plan,
                plan_type=0,
                state_id=1,
                start_date=start_date,
                end_date=end_date,
                renewal_date=end_date,
                subscription_id=str(plan.id),
                plan_price=_to_decimal(plan.total_price),
                gst_price=_to_decimal(plan.tax_price),
                final_price=_to_decimal(plan.final_price),
                coupon=coupon_code,
                coupon_free_trial_days=0,
                type_id=1,
                upcoming_plan_id=plan.id,
                upcoming_state=1,
                address=address,
                city=city,
                country=country,
                contact=contact,
                created_by=user,
            )

            if free_plan:
                free_plan.state_id = 3
                free_plan.save(update_fields=["state_id"])

        return Response(
            {
                "message": "Subscription created successfully.",
                "detail": _legacy_user_detail(user),
                "subscription_id": subscribed.id,
            },
            status=status.HTTP_200_OK,
        )

class OneTimeSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        plan_id = request.data.get("plan_id") or request.query_params.get("plan_id")
        coupon_code = request.data.get("coupon")
        address = request.data.get("address") or getattr(user, "address", None)
        city = request.data.get("city") or getattr(user, "city", None)
        country = request.data.get("country") or getattr(user, "country", None)
        contact = request.data.get("contact") or getattr(user, "contact_no", None)
        if not plan_id:
            return Response({"error": "plan_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        plan = Plan.objects.filter(plan_id=plan_id, state_id=1).first()
        if not plan:
            return Response({"error": "Plan not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                coupon = None
                coupon_days = 0
                final_price = _to_decimal(plan.final_price)
                gst_price = _to_decimal(plan.tax_price)
                if coupon_code:
                    coupon = Coupon.objects.filter(code=coupon_code, state_id=1).first()
                    if not coupon or not _is_coupon_valid_now(coupon):
                        return Response({"error": "coupon not found"}, status=status.HTTP_400_BAD_REQUEST)
                    coupon_days = int(coupon.no_of_free_trial_days or 0)
                    discount_amount = _coupon_discount_amount(
                        _to_decimal(plan.total_price), _to_decimal(coupon.discount), int(coupon.type_id or 0)
                    )
                    discounted = max(Decimal("0"), _to_decimal(plan.total_price) - discount_amount)
                    final_price = discounted + gst_price

                now = timezone.now()
                latest_paid = (
                    SubscribedPlan.objects.filter(created_by=user, plan_type=1, state_id__in=[1, 2])
                    .order_by("-end_date")
                    .first()
                )
                start_date = latest_paid.end_date if latest_paid and latest_paid.end_date else now
                state_id = 2 if latest_paid and latest_paid.end_date and latest_paid.end_date > now else 1
                end_date = start_date + timedelta(days=int(plan.duration or 0) + coupon_days + int(plan.incentive_days or 0))

                subscribed = SubscribedPlan.objects.create(
                    plan=plan,
                    plan_type=1,
                    state_id=0,  # created; gets activated in authenticate-one-time-sub
                    start_date=start_date,
                    end_date=end_date,
                    renewal_date=end_date,
                    subscription_id=str(plan.id),
                    plan_price=_to_decimal(plan.total_price),
                    gst_price=gst_price,
                    final_price=final_price,
                    coupon=coupon_code or None,
                    coupon_free_trial_days=coupon_days,
                    type_id=1 if coupon_code else 2,
                    upcoming_plan_id=plan.id,
                    upcoming_state=state_id,
                    address=address,
                    city=city,
                    country=country,
                    contact=contact,
                    created_by=user,
                )
                return Response(
                    {
                        "message": "Subscription created successfully.",
                        "subscription_id": subscribed.id,
                    },
                    status=status.HTTP_200_OK,
                )
        except Exception:
            logger.exception("one-time-subscription failed user_id=%s plan_id=%s", getattr(user, "id", None), plan_id)
            return Response({"error": "Unable to create one-time subscription right now."}, status=status.HTTP_400_BAD_REQUEST)


class CurrencyListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        currencies = Currency.objects.filter(state_id=Currency.STATE_ACTIVE).values(
            "country", "code", "symbol", "conversion_rate"
        )
        return Response({"list": list(currencies)}, status=status.HTTP_200_OK)
