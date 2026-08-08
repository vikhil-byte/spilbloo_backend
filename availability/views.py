from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from .models import DoctorSlot, SlotBooking, Slot, Notification, PrescriptionUpload
from .serializers import DoctorSlotSerializer, SlotBookingSerializer, SlotSerializer
from django.db import transaction
from django.utils import timezone
from core.models import RefundLog
from django.contrib.auth import get_user_model
from plans.models import SubscribedPlan
from django.core.mail import send_mail
from django.conf import settings
import os
from core.email_service import get_email_client
from core.firebase import _send_fcm


User = get_user_model()
import json
import logging

logger = logging.getLogger(__name__)


def send_event_email(to_email, subject, message):
    if not to_email:
        return
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")
    get_email_client().send_email(
        subject=subject,
        body=message,
        to_email=to_email,
        from_email=from_email
    )


def send_html_email(to_email, subject, template_name, context):
    """Render an HTML email template and send it."""
    if not to_email:
        return
    from django.template.loader import render_to_string
    html_content = render_to_string(f"emails/{template_name}", context)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")
    get_email_client().send_email(
        subject=subject,
        body=html_content,
        to_email=to_email,
        from_email=from_email,
        html_body=html_content,
    )


def send_html_email_to_admins(subject, template_name, context):
    """Send an HTML email to all admin users (role_id=0)."""
    from django.template.loader import render_to_string
    admins = User.objects.filter(role_id=User.ROLE_ADMIN, is_active=True, email__isnull=False).exclude(email='')
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")
    html_content = render_to_string(f"emails/{template_name}", context)
    for admin in admins:
        get_email_client().send_email(
            subject=subject,
            body=html_content,
            to_email=admin.email,
            from_email=from_email,
            html_body=html_content,
        )


from core.models import RefundLog, ApiAccessToken

def send_push_notification(user, title, description, data=None):
    if not user:
        logger.warning("[Push Notify Abort] No user object passed to send_push_notification.")
        return

    # Respect user preference: If user has muted push notifications (is_notify == 0), skip FCM dispatch
    if getattr(user, 'is_notify', 1) == 0:
        logger.info("[Push Notify Muted] User ID %s has notification toggle turned off (is_notify=0).", user.id)
        return

    logger.info("[Push Notify Request] Target User ID: %s (%s) | Title: %r", user.id, getattr(user, 'email', 'N/A'), title)

    # 1. Resolve tokens from direct attributes & ApiAccessToken table
    target_tokens = set()

    direct_device_token = getattr(user, "device_token", "") or ""
    if direct_device_token:
        target_tokens.add(direct_device_token)

    user_token = getattr(user, "token", "") or ""
    if user_token and user_token != direct_device_token:
        target_tokens.add(user_token)

    db_access_tokens = ApiAccessToken.objects.filter(created_by=user)
    db_token_count = db_access_tokens.count()
    for tok_rec in db_access_tokens:
        if tok_rec.device_token:
            target_tokens.add(tok_rec.device_token)

    logger.info("[Push Notify Token Discovery] User ID: %s | Direct Token Found: %s | ApiAccessToken Records: %d | Total Unique Tokens: %d",
                user.id, bool(direct_device_token), db_token_count, len(target_tokens))

    if not target_tokens:
        logger.warning("[Push Notify Warning] No device tokens found for User ID: %s", user.id)
        return

    # 2. Dispatch FCM to resolved tokens
    sent_count = 0
    fail_count = 0
    for tok in target_tokens:
        success = _send_fcm(tok, title, description, data=data)
        if success:
            sent_count += 1
        else:
            fail_count += 1

    logger.info("[Push Notify Summary] User ID: %s | Title: %r | Sent Succeeded: %d | Failed: %d",
                user.id, title, sent_count, fail_count)

    # Persist notification into database (tbl_notification) for audit and in-app inbox
    try:
        Notification.objects.create(
            title=title,
            description=description or title,
            to_user_id=user.id,
            created_by=user,
            state_id=1,
        )
    except Exception as e:
        logger.error("[Push Notify DB Persistence Error] Failed logging notification for User ID %s: %s", user.id, e)

class AddScheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        doctor = request.user
        availability_data = request.data.get('DoctorSlot[availability]') or request.data.get('availability', '[]')
        
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
        start_time = request.query_params.get('start_time') or request.data.get('start_time')
        end_time = request.query_params.get('end_time') or request.data.get('end_time')
        availability_data = request.data.get('DoctorSlot[availability]') or request.data.get('availability', '[]')

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


class SlotListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')
        page = request.query_params.get('page', 0)

        # PHP: Slot::findActive() — active slot templates sorted by id ASC, paginated
        queryset = Slot.objects.filter(state_id=1).order_by('id')

        page_size = 100
        start = int(page) * page_size
        end = start + page_size
        paginated = queryset[start:end]

        serializer = SlotSerializer(
            paginated, many=True,
            context={'request': request, 'start_time': start_time, 'end_time': end_time}
        )
        return Response({"list": serializer.data}, status=status.HTTP_200_OK)


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
        ).exclude(state_id=SlotBooking.STATE_CANCELED).values_list('slot_id', flat=True)

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
        slot_id = request.data.get('slot_id') or request.data.get('SlotBooking[slot_id]')
        start_time = request.data.get('start_time') or request.data.get('SlotBooking[start_time]')
        end_time = request.data.get('end_time') or request.data.get('SlotBooking[end_time]')
        doctor_id = request.data.get('doctor_id') or request.data.get('SlotBooking[doctor_id]')
        room_id = request.data.get('room_id') or request.data.get('SlotBooking[room_id]') or ""

        if not slot_id or not start_time or not end_time or not doctor_id:
            logger.warning("[BookingView Abort] Missing parameters: slot_id=%s doctor_id=%s start_time=%s end_time=%s", slot_id, doctor_id, start_time, end_time)
            return Response({"error": "Missing slot booking parameters."}, status=status.HTTP_400_BAD_REQUEST)


        # Check if already booked
        exists = SlotBooking.objects.filter(
            slot_id=slot_id,
            start_time=start_time,
            end_time=end_time,
            doctor_id=doctor_id,
            state_id__in=[SlotBooking.STATE_REQUEST, SlotBooking.STATE_ACCEPT]
        ).exists()

        if exists:
            return Response({"error": "This slot is already booked."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Check if patient has any active subscription or video credit
        has_active_subscription = SubscribedPlan.objects.filter(
            created_by=patient,
            state_id=1, # ACTIVE
            end_date__gte=timezone.now()
        ).exists()

        try:
            video_credits = int(getattr(patient, 'video_credit', 0) or 0)
        except (ValueError, TypeError):
            video_credits = 0
        
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
                if video_credits > 0:
                     patient.video_credit = video_credits - 1
                     patient.save(update_fields=['video_credit'])
                     type_id = 1 # SlotBooking::TYPE_BY_VIDEO_PLAN
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

                # Clients send room_id; fall back to the same scheme they use
                # ({patient}_{doctor}_{slot}) so the Agora channel is never empty.
                final_room_id = (room_id or "").strip()
                if not final_room_id:
                    final_room_id = f"{patient.id}_{doctor_id}_{slot_id}"

                booking = SlotBooking.objects.create(
                    slot_id=slot_id,
                    start_time=start_time,
                    end_time=end_time,
                    doctor_id=doctor_id,
                    created_by=patient,
                    state_id=SlotBooking.STATE_REQUEST,
                    type_id=type_id,
                    is_active=0, # IS_ROOM_ACTIVE_NO
                    room_id=final_room_id,
                )

                # Notifications...
                msg = f"{patient.full_name} sent you a request for a session."
                Notification.objects.create(
                    to_user_id=doctor_id,
                    created_by=patient,
                    title=msg,
                    description=msg
                )
                
                doctor_user = User.objects.filter(id=doctor_id).first()
                send_push_notification(doctor_user, "New Booking Request", msg)
                # PHP SlotBooking::sendBookingRequestmailtoDoctor
                if doctor_user:
                    session_date = (start_time.strftime("%B %d, %Y") if hasattr(start_time, "strftime") else str(start_time))
                    session_day = (start_time.strftime("%A") if hasattr(start_time, "strftime") else "")
                    session_start = (start_time.strftime("%I:%M %p") if hasattr(start_time, "strftime") else str(start_time))
                    session_end = (end_time.strftime("%I:%M %p") if hasattr(end_time, "strftime") else str(end_time))
                    send_html_email(
                        doctor_user.email,
                        "Video Session Request",
                        "newBooking.html",
                        {
                            "therapist_name": getattr(doctor_user, "full_name", ""),
                            "patient_name": getattr(patient, "full_name", ""),
                            "session_date": session_date,
                            "session_day": session_day,
                            "session_start_time": session_start,
                            "session_end_time": session_end,
                        },
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
        # Exclude pending requests from the doctor's schedule list (legacy PHP).
        qs = SlotBooking.objects.filter(doctor_id=self.request.user.id)
        if start_time and end_time:
            qs = qs.filter(start_time__gte=start_time, start_time__lte=end_time)
        return qs.exclude(state_id=SlotBooking.STATE_REQUEST).order_by('-id')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            page_num = int(request.query_params.get('page') or 1)
        except (ValueError, TypeError):
            page_num = 1
        per_page = 20
        total_count = queryset.count()
        page_count = (total_count + per_page - 1) // per_page if total_count > 0 else 0

        page = self.paginate_queryset(queryset)
        data = self.get_serializer(page if page is not None else queryset, many=True).data

        return Response({
            "list": data,
            "_meta": {
                "totalCount": total_count,
                "pageCount": page_count,
                "currentPage": page_num,
                "perPage": per_page,
            },
            "_links": {
                "self": {
                    "href": request.build_absolute_uri()
                }
            }
        }, status=status.HTTP_200_OK)


class PatientBookingListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SlotBookingSerializer

    def get_queryset(self):
        doctor_id = self.request.query_params.get('doctor_id')
        b_type = self.request.query_params.get('type') # UPCOMING/COMPLETED
        patient_id = self.request.query_params.get('patient_id')

        logger.info(
            "Fetching patient booking list: doctor_id=%s, patient_id=%s, type=%s, user_id=%s",
            doctor_id,
            patient_id,
            b_type,
            getattr(self.request.user, "id", None)
        )

        qs = SlotBooking.objects.filter(created_by_id=patient_id, doctor_id=doctor_id)
        if str(b_type) == str(SlotBooking.UPCOMING_BOOKING):
            qs = qs.filter(state_id__in=[SlotBooking.STATE_REQUEST, SlotBooking.STATE_ACCEPT])
        elif str(b_type) == str(SlotBooking.COMPLETED_BOOKING):
            qs = qs.filter(state_id__in=[SlotBooking.STATE_COMPLETED, SlotBooking.STATE_CANCELED])
        return qs.order_by('-id')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        try:
            page_num = int(request.query_params.get('page') or 1)
        except (ValueError, TypeError):
            page_num = 1
            
        per_page = 20
        total_count = queryset.count()
        page_count = (total_count + per_page - 1) // per_page if total_count > 0 else 0

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        logger.info("PatientBookingListView response: status_code=200, count=%d", total_count)

        return Response({
            "list": data,
            "_meta": {
                "totalCount": total_count,
                "pageCount": page_count,
                "currentPage": page_num,
                "perPage": per_page,
            },
            "_links": {
                "self": {
                    "href": request.build_absolute_uri()
                }
            }
        }, status=status.HTTP_200_OK)


class DoctorBookingReqView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SlotBookingSerializer

    def get_queryset(self):
        # Mark notifications read
        Notification.objects.filter(to_user_id=self.request.user.id).update(is_read=1)
        
        return SlotBooking.objects.filter(
            doctor_id=self.request.user.id,
            state_id=SlotBooking.STATE_REQUEST,
        ).order_by('id')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            page_num = int(request.query_params.get('page') or 1)
        except (ValueError, TypeError):
            page_num = 1
        per_page = 20
        total_count = queryset.count()
        page_count = (total_count + per_page - 1) // per_page if total_count > 0 else 0

        page = self.paginate_queryset(queryset)
        data = self.get_serializer(page if page is not None else queryset, many=True).data

        return Response({
            "list": data,
            "_meta": {
                "totalCount": total_count,
                "pageCount": page_count,
                "currentPage": page_num,
                "perPage": per_page,
            },
            "_links": {
                "self": {
                    "href": request.build_absolute_uri()
                }
            }
        }, status=status.HTTP_200_OK)


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

    def _handle_accept(self, request, booking_id=None):
        booking_id = booking_id or request.query_params.get("booking_id") or request.data.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = SlotBooking.objects.get(id=booking_id)
            booking.state_id = SlotBooking.STATE_ACCEPT
            booking.save(update_fields=['state_id'])

            # Send Notification & Push (matching PHP SlotController 608-615)
            user = request.user
            doc_name = getattr(user, "first_name", "") or getattr(user, "full_name", "") or "Doctor"
            msg = f"{doc_name} confirmed your request for"
            
            Notification.objects.create(
                description=msg,
                title=msg,
                to_user_id=booking.created_by_id,
                created_by=user,
                model_id=booking.id,
                model_type='SlotBooking'
            )
            send_push_notification(booking.created_by, msg, "")
            # PHP SlotBooking::sendBookingConfirmationMail
            doctor_user = user
            if booking.created_by and doctor_user:
                session_date = (booking.start_time.strftime("%B %d, %Y") if hasattr(booking.start_time, "strftime") else str(booking.start_time))
                session_start = (booking.start_time.strftime("%I:%M %p") if hasattr(booking.start_time, "strftime") else str(booking.start_time))
                send_html_email(
                    booking.created_by.email,
                    "Video Session Confirmed",
                    "confirmBooking.html",
                    {
                        "therapist_name": getattr(doctor_user, "full_name", ""),
                        "session_date": session_date,
                        "session_start_time": session_start,
                    },
                )
            return Response({"message": "Booking accepted successfully"}, status=status.HTTP_200_OK)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No Booking found"}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, booking_id=None):
        return self._handle_accept(request, booking_id)

    def post(self, request, booking_id=None):
        return self._handle_accept(request, booking_id)


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
            booking.state_id = SlotBooking.STATE_ACCEPT
            booking.doctor_reschedule = 1 # YES
            
            booking.save()
            
            msg = f"{doctor.full_name} has rescheduled your video session."
            Notification.objects.create(
                to_user_id=booking.created_by_id,
                created_by=doctor,
                title=msg,
                description=msg,
                model_id=booking.id,
            )
            send_push_notification(booking.created_by, "Session rescheduled", msg)
            # PHP SlotBooking::sendBookingRescheduleMailToUser + sendBookingRescheduleMailToDoctor
            patient_user = booking.created_by
            if patient_user and doctor:
                fmt = lambda dt: dt.strftime("%B %d, %Y") if hasattr(dt, "strftime") else str(dt)
                fmt_day = lambda dt: dt.strftime("%A") if hasattr(dt, "strftime") else ""
                fmt_time = lambda dt: dt.strftime("%I:%M %p") if hasattr(dt, "strftime") else str(dt)
                old_start = booking.old_start_time or booking.start_time
                old_end = booking.old_end_time or booking.end_time
                # Email to patient
                send_html_email(
                    patient_user.email,
                    "Video Session Rescheduled",
                    "reschedulePatient.html",
                    {
                        "therapist_name": getattr(doctor, "full_name", ""),
                        "patient_name": getattr(patient_user, "full_name", ""),
                        "old_session_date": fmt(old_start),
                        "old_session_day": fmt_day(old_start),
                        "old_session_start_time": fmt_time(old_start),
                        "old_session_end_time": fmt_time(old_end),
                        "session_date": fmt(booking.start_time),
                        "session_day": fmt_day(booking.start_time),
                        "session_start_time": fmt_time(booking.start_time),
                        "session_end_time": fmt_time(booking.end_time),
                    },
                )
                # Email to doctor
                send_html_email(
                    doctor.email,
                    "Video Session Rescheduled",
                    "rescheduleDoctor.html",
                    {
                        "therapist_name": getattr(doctor, "full_name", ""),
                        "patient_name": getattr(patient_user, "full_name", ""),
                        "old_session_date": fmt(old_start),
                        "old_session_day": fmt_day(old_start),
                        "old_session_start_time": fmt_time(old_start),
                        "old_session_end_time": fmt_time(old_end),
                        "session_date": fmt(booking.start_time),
                        "session_day": fmt_day(booking.start_time),
                        "session_start_time": fmt_time(booking.start_time),
                        "session_end_time": fmt_time(booking.end_time),
                    },
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
                if booking.state_id == SlotBooking.STATE_CANCELED:
                     return Response({"error": "Booking is already canceled."}, status=status.HTTP_400_BAD_REQUEST)
                
                booking.state_id = SlotBooking.STATE_CANCELED
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
                    description=msg,
                    model_id=booking.id,
                )
                send_push_notification(patient, "Session cancelled", msg)
                # PHP SlotBooking::sendBookingCancelMailToUser
                if patient:
                    fmt = lambda dt: dt.strftime("%B %d, %Y") if hasattr(dt, "strftime") else str(dt)
                    fmt_day = lambda dt: dt.strftime("%A") if hasattr(dt, "strftime") else ""
                    fmt_time = lambda dt: dt.strftime("%I:%M %p") if hasattr(dt, "strftime") else str(dt)
                    send_html_email(
                        patient.email,
                        "Video Session Cancelled",
                        "bookingCancel.html",
                        {
                            "first_name": getattr(patient, "full_name", "") or getattr(patient, "first_name", ""),
                            "therapist_name": getattr(doctor, "full_name", ""),
                            "session_date": fmt(booking.start_time),
                            "session_day": fmt_day(booking.start_time),
                            "session_start_time": fmt_time(booking.start_time),
                            "session_end_time": fmt_time(booking.end_time),
                        },
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
        booking_id = booking_id or request.query_params.get("booking_id") or request.data.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = SlotBooking.objects.get(id=booking_id, created_by_id=user.id)
        except SlotBooking.DoesNotExist:
            return Response({"error": "No booking found."}, status=status.HTTP_400_BAD_REQUEST)

        if booking.patient_reschedule == 1:
            return Response({"error": "You have already rescheduled the booking once."}, status=status.HTTP_400_BAD_REQUEST)

        start_time = request.data.get("start_time") or request.data.get("SlotBooking[start_time]")
        end_time = request.data.get("end_time") or request.data.get("SlotBooking[end_time]")
        slot_id = request.data.get("slot_id") or request.data.get("SlotBooking[slot_id]")

        if not start_time or not end_time:
            return Response({"error": "Data not posted."}, status=status.HTTP_400_BAD_REQUEST)

        booking.old_start_time = booking.start_time
        booking.old_end_time = booking.end_time
        booking.start_time = start_time
        booking.end_time = end_time
        if slot_id:
            booking.slot_id = slot_id
        booking.state_id = SlotBooking.STATE_ACCEPT
        booking.patient_reschedule = 1  # YES
        booking.save()


        patient_name = getattr(user, "full_name", "") or getattr(user, "first_name", "") or "Patient"
        message = f"{patient_name} has rescheduled your video session to"
        Notification.objects.create(
            to_user_id=booking.doctor_id,
            created_by=user,
            title=message,
            description=message,
            model_id=booking.id,
            model_type="SlotBooking",
        )
        send_push_notification(
            User.objects.filter(id=booking.doctor_id).first(),
            "Session rescheduled", message,
        )
        return Response(
            {
                "message": "Booking rescheduled successfully.",
                "details": SlotBookingSerializer(booking).data
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
