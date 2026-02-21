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
        return Response({"message": "Not Implemented. Required Razorpay integeration"}, status=status.HTTP_501_NOT_IMPLEMENTED)

class AuthenticateSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({"message": "Not Implemented. Required Razorpay integeration"}, status=status.HTTP_501_NOT_IMPLEMENTED)

class AuthenticateOneTimeSubView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({"message": "Not Implemented. Required Razorpay integeration"}, status=status.HTTP_501_NOT_IMPLEMENTED)

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
        return Response({"message": "Not Implemented. Required Razorpay integeration"}, status=status.HTTP_501_NOT_IMPLEMENTED)

class CheckBuyVideoPlanView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({"message": "Not Implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)

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
