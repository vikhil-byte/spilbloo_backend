from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from .models import DoctorSlot, SlotBooking, Slot, Notification, PrescriptionUpload
from .serializers import DoctorSlotSerializer, SlotBookingSerializer
from django.db import transaction
from django.utils import timezone
from core.models import RefundLog
from django.contrib.auth import get_user_model
from plans.models import SubscribedPlan
from django.core.mail import send_mail
from django.conf import settings
import os

User = get_user_model()
import json
import logging

logger = logging.getLogger(__name__)


def send_event_email(to_email, subject, message):
    if not to_email:
        return
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")
    try:
        send_mail(subject, message, from_email, [to_email], fail_silently=False)
    except Exception:
        logger.info("email fallback log to=%s subject=%s", to_email, subject)


def _send_fcm(token, title, description):
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except Exception:
        return False

    try:
        app = firebase_admin.get_app()
    except Exception:
        app = None

    try:
        if app is None:
            cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                app = firebase_admin.initialize_app(cred)
            else:
                service_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
                if not service_json:
                    return False
                cred = credentials.Certificate(json.loads(service_json))
                app = firebase_admin.initialize_app(cred)

        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=description),
            data={"title": title, "description": description},
        )
        messaging.send(msg, app=app)
        return True
    except Exception:
        return False

def send_push_notification(user, title, description):
    if not user:
        return
    token = getattr(user, "device_token", "") if hasattr(user, "device_token") else ""
    sent = False
    if token:
        sent = _send_fcm(token, title, description)
    logger.info(
        "push notify user_id=%s has_device_token=%s sent=%s title=%s",
        user.id,
        bool(token),
        sent,
        title,
    )

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
        except Exception:
            logger.exception("add-schedule failed for doctor_id=%s", getattr(doctor, "id", None))
            return Response({"error": "Unable to save availability."}, status=status.HTTP_400_BAD_REQUEST)


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
        except Exception:
            logger.exception("update-schedule failed for doctor_id=%s", getattr(doctor, "id", None))
            return Response({"error": "Unable to update availability."}, status=status.HTTP_400_BAD_REQUEST)


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
                # Deduction Logic (SlotController.php 370-399)
                deducted = False
                type_id = 0
                
                # Priority 1: User's video_credit
                if patient.video_credit > 0:
                     patient.video_credit -= 1 # User::ONE_VIDEO_CREDIT
                     patient.save(update_fields=['video_credit'])
                     type_id = 1 # SlotBooking::TYPE_BY_VIDEO_PLAN (assumed mapping)
                     deducted = True
                
                # Priority 2: SubscribedPlan's video session
                if not deducted:
                     plan = SubscribedPlan.objects.filter(
                         created_by=patient,
                         state_id=1 # STATE_ACTIVE
                     ).first()
                     if plan and plan.no_of_video_session > 0:
                          plan.no_of_video_session -= 1
                          plan.save(update_fields=['no_of_video_session'])
                          type_id = 2 # SlotBooking::TYPE_BY_TEXT_SUBSCRIPTION
                          deducted = True
                
                if not deducted:
                     return Response({"error": "Not enough video credits for booking."}, status=status.HTTP_400_BAD_REQUEST)

                booking = SlotBooking.objects.create(
                    slot_id=slot_id,
                    start_time=start_time,
                    end_time=end_time,
                    doctor_id=doctor_id,
                    created_by=patient,
                    state_id=2, # STATE_REQUEST
                    type_id=type_id,
                    is_active=0 # IS_ROOM_ACTIVE_NO
                )

                # Notifications...
                msg = f"{patient.full_name} sent you a request for a session."
                Notification.objects.create(
                    to_user_id=doctor_id,
                    created_by=patient,
                    title=msg,
                    html=msg
                )
                
                doctor_user = User.objects.filter(id=doctor_id).first()
                send_push_notification(doctor_user, "New Booking Request", msg)
                send_event_email(
                    getattr(doctor_user, "email", ""),
                    "New booking request",
                    msg,
                )
            
            return Response({
                "message": "Booking added successfully.",
                "details": SlotBookingSerializer(booking).data
            }, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("booking creation failed for patient_id=%s doctor_id=%s", getattr(patient, "id", None), doctor_id)
            return Response({"error": "Unable to create booking right now."}, status=status.HTTP_400_BAD_REQUEST)

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

    def post(self, request, booking_id=None):
        booking_id = booking_id or request.data.get("booking_id") or request.query_params.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = SlotBooking.objects.get(id=booking_id)
            booking.state_id = 3 # ACCEPT
            booking.save()
            return Response({"message": "Booking accepted successfully"}, status=status.HTTP_200_OK)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No Booking found"}, status=status.HTTP_400_BAD_REQUEST)

class DoctorRescheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id=None):
        doctor = request.user
        booking_id = booking_id or request.data.get("booking_id") or request.query_params.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = SlotBooking.objects.get(id=booking_id, doctor_id=doctor.id)
            if booking.doctor_reschedule == 1: # YES
                return Response({"error": "You have already rescheduled the booking once."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Save old times (actionDoctorReschedule 652-653)
            booking.old_start_time = booking.start_time
            booking.old_end_time = booking.end_time
            
            # Load new times from post
            booking.start_time = request.data.get('start_time', booking.start_time)
            booking.end_time = request.data.get('end_time', booking.end_time)
            booking.state_id = 3 # STATE_ACCEPT
            booking.doctor_reschedule = 1 # YES
            
            booking.save()
            
            msg = f"{doctor.full_name} has rescheduled your video session."
            Notification.objects.create(
                to_user_id=booking.created_by_id,
                created_by=doctor,
                title=msg,
                html=msg
            )
            send_event_email(
                getattr(booking.created_by, "email", ""),
                "Session rescheduled by therapist",
                msg,
            )
            return Response({
                "message": "Booking reschedule successfully.",
                "details": SlotBookingSerializer(booking).data
            }, status=status.HTTP_200_OK)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No booking found."}, status=status.HTTP_400_BAD_REQUEST)

class DoctorCancelView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id=None):
        doctor = request.user
        booking_id = booking_id or request.data.get("booking_id") or request.query_params.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                booking = SlotBooking.objects.select_for_update().get(id=booking_id, doctor_id=doctor.id)
                if booking.state_id == 4: # STATE_CANCELED
                     return Response({"error": "Booking is already canceled."}, status=status.HTTP_400_BAD_REQUEST)
                
                booking.state_id = 4 # CANCELED
                booking.is_refunded = 1 # YES
                booking.cancel_reason = "Therapist canceled the video session"
                booking.save()

                # Refund Logic (SlotController.php 714-736)
                patient = booking.created_by
                if booking.type_id == 2: # TYPE_BY_TEXT_SUBSCRIPTION
                     plan = SubscribedPlan.objects.filter(created_by=patient, state_id=1).first()
                     if plan:
                          plan.no_of_video_session += 1
                          plan.save(update_fields=['no_of_video_session'])
                     else:
                          patient.video_credit += 1
                          patient.save(update_fields=['video_credit'])
                else:
                     patient.video_credit += 1
                     patient.save(update_fields=['video_credit'])

                # Create RefundLog
                RefundLog.objects.create(
                    reason=f"Therapist {doctor.full_name} canceled the video session",
                    doctor=doctor,
                    created_by=patient,
                    credit=1,
                    booking_id=booking.id,
                    state_id=1
                )

                msg = f"{doctor.full_name} has cancelled your video session."
                Notification.objects.create(
                    to_user_id=patient.id,
                    created_by=doctor,
                    title=msg,
                    html=msg
                )
                send_event_email(
                    getattr(patient, "email", ""),
                    "Session cancelled by therapist",
                    msg,
                )

                return Response({
                    "message": "Booking canceled successfully.",
                    "details": SlotBookingSerializer(booking).data
                }, status=status.HTTP_200_OK)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No booking found."}, status=status.HTTP_400_BAD_REQUEST)

class PatientRescheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id=None):
        user = request.user
        booking_id = booking_id or request.data.get("booking_id") or request.query_params.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = SlotBooking.objects.get(id=booking_id, created_by_id=user.id)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No booking found."}, status=status.HTTP_400_BAD_REQUEST)

        if booking.patient_reschedule == 1:
            return Response({"error": "You have already rescheduled the booking once."}, status=status.HTTP_400_BAD_REQUEST)

        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")
        if not start_time or not end_time:
            return Response({"error": "Data not posted."}, status=status.HTTP_400_BAD_REQUEST)

        booking.old_start_time = booking.start_time
        booking.old_end_time = booking.end_time
        booking.start_time = start_time
        booking.end_time = end_time
        booking.state_id = 3  # STATE_ACCEPT
        booking.patient_reschedule = 1  # YES
        booking.save()

        message = f"{user.full_name} has rescheduled your video session to"
        Notification.objects.create(
            to_user_id=booking.doctor_id,
            created_by=user,
            title=message,
            html=message,
            model_type="SlotBooking",
        )
        doctor_user = User.objects.filter(id=booking.doctor_id).first()
        send_event_email(
            getattr(doctor_user, "email", ""),
            "Session rescheduled by patient",
            message,
        )
        return Response(
            {
                "details": SlotBookingSerializer(booking).data,
                "message": "Booking reschedule successfully.",
            },
            status=status.HTTP_200_OK,
        )

class ConfirmRescheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id=None):
        booking_id = booking_id or request.data.get("booking_id") or request.query_params.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = SlotBooking.objects.get(id=booking_id)
            booking.is_reschedule_confirm = 1 # YES
            booking.save()
            return Response({"message": "Reschedule confirmed successfully"}, status=status.HTTP_200_OK)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No Booking found"}, status=status.HTTP_400_BAD_REQUEST)


class UploadPrescriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        booking_id = request.data.get("booking_id") or request.query_params.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = SlotBooking.objects.get(id=booking_id)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No booking found."}, status=status.HTTP_400_BAD_REQUEST)

        prescription_file = request.FILES.get("prescription_file") or request.FILES.get("file")
        notes = request.data.get("notes", "")
        upload = PrescriptionUpload.objects.create(
            booking_id=booking.id,
            notes=notes,
            file=prescription_file,
            created_by=request.user,
        )
        return Response(
            {
                "message": "Prescription uploaded successfully.",
                "booking_id": booking.id,
                "prescription_id": upload.id,
                "file_url": upload.file.url if upload.file else "",
            },
            status=status.HTTP_200_OK,
        )


class CheckSessionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        booking_id = request.data.get("booking_id") or request.query_params.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = SlotBooking.objects.get(id=booking_id)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No booking found."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Session status fetched successfully.",
                "booking_id": booking.id,
                "is_active": int(getattr(booking, "is_active", 0) or 0),
                "is_call_end": int(getattr(booking, "is_call_end", 0) or 0),
            },
            status=status.HTTP_200_OK,
        )


class CheckVideoLinkView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        booking_id = request.data.get("booking_id") or request.query_params.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = SlotBooking.objects.get(id=booking_id)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No booking found."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Video link fetched successfully.",
                "booking_id": booking.id,
                "room_id": getattr(booking, "room_id", "") or "",
            },
            status=status.HTTP_200_OK,
        )
