import json
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from availability.models import DoctorSlot, SlotBooking, Notification
from availability.views import send_push_notification
from calls.views import IsDoctor
from plans.models import WebhookLog

from .constants import (
    ORIGINAL_PRICE, DISCOUNTED_PRICE, DURATION_MINUTES,
    REFUND_WINDOW_DAYS, HOLD_TTL_MINUTES,
)
from .models import DiscoveryBooking
from .serializers import DiscoveryBookingSerializer
from .services import razorpay_client

logger = logging.getLogger(__name__)


def _eligible_doctor_ids():
    """Same directory filter as core.views.PublicTherapistListView, plus is_available."""
    return list(
        User.objects.filter(
            role_id=User.ROLE_DOCTER,
            state_id=User.STATE_ACTIVE,
            is_active=True,
            is_hidden_from_directory=False,
            is_available=True,
        ).values_list('id', flat=True)
    )


def _active_discovery_bookings_qs(doctor_ids, window_start, window_end):
    hold_cutoff = timezone.now() - timedelta(minutes=HOLD_TTL_MINUTES)
    return (
        DiscoveryBooking.objects.filter(
            assigned_doctor_id__in=doctor_ids,
            start_time__lt=window_end,
            end_time__gt=window_start,
        ).exclude(state_id=DiscoveryBooking.STATE_CANCELED)
        # A stale, still-unpaid hold no longer blocks the slot.
        .exclude(state_id=DiscoveryBooking.STATE_CREATED, created_on__lt=hold_cutoff)
    )


def _busy_windows_by_doctor(doctor_ids, window_start, window_end):
    """{doctor_id: [(start, end), ...]} of everything already occupying that
    doctor's time in the window, across both normal SlotBookings and Discover
    bookings."""
    windows = {}
    slot_bookings = SlotBooking.objects.filter(
        doctor_id__in=doctor_ids, start_time__lt=window_end, end_time__gt=window_start,
    ).exclude(state_id=SlotBooking.STATE_CANCELED).values_list('doctor_id', 'start_time', 'end_time')
    discovery_bookings = _active_discovery_bookings_qs(doctor_ids, window_start, window_end).values_list(
        'assigned_doctor_id', 'start_time', 'end_time'
    )
    for doc_id, start, end in list(slot_bookings) + list(discovery_bookings):
        windows.setdefault(doc_id, []).append((start, end))
    return windows


def _overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


