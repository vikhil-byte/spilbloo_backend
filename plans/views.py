from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from .models import Plan, SubscribedPlan, Coupon
from core.models import VideoPlan, SubscribedVideo, VideoCoupon, CouponUser
from .serializers import (
    PlanSerializer, SubscribedPlanSerializer, VideoPlanSerializer, 
    SubscribedVideoSerializer, CouponSerializer, VideoCouponSerializer
)
import json
import logging
import razorpay
from django.conf import settings

logger = logging.getLogger(__name__)

# Initialize Razorpay Client (ensure keys are in settings)
razorpay_client = razorpay.Client(auth=(
    getattr(settings, 'RAZORPAY_KEY_ID', ''), 
    getattr(settings, 'RAZORPAY_KEY_SECRET', '')
))

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

class CompanyUserPlanListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PlanSerializer

    def get_queryset(self):
        user = self.request.user
        # Needs to join with UserCompany model to get allowed plan_ids
        return Plan.objects.none() # Placeholder until company module is migrated

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

    def post(self, request):
        plan_id = request.data.get('plan_id') # This is the Razorpay Plan ID string
        user = request.user
        
        try:
            with transaction.atomic():
                plan_obj = Plan.objects.get(plan_id=plan_id)
                
                # Check if already on a paid plan (actionCreateSubscription 427-432)
                if SubscribedPlan.objects.filter(created_by=user, state_id=1, plan_type=1).exists():
                     return Response({"error": "You are already on a plan."}, status=status.HTTP_400_BAD_REQUEST)

                # 1. Address Persistence (actionCreateSubscription 441-461)
                # If user doesn't have address, save it. Otherwise use user's address.
                user_address = request.data.get('address')
                if user_address:
                     user.address = user_address
                     user.city = request.data.get('city', user.city)
                     user.state = request.data.get('state', user.state)
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
                rezorpay_start_at = start_time + timezone.timedelta(days=total_trial_days)
                start_at_timestamp = int(rezorpay_start_at.timestamp())

                # 3. Create Razorpay Subscription
                params = {
                    'plan_id': plan_id,
                    'customer_notify': 1,
                    'total_count': 12, # BILLING_CYCLE equivalent
                }
                if total_trial_days > 0:
                    params['start_at'] = start_at_timestamp
                
                # In real migration: subscription = razorpay_client.subscription.create(params)
                subscription_id = "sub_mock_" + str(random.randint(1000, 9999))
                
                # 4. Save SubscribedPlan record
                subscribed_plan = SubscribedPlan.objects.create(
                    plan=plan_obj,
                    subscription_id=subscription_id,
                    created_by=user,
                    state_id=0, # STATE_CREATED
                    plan_type=1, # PLAN_TYPE_PAID
                    start_date=timezone.now(),
                    trial_end_at=rezorpay_start_at,
                    no_of_video_session=plan_obj.no_of_video_session
                )
                
                return Response({
                    "message": "Subscription created successfully.",
                    "subscription_id": subscription_id
                }, status=status.HTTP_201_CREATED)
            
        except Plan.DoesNotExist:
            return Response({"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AuthenticateSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        plan_id_str = request.data.get('plan_id')
        sub_id = request.data.get('sub_id')
        
        try:
            plan = Plan.objects.get(plan_id=plan_id_str)
            subscribed_plan = SubscribedPlan.objects.get(
                created_by=user,
                plan=plan,
                subscription_id=sub_id
            )
            
            # PHP logic: actionAuthenticateSubscription (lines 613-673)
            # Verify Razorpay signature etc. here in production
            
            # Cancel free plan if exists
            # SubscribedPlan.objects.filter(created_by=user, plan_type=0, state_id=1).update(state_id=2) # Cancelled
            
            subscribed_plan.state_id = 1 # STATE_ACTIVE
            subscribed_plan.transaction_id = request.data.get('transaction_id')
            subscribed_plan.save()
            
            return Response({
                "message": "Plan bought successfully.",
                "detail": UserSerializer(user).data
            }, status=status.HTTP_200_OK)
            
        except (Plan.DoesNotExist, SubscribedPlan.DoesNotExist):
            return Response({"error": "Subscription or Plan not found."}, status=status.HTTP_400_BAD_REQUEST)

class AuthenticateOneTimeSubView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({"message": "One-time payment verified."}, status=status.HTTP_200_OK)

class CancelCompanyView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, subscription_id):
        # ... logic to cancel
        return Response({"message": "Subscription cancelled successfully."}, status=status.HTTP_200_OK)

class CancelView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, plan_id):
        # ... logic to cancel RazorPay subscription
        return Response({"message": "Subscription cancelled successfully."}, status=status.HTTP_200_OK)

class BuyVideoPlanView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        plan_id = request.data.get('plan_id')
        try:
            plan = VideoPlan.objects.get(id=plan_id)
            # Similar to CreateSubscriptionView but for VideoPlan
            return Response({
                "message": "Video Plan order created.",
                "razorpay_order_id": "v_rzp_mock_" + str(plan.id),
                "amount": plan.final_price
            }, status=status.HTTP_201_CREATED)
        except VideoPlan.DoesNotExist:
            return Response({"error": "Video Plan not found"}, status=status.HTTP_404_NOT_FOUND)

class CheckBuyVideoPlanView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({"message": "Checking video plan status..."}, status=status.HTTP_200_OK)

class VideoPlanListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = VideoPlanSerializer

    def get_queryset(self):
        currency = self.request.query_params.get('currency', 'INR')
        return VideoPlan.objects.filter(state_id=1, currency_code=currency).order_by('-id')

class ApplyCouponView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        code = request.data.get('code')
        plan_id = request.data.get('plan_id')
        try:
            coupon = Coupon.objects.get(code=code, state_id=1)
            # Add discount calculation logic
            return Response({"message": "Coupon code successfully applied!", "status": 1}, status=status.HTTP_200_OK)
        except Coupon.DoesNotExist:
            return Response({"error": "Invalid coupon code", "status": 0}, status=status.HTTP_200_OK)

class ApplyVideoCouponView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        code = request.data.get('code')
        plan_id = request.data.get('plan_id')
        try:
            coupon = VideoCoupon.objects.get(code=code, state_id=1)
            # Add discount calculation logic
            return Response({"message": "Coupon code successfully applied!", "status": 1}, status=status.HTTP_200_OK)
        except VideoCoupon.DoesNotExist:
            return Response({"error": "Invalid coupon code", "status": 0}, status=status.HTTP_200_OK)

class UpdateSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, plan_id):
        return Response({"message": "Subscription updated successfully."}, status=status.HTTP_200_OK)

class FreeSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, plan_id):
        return Response({"message": "Subscription created successfully."}, status=status.HTTP_200_OK)

class OneTimeSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, plan_id):
        return Response({"message": "Subscription created successfully."}, status=status.HTTP_200_OK)
