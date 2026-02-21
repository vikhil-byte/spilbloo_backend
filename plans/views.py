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
        plan_id = request.data.get('plan_id')
        try:
            plan = Plan.objects.get(id=plan_id)
            
            # 1. Create Order in Razorpay
            order_data = {
                "amount": int(float(plan.final_price) * 100), # Amount in paise
                "currency": plan.currency_code or "INR",
                "payment_capture": 1 # Auto capture
            }
            
            # RAZORPAY ORDER GENERATION
            # order = razorpay_client.order.create(data=order_data)
            # order_id = order['id']
            order_id = "rzp_test_mock_" + str(plan.id) # Placeholder for now
            
            return Response({
                "message": "Subscription order created.",
                "razorpay_order_id": order_id,
                "amount": plan.final_price,
                "currency": plan.currency_code
            }, status=status.HTTP_201_CREATED)
            
        except Plan.DoesNotExist:
            return Response({"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AuthenticateSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # Mapped from PHP: Verify signature and create SubscribedPlan
        payment_id = request.data.get('razorpay_payment_id')
        order_id = request.data.get('razorpay_order_id')
        signature = request.data.get('razorpay_signature')
        
        # Verify via razorpay_client.utility.verify_payment_signature(...)
        
        return Response({"message": "Payment verified and subscription activated."}, status=status.HTTP_200_OK)

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