class AvailableSlotsView(APIView):
    """
    GET /api/discover/available-slots/?date=YYYY-MM-DD

    Default slot-selection logic (flagged with product as TBD): the patient
    picks a *time*, not a therapist. A time is "open" if at least one
    eligible therapist has published availability (DoctorSlot) starting then
    with no conflicting booking in the following 15 minutes.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        date_str = request.query_params.get('date')
        parsed_date = parse_date(date_str) if date_str else None
        if not parsed_date:
            return Response({"error": "date (YYYY-MM-DD) is required."}, status=status.HTTP_400_BAD_REQUEST)

        day_start = timezone.make_aware(datetime.combine(parsed_date, datetime.min.time()))
        day_end = day_start + timedelta(days=1)

        eligible_ids = _eligible_doctor_ids()
        if not eligible_ids:
            return Response({"list": []}, status=status.HTTP_200_OK)

        doctor_slots = list(
            DoctorSlot.objects.filter(
                created_by_id__in=eligible_ids,
                start_time__gte=day_start,
                start_time__lt=day_end,
                state_id=1,
            ).values('created_by_id', 'start_time')
        )
        if not doctor_slots:
            return Response({"list": []}, status=status.HTTP_200_OK)

        busy_by_doctor = _busy_windows_by_doctor(
            eligible_ids, day_start - timedelta(hours=2), day_end + timedelta(hours=2)
        )

        free_times = set()
        for row in doctor_slots:
            doc_id = row['created_by_id']
            start = row['start_time']
            end = start + timedelta(minutes=DURATION_MINUTES)
            windows = busy_by_doctor.get(doc_id, [])
            if not any(_overlaps(start, end, w_start, w_end) for w_start, w_end in windows):
                free_times.add(start)

        return Response(
            {
                "list": [
                    {"start_time": t, "end_time": t + timedelta(minutes=DURATION_MINUTES)}
                    for t in sorted(free_times)
                ]
            },
            status=status.HTTP_200_OK,
        )


class CreateOrderView(APIView):
    """POST /api/discover/create-order/  {start_time: ISO datetime}"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        patient = request.user
        start_time_str = request.data.get('start_time')
        start_time = parse_datetime(start_time_str) if start_time_str else None
        if not start_time:
            return Response({"error": "start_time (ISO datetime) is required."}, status=status.HTTP_400_BAD_REQUEST)
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        end_time = start_time + timedelta(minutes=DURATION_MINUTES)

        # One-time offer, lifetime per patient.
        if DiscoveryBooking.objects.filter(created_by=patient).exclude(state_id=DiscoveryBooking.STATE_CANCELED).exists():
            return Response(
                {"error": "You've already used your one-time Discover offer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        eligible_ids = _eligible_doctor_ids()
        doctors_with_slot = set(
            DoctorSlot.objects.filter(
                created_by_id__in=eligible_ids, start_time=start_time, state_id=1,
            ).values_list('created_by_id', flat=True)
        )
        if not doctors_with_slot:
            return Response({"error": "This slot is no longer available."}, status=status.HTTP_400_BAD_REQUEST)

        busy_by_doctor = _busy_windows_by_doctor(
            list(doctors_with_slot), start_time - timedelta(hours=2), end_time + timedelta(hours=2)
        )
        available_doctor_ids = [
            d for d in doctors_with_slot
            if not any(_overlaps(start_time, end_time, w_start, w_end) for w_start, w_end in busy_by_doctor.get(d, []))
        ]
        if not available_doctor_ids:
            return Response({"error": "This slot is no longer available."}, status=status.HTTP_400_BAD_REQUEST)

        # Load-balance: assign whichever eligible therapist has taken the fewest Discover calls this week.
        week_ago = timezone.now() - timedelta(days=7)
        load_counts = dict(
            DiscoveryBooking.objects.filter(assigned_doctor_id__in=available_doctor_ids, created_on__gte=week_ago)
            .exclude(state_id=DiscoveryBooking.STATE_CANCELED)
            .values('assigned_doctor_id')
            .annotate(cnt=Count('id'))
            .values_list('assigned_doctor_id', 'cnt')
        )
        assigned_doctor_id = min(available_doctor_ids, key=lambda d: load_counts.get(d, 0))

        if not getattr(settings, "RAZORPAY_KEY_ID", "") or not getattr(settings, "RAZORPAY_KEY_SECRET", ""):
            return Response({"error": "Razorpay credentials are not configured."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = razorpay_client.order.create({
                "amount": DISCOUNTED_PRICE * 100,
                "currency": "INR",
                "payment_capture": 1,
            })
        except Exception:
            logger.exception("[Discover] razorpay order creation failed user_id=%s", patient.id)
            return Response({"error": "Unable to create payment order right now."}, status=status.HTTP_400_BAD_REQUEST)

        booking = DiscoveryBooking.objects.create(
            assigned_doctor_id=assigned_doctor_id,
            date=start_time.date(),
            start_time=start_time,
            end_time=end_time,
            original_price=ORIGINAL_PRICE,
            amount=DISCOUNTED_PRICE,
            razorpay_order_id=order.get("id"),
            state_id=DiscoveryBooking.STATE_CREATED,
            created_by=patient,
        )

        logger.info(
            "[Discover] order created booking_id=%s user_id=%s doctor_id=%s start_time=%s",
            booking.id, patient.id, assigned_doctor_id, start_time,
        )
        return Response({
            "message": "Discover order created.",
            "booking_id": booking.id,
            "razorpay_order_id": order.get("id"),
            "razorpay_key_id": getattr(settings, "RAZORPAY_KEY_ID", ""),
            "amount": DISCOUNTED_PRICE,
            "currency": "INR",
        }, status=status.HTTP_200_OK)


class VerifyPaymentView(APIView):
    """POST /api/discover/verify-payment/ {booking_id, razorpay_payment_id, razorpay_signature}"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        patient = request.user
        booking_id = request.data.get('booking_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')

        if not booking_id or not razorpay_payment_id or not razorpay_signature:
            return Response(
                {"error": "booking_id, razorpay_payment_id and razorpay_signature are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            booking = DiscoveryBooking.objects.get(id=booking_id, created_by=patient)
        except DiscoveryBooking.DoesNotExist:
            return Response({"error": "Discover booking not found."}, status=status.HTTP_400_BAD_REQUEST)

        if booking.state_id != DiscoveryBooking.STATE_CREATED:
            return Response({"error": "This booking has already been processed."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': booking.razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            })
        except Exception as exc:
            logger.warning("[Discover] signature verification failed booking_id=%s: %s", booking.id, exc)
            return Response({"error": "Payment verification failed."}, status=status.HTTP_400_BAD_REQUEST)

        slot_booking = None
        with transaction.atomic():
            booking = DiscoveryBooking.objects.select_for_update().get(id=booking.id)
            if booking.state_id != DiscoveryBooking.STATE_CREATED:
                return Response({"error": "This booking has already been processed."}, status=status.HTTP_400_BAD_REQUEST)

            # Final race check: the assigned therapist may have been booked elsewhere
            # while checkout was in progress. If so, refund immediately and bail out.
            busy = _busy_windows_by_doctor(
                [booking.assigned_doctor_id],
                booking.start_time - timedelta(hours=2),
                booking.end_time + timedelta(hours=2),
            ).get(booking.assigned_doctor_id, [])
            if any(_overlaps(booking.start_time, booking.end_time, w_start, w_end) for w_start, w_end in busy):
                booking.state_id = DiscoveryBooking.STATE_CANCELED
                booking.cancel_reason = "Slot was taken before payment could be confirmed."
                booking.razorpay_payment_id = razorpay_payment_id
                booking.razorpay_signature = razorpay_signature
                booking.save(update_fields=["state_id", "cancel_reason", "razorpay_payment_id", "razorpay_signature"])
                self._refund_immediately(booking, razorpay_payment_id)
                return Response(
                    {"error": "This slot was just taken. You've been refunded — please pick another slot."},
                    status=status.HTTP_409_CONFLICT,
                )

            # Same lifecycle as a normal booking: request sent to the doctor,
            # who must accept it (via the existing AcceptBookingView) before
            # the call is actually scheduled.
            room_id = f"discover_{patient.id}_{booking.assigned_doctor_id}_{booking.id}"
            slot_booking = SlotBooking.objects.create(
                slot_id=0,
                start_time=booking.start_time,
                end_time=booking.end_time,
                doctor_id=booking.assigned_doctor_id,
                date=booking.date,
                room_id=room_id,
                state_id=SlotBooking.STATE_REQUEST,
                type_id=SlotBooking.TYPE_DISCOVERY,
                is_active=0,
                created_by=patient,
            )

            booking.slot_booking_id = slot_booking.id
            booking.razorpay_payment_id = razorpay_payment_id
            booking.razorpay_signature = razorpay_signature
            booking.state_id = DiscoveryBooking.STATE_PAID
            booking.refund_eligible_until = timezone.now() + timedelta(days=REFUND_WINDOW_DAYS)
            booking.save(update_fields=[
                "slot_booking_id", "razorpay_payment_id", "razorpay_signature",
                "state_id", "refund_eligible_until",
            ])

        doctor = User.objects.filter(id=booking.assigned_doctor_id).first()
        if doctor:
            msg = f"{patient.full_name or 'A patient'} sent you a Discover session request."
            Notification.objects.create(
                to_user_id=doctor.id, created_by=patient, title=msg, description=msg,
                model_id=slot_booking.id, model_type='SlotBooking',
            )
            send_push_notification(doctor, "New Discover Request", msg)

        logger.info("[Discover] payment verified booking_id=%s user_id=%s slot_booking_id=%s", booking.id, patient.id, slot_booking.id)
        return Response({
            "message": "Payment confirmed. Your Discover request has been sent to the therapist.",
            "booking": DiscoveryBookingSerializer(booking).data,
            "slot_booking_id": slot_booking.id,
            "room_id": room_id,
        }, status=status.HTTP_200_OK)

    def _refund_immediately(self, booking, razorpay_payment_id):
        try:
            refund = razorpay_client.payment.refund(razorpay_payment_id, {"amount": int(booking.amount * 100)})
            booking.refund_id = refund.get("id", "") if isinstance(refund, dict) else ""
            booking.refunded_amount = booking.amount
            booking.refunded_at = timezone.now()
            booking.save(update_fields=["refund_id", "refunded_amount", "refunded_at"])
        except Exception:
            logger.exception("[Discover] immediate refund failed booking_id=%s", booking.id)


class PatientCancelDiscoveryView(APIView):
    """POST /api/discover/cancel/ {booking_id} — non-refundable."""
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id=None):
        patient = request.user
        booking_id = booking_id or request.data.get('booking_id')
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = DiscoveryBooking.objects.get(id=booking_id, created_by=patient)
        except DiscoveryBooking.DoesNotExist:
            return Response({"error": "Discover booking not found."}, status=status.HTTP_400_BAD_REQUEST)

        if booking.state_id not in (DiscoveryBooking.STATE_CREATED, DiscoveryBooking.STATE_PAID):
            return Response({"error": "This booking can no longer be canceled."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            booking.state_id = DiscoveryBooking.STATE_CANCELED
            booking.cancel_reason = "Canceled by patient"
            booking.save(update_fields=["state_id", "cancel_reason"])

            if booking.slot_booking_id:
                SlotBooking.objects.filter(id=booking.slot_booking_id).update(
                    state_id=SlotBooking.STATE_CANCELED,
                    cancel_reason="Discover booking canceled by patient",
                )

        logger.info("[Discover] patient canceled booking_id=%s user_id=%s", booking.id, patient.id)
        return Response(
            {"message": "Discover booking canceled. This payment is non-refundable."},
            status=status.HTTP_200_OK,
        )


class TherapistCancelDiscoveryView(APIView):
    """POST /api/discover/therapist-cancel/ {booking_id} — auto-refunds the patient."""
    permission_classes = (IsAuthenticated, IsDoctor)

    def post(self, request, booking_id=None):
        doctor = request.user
        booking_id = booking_id or request.data.get('booking_id')
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = DiscoveryBooking.objects.get(id=booking_id, assigned_doctor=doctor)
        except DiscoveryBooking.DoesNotExist:
            return Response({"error": "Discover booking not found."}, status=status.HTTP_400_BAD_REQUEST)

        if booking.state_id != DiscoveryBooking.STATE_PAID:
            return Response({"error": "Only a paid booking can be canceled this way."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            booking = DiscoveryBooking.objects.select_for_update().get(id=booking.id)
            booking.cancel_reason = f"Therapist {doctor.full_name} canceled the Discover session"

            try:
                refund = razorpay_client.payment.refund(
                    booking.razorpay_payment_id, {"amount": int(booking.amount * 100)}
                )
                booking.state_id = DiscoveryBooking.STATE_REFUNDED
                booking.refund_id = refund.get("id", "") if isinstance(refund, dict) else ""
                booking.refunded_amount = booking.amount
                booking.refunded_at = timezone.now()
                booking.save(update_fields=[
                    "state_id", "cancel_reason", "refund_id", "refunded_amount", "refunded_at",
                ])
            except Exception:
                logger.exception("[Discover] therapist-cancel refund failed booking_id=%s", booking.id)
                booking.state_id = DiscoveryBooking.STATE_REFUND_FAILED
                booking.save(update_fields=["state_id", "cancel_reason"])

            if booking.slot_booking_id:
                SlotBooking.objects.filter(id=booking.slot_booking_id).update(
                    state_id=SlotBooking.STATE_CANCELED,
                    is_refunded=1,
                    cancel_reason="Therapist canceled the Discover session",
                )

        patient = booking.created_by
        msg = f"{doctor.full_name} has canceled your Discover session. Your payment has been refunded."
        Notification.objects.create(
            to_user_id=patient.id, created_by=doctor, title=msg, description=msg, model_id=booking.id,
        )
        send_push_notification(patient, "Discover session canceled", msg)

        logger.info("[Discover] therapist canceled booking_id=%s doctor_id=%s state=%s", booking.id, doctor.id, booking.state_id)
        return Response(
            {"message": "Discover booking canceled.", "booking": DiscoveryBookingSerializer(booking).data},
            status=status.HTTP_200_OK,
        )


class MarkNoShowView(APIView):
    """
    POST /api/discover/mark-no-show/ {booking_id}

    A no-show still counts as a completed call — no refund — but is flagged
    (is_no_show) so support/ops can tell it apart from a call that actually
    happened. The booking can still be rescheduled afterwards via the
    existing DoctorRescheduleView/PatientRescheduleView, same as any booking.
    """
    permission_classes = (IsAuthenticated, IsDoctor)

    def post(self, request, booking_id=None):
        doctor = request.user
        booking_id = booking_id or request.data.get('booking_id')
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            booking = DiscoveryBooking.objects.get(id=booking_id, assigned_doctor=doctor)
        except DiscoveryBooking.DoesNotExist:
            return Response({"error": "Discover booking not found."}, status=status.HTTP_400_BAD_REQUEST)

        if not booking.slot_booking_id:
            return Response({"error": "This booking hasn't been scheduled yet."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            booking.is_no_show = True
            booking.state_id = DiscoveryBooking.STATE_COMPLETED
            booking.save(update_fields=["is_no_show", "state_id"])

            SlotBooking.objects.filter(id=booking.slot_booking_id).update(
                state_id=SlotBooking.STATE_COMPLETED,
                is_active=0,
                complete_reason="No show",
            )

        logger.info("[Discover] no-show marked booking_id=%s doctor_id=%s", booking.id, doctor.id)
        return Response(
            {"message": "Marked as a no-show. No refund is issued; the call can still be rescheduled.",
             "booking": DiscoveryBookingSerializer(booking).data},
            status=status.HTTP_200_OK,
        )


class DiscoveryWebhookView(APIView):
    """
    POST /api/discover/razorpay-webhook/

    Reconciliation backstop only — logs Discover-relevant Razorpay events
    (payment.captured, refund.processed, etc.) to the existing WebhookLog
    table. verify-payment/ remains the sole path that activates a booking.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        payload_bytes = request.body
        sig_header = request.META.get("HTTP_X_RAZORPAY_SIGNATURE", "")
        secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")

        if secret:
            if not sig_header:
                return Response({"error": "Signature header missing."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                razorpay_client.utility.verify_webhook_signature(
                    payload_bytes.decode("utf-8"), sig_header, secret
                )
            except Exception as exc:
                logger.warning("[Discover] webhook signature verification failed: %s", exc)
                return Response({"error": "Invalid webhook signature."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event_json = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return Response({"error": "Invalid JSON payload."}, status=status.HTTP_400_BAD_REQUEST)

        event_name = event_json.get("event", "")
        payload = event_json.get("payload", {})
        order_id = (
            payload.get("order", {}).get("entity", {}).get("id")
            or payload.get("payment", {}).get("entity", {}).get("order_id")
            or ""
        )

        try:
            WebhookLog.objects.create(
                event=event_name or "unknown",
                subscription_id=f"discover:{order_id}" if order_id else "discover:unknown",
                data=payload_bytes.decode("utf-8", errors="ignore"),
            )
        except Exception as exc:
            logger.warning("[Discover] failed to save WebhookLog entry: %s", exc)

        logger.info("[Discover] webhook received event=%s order_id=%s", event_name, order_id)
        return Response({"status": "received"}, status=status.HTTP_200_OK)
