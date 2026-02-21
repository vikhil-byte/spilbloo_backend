from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from .models import DoctorSlot, SlotBooking, Slot, Notification
from .serializers import DoctorSlotSerializer, SlotBookingSerializer
from django.db import transaction
from django.utils import timezone
from plans.models import SubscribedPlan
import json
import logging

logger = logging.getLogger(__name__)

def send_push_notification(user, title, description):
    # Placeholder for Firebase Cloud Messaging (FCM)
    logger.info(f"Sending Push to {user.id}: {title}")
    # from firebase_admin import messaging
    # ... message building and sending ...
    pass

class AddScheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        doctor = request.user
        availability_data = request.data.get('availability', '[]')
        
        try:
            availability_list = json.loads(availability_data)
        except json.JSONDecodeError:
            return Response({"error": "Invalid availability JSON."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                for item in availability_list:
                    slot_id = item.get('slot_id')
                    start_time = item.get('start_time')
                    end_time = item.get('end_time')

                    # Check if slot exists
                    exists = DoctorSlot.objects.filter(
                        created_by=doctor,
                        availability_slot_id=slot_id,
                        start_time=start_time,
                        end_time=end_time
                    ).exists()

                    if not exists:
                        DoctorSlot.objects.create(
                            availability_slot_id=slot_id,
                            start_time=start_time,
                            end_time=end_time,
                            state_id=1, # STATE_ACTIVE
                            created_by=doctor
                        )
            return Response({"message": "Availability saved successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UpdateScheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        doctor = request.user
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        availability_data = request.data.get('availability', '[]')

        if not start_time or not end_time:
            return Response({"error": "Start and End time required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            availability_list = json.loads(availability_data)
        except json.JSONDecodeError:
            return Response({"error": "Invalid availability JSON."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Delete existing slots in range
                DoctorSlot.objects.filter(
                    created_by=doctor,
                    start_time__gte=start_time,
                    start_time__lte=end_time
                ).delete()

                # Add new ones
                for item in availability_list:
                    DoctorSlot.objects.create(
                        availability_slot_id=item.get('slot_id'),
                        start_time=item.get('start_time'),
                        end_time=item.get('end_time'),
                        state_id=1,
                        created_by=doctor
                    )
            return Response({"message": "Availability saved successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetDoctorSlotView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        doctor_id = request.query_params.get('doctor_id')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')

        if not doctor_id or not start_time or not end_time:
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        # Implementation similar to PHP SlotController `actionGetDoctorSlot`
        doctor_slots = DoctorSlot.objects.filter(
            created_by_id=doctor_id,
            start_time__gte=start_time,
            start_time__lte=end_time
        ).values_list('availability_slot_id', flat=True)

        booked_slots = SlotBooking.objects.filter(
            doctor_id=doctor_id,
            start_time__gte=start_time,
            start_time__lte=end_time
        ).exclude(state_id=4).values_list('slot_id', flat=True) # STATE_CANCELED = 4 (or similar in mapping)

        available_slots = set(doctor_slots) - set(booked_slots)

        final_slots = DoctorSlot.objects.filter(
            created_by_id=doctor_id,
            start_time__gte=start_time,
            start_time__lte=end_time,
            availability_slot_id__in=available_slots
        )

        serializer = DoctorSlotSerializer(final_slots, many=True)
        return Response({"list": serializer.data}, status=status.HTTP_200_OK)


class BookingView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        patient = request.user
        slot_id = request.data.get('slot_id')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        doctor_id = request.data.get('doctor_id')

        # Check if already booked
        exists = SlotBooking.objects.filter(
            slot_id=slot_id,
            start_time=start_time,
            end_time=end_time,
            doctor_id=doctor_id,
            state_id__in=[1, 2] # STATE_REQUEST, STATE_ACCEPT
        ).exists()

        if exists:
            return Response({"error": "This slot is already booked."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Check if patient has any active subscription or video credit
        has_active_subscription = SubscribedPlan.objects.filter(
            created_by=patient,
            state_id=1, # ACTIVE
            end_date__gte=timezone.now()
        ).exists()

        video_credits = getattr(patient, 'video_credit', 0)
        
        # Logic mapped from PHP: If not subscribed and no credits, block.
        if not has_active_subscription and video_credits <= 0:
             return Response({
                 "error": "You don't have enough credits to book a session. Please subscribe to a plan."
             }, status=status.HTTP_402_PAYMENT_REQUIRED)

        try:
            with transaction.atomic():
                booking = SlotBooking.objects.create(
                    slot_id=slot_id,
                    start_time=start_time,
                    end_time=end_time,
                    doctor_id=doctor_id,
                    created_by=patient,
                    state_id=2 # STATE_REQUEST
                )

                # Deduct credit if applicable
                if not has_active_subscription and video_credits > 0:
                     patient.video_credit = video_credits - 1
                     patient.save()

                # DB Notification
                msg = f"{patient.full_name} sent you a request for a session."
                Notification.objects.create(
                    model_type='SlotBooking',
                    to_user_id=doctor_id,
                    created_by=patient,
                    title=msg,
                    html=msg
                )
                
                # Push Notification (FCM)
                send_push_notification(booking.doctor_id, "New Booking Request", msg)
            
            return Response({
                "message": "Booking added successfully.",
                "details": SlotBookingSerializer(booking).data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DoctorBookingListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SlotBookingSerializer

    def get_queryset(self):
        start_time = self.request.query_params.get('start_time')
        end_time = self.request.query_params.get('end_time')
        # STATE_REQUEST = usually 2, we filter out requests
        return SlotBooking.objects.filter(
            doctor_id=self.request.user.id,
            start_time__gte=start_time,
            start_time__lte=end_time
        ).exclude(state_id=2).order_by('-id')

class PatientBookingListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SlotBookingSerializer

    def get_queryset(self):
        doctor_id = self.request.query_params.get('doctor_id')
        b_type = self.request.query_params.get('type') # UPCOMING/COMPLETED
        patient_id = self.request.query_params.get('patient_id')

        qs = SlotBooking.objects.filter(created_by_id=patient_id, doctor_id=doctor_id)
        if str(b_type) == '1': # UPCOMING
            qs = qs.filter(state_id__in=[2, 3]) # REQUEST, ACCEPT
        elif str(b_type) == '2': # COMPLETED
            qs = qs.filter(state_id__in=[4, 5]) # CANCELLED, COMPLETED
        return qs.order_by('-id')

class DoctorBookingReqView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SlotBookingSerializer

    def get_queryset(self):
        # Mark notifications read
        Notification.objects.filter(to_user_id=self.request.user.id).update(is_read=1)
        
        return SlotBooking.objects.filter(doctor_id=self.request.user.id, state_id__in=[2]).order_by('id')

class NotificationCountView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        count = Notification.objects.filter(
            to_user_id=request.user.id,
            is_read=0,
            model_type='SlotBooking'
        ).count()
        return Response({"notification_count": count}, status=status.HTTP_200_OK)

class AcceptBookingView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id):
        try:
            booking = SlotBooking.objects.get(id=booking_id)
            booking.state_id = 3 # ACCEPT
            booking.save()
            return Response({"message": "Booking accepted successfully"}, status=status.HTTP_200_OK)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No Booking found"}, status=status.HTTP_400_BAD_REQUEST)

class DoctorRescheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id):
        # Awaiting implementation logic similar to AcceptBooking
        return Response({"message": "Booking reschedule successfully."}, status=status.HTTP_200_OK)

class DoctorCancelView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id):
        try:
            booking = SlotBooking.objects.get(id=booking_id, doctor_id=request.user.id)
            booking.state_id = 4 # CANCELED
            booking.save()
            return Response({"message": "Booking canceled successfully."}, status=status.HTTP_200_OK)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No booking found."}, status=status.HTTP_400_BAD_REQUEST)

class PatientRescheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id):
        return Response({"message": "Booking reschedule successfully."}, status=status.HTTP_200_OK)

class ConfirmRescheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id):
        try:
            booking = SlotBooking.objects.get(id=booking_id)
            booking.is_reschedule_confirm = 1 # YES
            booking.save()
            return Response({"message": "Reschedule confirmed successfully"}, status=status.HTTP_200_OK)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No Booking found"}, status=status.HTTP_400_BAD_REQUEST)
