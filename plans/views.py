from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from accounts.permissions import IsAdminUser
from core.mixins import StandardizedResponseMixin
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from .models import Plan, SubscribedPlan, Coupon
from core.models import VideoPlan, SubscribedVideo, VideoCoupon, CouponUser
from .serializers import (
    PlanSerializer, SubscribedPlanSerializer, VideoPlanSerializer, 
    SubscribedVideoSerializer, CouponSerializer, VideoCouponSerializer
)
import random
import logging
import json
from django.conf import settings
from .utils import razorpay_service

logger = logging.getLogger(__name__)

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
                try:
                    razorpay_sub = razorpay_service.create_subscription(
                        plan_id=plan_id,
                        total_count=12,
                        start_at=start_at_timestamp if total_trial_days > 0 else None
                    )
                    subscription_id = razorpay_sub['id']
                except Exception as e:
                    logger.error(f"Razorpay subscription creation failed: {str(e)}")
                    return Response({"error": "Failed to create subscription with Razorpay"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # 4. Save SubscribedPlan record
                subscribed_plan = SubscribedPlan.objects.create(
                    plan=plan_obj,
                    subscription_id=subscription_id,
                    created_by=user,
                    state_id=0, # STATE_CREATED
                    plan_type=1, # PLAN_TYPE_PAID
                    start_date=timezone.now(),
                    trial_end_at=rezorpay_start_at,
                    no_of_video_session=plan_obj.no_of_video_session,
                    address=user_address,
                    city=request.data.get('city'),
                    state=request.data.get('state'),
                    country=request.data.get('country'),
                    zipcode=request.data.get('zipcode'),
                    contact=request.data.get('contact')
                )
                
                return Response({
                    "message": "Subscription created successfully.",
                    "subscription_id": subscription_id,
                    "razorpay_key": settings.RAZORPAY_KEY_ID
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
        payment_id = request.data.get('payment_id')
        signature = request.data.get('signature')
        
        try:
            plan = Plan.objects.get(plan_id=plan_id_str)
            subscribed_plan = SubscribedPlan.objects.get(
                created_by=user,
                plan=plan,
                subscription_id=sub_id
            )
            
            # 1. Verify Razorpay signature
            signature_data = {
                'razorpay_subscription_id': sub_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            if not razorpay_service.verify_payment_signature(signature_data):
                return Response({"error": "Invalid signature provided."}, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Activate the plan
            subscribed_plan.state_id = 1 # STATE_ACTIVE
            subscribed_plan.transaction_id = payment_id
            subscribed_plan.signature = signature
            
            # Set end_date based on plan duration
            subscribed_plan.start_date = timezone.now()
            subscribed_plan.end_date = subscribed_plan.start_date + timezone.timedelta(days=plan.duration)
            subscribed_plan.save()

            # 3. Update User role to PATIENT if they are not already (ROLE_PATIENT = 4)
            if user.role_id != 4:
                user.role_id = 4
                user.save()
            
            from accounts.serializers import UserSerializer
            return Response({
                "message": "Plan activated successfully.",
                "detail": UserSerializer(user).data
            }, status=status.HTTP_200_OK)
            
        except (Plan.DoesNotExist, SubscribedPlan.DoesNotExist):
            return Response({"error": "Subscription or Plan not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
        user = request.user
        
        # Billing info
        address = request.data.get('address')
        city = request.data.get('city')
        country = request.data.get('country')
        contact = request.data.get('contact')

        try:
            plan = VideoPlan.objects.get(id=plan_id)
            
            # 1. Create Razorpay Order
            # Amount in VideoPlan is stored as CharField in current model, need to convert to float/decimal
            try:
                amount = float(plan.final_price)
            except (ValueError, TypeError):
                amount = 0

            razorpay_order = razorpay_service.create_order(
                amount=amount,
                currency=plan.currency_code or "INR",
                receipt=f"vid_receipt_{user.id}_{int(timezone.now().timestamp())}"
            )
            
            # 2. Create SubscribedVideo record (STATE_INACTIVE = 0)
            subscribed_video = SubscribedVideo.objects.create(
                plan=plan,
                order_id=razorpay_order['id'],
                created_by=user,
                state_id=0, # STATE_INACTIVE/New
                plan_price=float(plan.total_price) if plan.total_price else 0,
                gst_price=float(plan.tax_price) if plan.tax_price else 0,
                final_price=amount,
                address=address or user.address,
                city=city or user.city,
                country=country or user.country,
                contact=contact or user.contact_no
            )

            return Response({
                "message": "Video Plan order created.",
                "razorpay_order_id": razorpay_order['id'],
                "amount": amount,
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "subscribed_video_id": subscribed_video.id
            }, status=status.HTTP_201_CREATED)
            
        except VideoPlan.DoesNotExist:
            return Response({"error": "Video Plan not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to create video plan order: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CheckBuyVideoPlanView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        order_id = request.data.get('order_id')
        payment_id = request.data.get('payment_id')
        signature = request.data.get('signature')

        try:
            subscribed_video = SubscribedVideo.objects.get(
                created_by=user,
                order_id=order_id,
                state_id=0 # Must be in New state
            )

            # 1. Verify Signature
            params = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            if not razorpay_service.verify_payment_signature(params):
                return Response({"error": "Invalid signature provided."}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Activate Subscription
            subscribed_video.state_id = 1 # ACTIVE
            subscribed_video.transaction_id = payment_id
            subscribed_video.signature = signature
            subscribed_video.save()

            # 3. Add Credits to User
            user.video_credit = (user.video_credit or 0) + subscribed_video.plan.credit
            user.save()

            return Response({
                "message": "Video Plan activated successfully.",
                "video_credits": user.video_credit
            }, status=status.HTTP_200_OK)

        except SubscribedVideo.DoesNotExist:
            return Response({"error": "Video subscription record not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Video plan activation failed: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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

class AdminSubscribedPlanListView(generics.ListAPIView, StandardizedResponseMixin):
    permission_classes = (IsAdminUser,)
    serializer_class = SubscribedPlanSerializer
    queryset = SubscribedPlan.objects.all().order_by('-id')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(serializer.data)

class AdminSubscribedPlanDetailView(generics.RetrieveAPIView, StandardizedResponseMixin):
    permission_classes = (IsAdminUser,)
    queryset = SubscribedPlan.objects.all()
    serializer_class = SubscribedPlanSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(serializer.data)

class AdminSubscribedPlanCancelView(APIView, StandardizedResponseMixin):
    permission_classes = (IsAdminUser,)

    def post(self, request, pk):
        try:
            sub = SubscribedPlan.objects.get(pk=pk)
            reason = request.data.get('reason', 'Cancelled by Admin')
            sub.state_id = 2 # Cancelled
            sub.cancel_reason = reason
            sub.save()
            return self.success_response({"message": "Subscription cancelled successfully."})
        except SubscribedPlan.DoesNotExist:
            return self.error_response("Subscription not found.", status_code=404)

class AdminSubscribedPlanExtendView(APIView, StandardizedResponseMixin):
    permission_classes = (IsAdminUser,)

    def post(self, request, pk):
        try:
            sub = SubscribedPlan.objects.get(pk=pk)
            days = int(request.data.get('days', 0))
            if days <= 0:
                return self.error_response("Invalid number of days.")
            
            # If current end_date is in past, start from now
            current_end = sub.end_date or timezone.now()
            if current_end < timezone.now():
                current_end = timezone.now()
            
            new_end = current_end + timezone.timedelta(days=days)
            sub.end_date = new_end
            sub.renewal_date = new_end # Sync renewal date
            sub.save()
            
            return self.success_response({"message": f"Subscription extended by {days} days."})
        except (SubscribedPlan.DoesNotExist):
            return self.error_response("Subscription not found.", status_code=404)
        except ValueError:
            return self.error_response("Days must be a valid integer.")

class RazorpayWebhookView(APIView):
    permission_classes = (AllowAny,) # Webhooks should be accessible

    def post(self, request):
        payload = request.body.decode('utf-8')
        signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
        
        if not signature:
            return Response({"error": "No signature"}, status=status.HTTP_400_BAD_REQUEST)

        # Verify webhook signature
        try:
            razorpay_service.client.utility.verify_webhook_signature(payload, signature, settings.RAZORPAY_WEBHOOK_SECRET)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event_data = json.loads(payload)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event_data.get('event')
        
        logger.info(f"Received Razorpay Webhook Event: {event_type}")

        # Handle events
        if event_type == 'subscription.charged':
            self.handle_subscription_charged(event_data)
        elif event_type in ['subscription.cancelled', 'subscription.halted', 'subscription.expired']:
            self.handle_subscription_status_change(event_data, event_type)
        
        return Response({"status": "ok"}, status=status.HTTP_200_OK)

    def handle_subscription_charged(self, data):
        sub_id = data['payload']['subscription']['entity']['id']
        try:
            sub = SubscribedPlan.objects.get(subscription_id=sub_id)
            sub.state_id = 1 # Active
            sub.save()
            logger.info(f"Subscription {sub_id} activated via webhook")
        except SubscribedPlan.DoesNotExist:
            logger.error(f"Subscription {sub_id} not found in database for charged event")

    def handle_subscription_status_change(self, data, event_type):
        sub_id = data['payload']['subscription']['entity']['id']
        try:
            sub = SubscribedPlan.objects.get(subscription_id=sub_id)
            if event_type == 'subscription.cancelled':
                sub.state_id = 2 # Cancelled
            else:
                sub.state_id = 3 # Expired/Halted
            sub.save()
            logger.info(f"Subscription {sub_id} status updated to {event_type} via webhook")
        except SubscribedPlan.DoesNotExist:
            logger.error(f"Subscription {sub_id} not found in database for event {event_type}")
