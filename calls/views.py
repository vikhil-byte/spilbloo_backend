from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from .models import Call
from .serializers import CallSerializer
from availability.views import send_push_notification
from availability.models import SlotBooking, Notification
from availability.serializers import SlotBookingSerializer
from accounts.models import User
import logging
import time

logger = logging.getLogger(__name__)

ROLE_PUBLISHER = 1


class IsDoctor(BasePermission):
    message = "Only therapists can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and int(getattr(request.user, "role_id", 0)) == User.ROLE_DOCTER
        )


def _extract_param(data, query_params, *keys):
    """
    Helper to extract parameter values from request data or query params.
    Handles standard keys ('booking_id'), nested dicts, PHP form keys ('Call[booking_id]'),
    malformed bracket keys ('Call[booking_id]]'), and Django QueryDicts/MultiValueDicts.
    """
    def _unwrap(v):
        if isinstance(v, (list, tuple)) and len(v) > 0:
            return v[0]
        return v

    for key in keys:
        target_sub = f"[{key}]"

        # 1. Search request.data / body
        if data:
            # Direct key lookup
            val = data.get(key)
            if val is not None and val != "" and val != []:
                return _unwrap(val)

            # Nested Call dict
            if isinstance(data, dict) and "Call" in data and isinstance(data["Call"], dict):
                val = data["Call"].get(key)
                if val is not None and val != "" and val != []:
                    return _unwrap(val)

            # Iterate all keys in data (handles QueryDict & dict)
            items = data.items() if hasattr(data, "items") else []
            for d_key, d_val in items:
                d_val = _unwrap(d_val)
                if d_val is not None and d_val != "":
                    cleaned_key = d_key.replace("]", "").replace("[", "")
                    if target_sub in d_key or cleaned_key.endswith(key):
                        return d_val

        # 2. Search request.query_params
        if query_params:
            val = query_params.get(key)
            if val is not None and val != "" and val != []:
                return _unwrap(val)

            items = query_params.items() if hasattr(query_params, "items") else []
            for q_key, q_val in items:
                q_val = _unwrap(q_val)
                if q_val is not None and q_val != "":
                    cleaned_key = q_key.replace("]", "").replace("[", "")
                    if target_sub in q_key or cleaned_key.endswith(key):
                        return q_val

    return None


def _parse_duration_to_seconds(val):
    """
    Safely parses duration input into integer seconds.
    Handles int/float numbers, numeric strings ('45'), and time strings ('00:45', '01:15:30').
    """
    if val is None or val == "":
        return 0
    if isinstance(val, (int, float)):
        return int(val)

    val_str = str(val).strip()
    if val_str.isdigit():
        return int(val_str)

    if ":" in val_str:
        try:
            parts = [int(p) for p in val_str.split(":")]
            if len(parts) == 2:  # MM:SS
                return parts[0] * 60 + parts[1]
            elif len(parts) == 3:  # HH:MM:SS
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
        except ValueError:
            pass

    try:
        return int(float(val_str))
    except (ValueError, TypeError):
        return 0


class JoinView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request):
        user = request.user
        data = request.data or {}
        query_params = request.query_params or {}

        booking_id = _extract_param(data, query_params, 'booking_id')
        session_id = _extract_param(data, query_params, 'session_id', 'room_id')

        logger.info(
            "JoinView request received: user_id=%s data=%s query_params=%s parsed_booking_id=%s parsed_session_id=%s",
            getattr(user, "id", None), data, dict(query_params), booking_id, session_id
        )

        if not session_id and not booking_id:
            logger.warning(
                "JoinView Bad Request: Missing both booking_id and session_id (booking_id=%s, session_id=%s)",
                booking_id,
                session_id,
            )
            return Response({"error": "Data not posted."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = None
            if booking_id:
                booking = SlotBooking.objects.filter(id=booking_id).first()

            # Fallback: if booking_id was missing or not found, try lookup via session_id (room_id)
            if not booking and session_id:
                booking = SlotBooking.objects.filter(room_id=session_id).order_by('-id').first()
                if booking:
                    booking_id = booking.id
                    logger.info("JoinView resolved booking_id=%s via session_id=%s", booking_id, session_id)

            if not booking:
                logger.warning(
                    "JoinView Bad Request: Booking id=%s session_id=%s does not exist",
                    booking_id,
                    session_id,
                )
                return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)

            if session_id and str(booking.room_id) != str(session_id):
                logger.warning(
                    "JoinView Bad Request: Room/Session mismatch for booking_id=%s (DB room_id=%s vs received session_id=%s)",
                    booking_id, booking.room_id, session_id
                )
                return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)

            # Ensure session_id is populated from booking if missing
            if not session_id:
                session_id = booking.room_id

            # Identify receiver
            if user.role_id == User.ROLE_DOCTER:
                receiver_user_id = booking.created_by_id
                name = user.full_name
            else:
                receiver_user_id = booking.doctor_id
                name = user.full_name

            receiver_user = User.objects.get(id=receiver_user_id)

            call = Call.objects.create(
                state_id=1,  # JOIN
                booking_id=booking.id,
                session_id=session_id,
                user=receiver_user,
                start_time=timezone.now(),
                created_by=user
            )

            # Mirror PHP behavior: send wait notification only if receiver hasn't joined yet.
            other_user_joined = Call.objects.filter(
                booking_id=booking.id,
                session_id=session_id,
                state_id=1,
                created_by_id=receiver_user.id,
            ).exists()
            if not other_user_joined:
                message = f"{name} is waiting for you in the room!"
                Notification.objects.create(
                    to_user_id=receiver_user.id,
                    created_by=user,
                    title=message,
                    model_id=call.id,
                    model_type='Call'
                )
                send_push_notification(
                    receiver_user, "Incoming Call", message,
                    data={"controller": "call", "action": "join", "message": message,
                          "user_id": str(user.id), "detail": CallSerializer(call).data},
                )

            logger.info("JoinView success: user_id=%s booking_id=%s call_id=%s", user.id, booking.id, call.id)
            return Response({
                "message": "Joined Successfully.",
                "detail": CallSerializer(call).data
            }, status=status.HTTP_200_OK)

        except SlotBooking.DoesNotExist:
            logger.warning("JoinView Bad Request: SlotBooking DoesNotExist for booking_id=%s", booking_id)
            return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.warning("JoinView Bad Request: Receiver User DoesNotExist")
            return Response({"error": "Reciever user not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("join-call failed user_id=%s booking_id=%s", getattr(user, "id", None), booking_id)
            return Response({"error": "Unable to join call right now."}, status=status.HTTP_400_BAD_REQUEST)


class LeaveView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request):
        user = request.user
        data = request.data or {}
        query_params = request.query_params or {}

        booking_id = _extract_param(data, query_params, 'booking_id')
        session_id = _extract_param(data, query_params, 'session_id', 'room_id')
        raw_duration = _extract_param(data, query_params, 'duration') or 0
        raw_duration_millisec = _extract_param(data, query_params, 'duration_millisec') or 0

        duration = _parse_duration_to_seconds(raw_duration)
        duration_millisec = _parse_duration_to_seconds(raw_duration_millisec)
        if duration_millisec == 0 and duration > 0:
            duration_millisec = duration * 1000

        logger.info(
            "LeaveView request received: user_id=%s data=%s query_params=%s parsed_booking_id=%s parsed_session_id=%s raw_duration=%s -> parsed_duration=%s raw_dur_ms=%s -> parsed_dur_ms=%s",
            getattr(user, "id", None), data, dict(query_params), booking_id, session_id, raw_duration, duration, raw_duration_millisec, duration_millisec
        )

        try:
            booking = None
            if booking_id:
                booking = SlotBooking.objects.filter(id=booking_id).first()
            if not booking and session_id:
                booking = SlotBooking.objects.filter(room_id=session_id).order_by('-id').first()
                if booking:
                    booking_id = booking.id

            if not booking:
                logger.warning(
                    "LeaveView Bad Request: Booking id=%s session_id=%s does not exist",
                    booking_id,
                    session_id,
                )
                return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)

            # PHP compound check: booking_id AND room_id must match
            if session_id and booking.room_id and str(booking.room_id) != str(session_id):
                logger.warning(
                    "LeaveView Bad Request: Room/Session mismatch for booking_id=%s (DB room_id=%s vs received session_id=%s)",
                    booking_id, booking.room_id, session_id
                )
                return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)

            call = Call.objects.create(
                state_id=2,  # LEFT
                booking_id=booking.id,
                session_id=session_id or booking.room_id,
                user=user,  # PHP sets user_id to current user via beforeValidate
                end_time=timezone.now(),
                duration=duration,
                duration_millisec=duration_millisec,
                created_by=user
            )

            # PHP stores call_duration as HH:MM:SS string (varchar) — convert
            # integer seconds back to that format for SlotBooking CharField.
            _dur = int(duration or 0)
            _hours, _remainder = divmod(_dur, 3600)
            _mins, _secs = divmod(_remainder, 60)
            booking.call_duration = f"{_hours:02d}:{_mins:02d}:{_secs:02d}"
            booking.duration_millisec = str(duration_millisec)
            booking.is_call_end = 1  # YES
            booking.save(update_fields=['call_duration', 'duration_millisec', 'is_call_end'])

            logger.info(
                "LeaveView success: user_id=%s booking_id=%s call_id=%s duration=%s",
                user.id,
                booking.id,
                call.id,
                duration,
            )
            return Response({
                "message": "Room leave Successfully.",
                "detail": CallSerializer(call).data
            }, status=status.HTTP_200_OK)

        except SlotBooking.DoesNotExist:
            logger.warning("LeaveView Bad Request: SlotBooking DoesNotExist for booking_id=%s", booking_id)
            return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception(
                "leave-call failed user_id=%s booking_id=%s raw_duration=%s",
                getattr(user, "id", None),
                booking_id,
                raw_duration,
            )
            return Response({"error": "Unable to leave call right now."}, status=status.HTTP_400_BAD_REQUEST)


class CompleteBookingView(APIView):
    permission_classes = (IsAuthenticated, IsDoctor)

    def get(self, request, booking_id=None):
        return self.post(request, booking_id=booking_id)

    def post(self, request, booking_id=None):
        user = request.user
        data = request.data or {}
        query_params = request.query_params or {}

        booking_id = booking_id or _extract_param(data, query_params, 'booking_id')
        session_id = _extract_param(data, query_params, 'session_id', 'room_id')
        raw_duration = _extract_param(data, query_params, 'duration') or 0
        raw_duration_millisec = _extract_param(data, query_params, 'duration_millisec') or 0

        duration = _parse_duration_to_seconds(raw_duration)
        duration_millisec = _parse_duration_to_seconds(raw_duration_millisec)
        if duration_millisec == 0 and duration > 0:
            duration_millisec = duration * 1000

        logger.info(
            "CompleteBookingView request received: user_id=%s data=%s query_params=%s parsed_booking_id=%s parsed_session_id=%s parsed_duration=%s",
            getattr(user, "id", None), data, dict(query_params), booking_id, session_id, duration
        )

        try:
            booking = None
            if booking_id:
                booking = SlotBooking.objects.filter(id=booking_id).first()
            if not booking and session_id:
                booking = SlotBooking.objects.filter(room_id=session_id).order_by('-id').first()

            if not booking:
                logger.warning(
                    "CompleteBookingView Bad Request: Booking id=%s session_id=%s does not exist",
                    booking_id,
                    session_id,
                )
                return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)

            call = Call.objects.create(
                state_id=3,  # COMPLETED
                booking_id=booking.id,
                session_id=session_id or booking.room_id,
                end_time=timezone.now(),
                duration=duration,
                duration_millisec=duration_millisec,
                created_by=user
            )

            booking.state_id = SlotBooking.STATE_COMPLETED
            booking.is_active = 0  # NO
            booking.complete_reason = "Therapist change the state to completed"
            booking.save(update_fields=['state_id', 'is_active', 'complete_reason'])

            # Notification with doctor name (matches PHP behavior)
            doctor_name = ""
            if booking.doctor_id:
                doctor_user = User.objects.filter(id=booking.doctor_id).first()
                if doctor_user:
                    doctor_name = getattr(doctor_user, 'full_name', '') or ''
            message = f"Your booking with {doctor_name} completed successfully"

            Notification.objects.create(
                to_user_id=booking.created_by_id,
                created_by=user,
                title=message,
                model_id=booking.id,
                model_type='SlotBooking'
            )
            send_push_notification(
                booking.created_by, message, "",
                data={"controller": "call", "action": "complete-booking",
                      "message": message, "user_id": str(user.id),
                      "detail": SlotBookingSerializer(booking).data},
            )

            logger.info(
                "CompleteBookingView success: user_id=%s booking_id=%s call_id=%s duration=%s",
                user.id,
                booking.id,
                call.id,
                duration,
            )
            return Response({
                "message": "Booking completed successfully",
                "detail": SlotBookingSerializer(booking).data
            }, status=status.HTTP_200_OK)

        except SlotBooking.DoesNotExist:
            logger.warning(
                "CompleteBookingView Bad Request: SlotBooking DoesNotExist for booking_id=%s",
                booking_id,
            )
            return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception(
                "complete-booking failed user_id=%s booking_id=%s raw_duration=%s",
                getattr(user, "id", None),
                booking_id,
                raw_duration,
            )
            return Response(
                {"error": "Unable to complete booking right now."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AgoraTokenView(APIView):
    """
    Mint a short-lived Agora RTC token for a booking participant.

    When AGORA_APP_CERTIFICATE is empty (App ID-only testing mode), returns an
    empty token so existing clients can still join.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return self._issue_token(request)

    def post(self, request):
        return self._issue_token(request)

    def _issue_token(self, request):
        user = request.user
        data = request.data or {}
        query_params = request.query_params or {}

        booking_id = _extract_param(data, query_params, 'booking_id')
        channel = _extract_param(data, query_params, 'channel', 'session_id', 'room_id')
        if not booking_id or not channel:
            return Response(
                {"error": "booking_id and channel are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            booking = SlotBooking.objects.get(id=booking_id)
        except SlotBooking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)

        participant_ids = {booking.created_by_id, booking.doctor_id}
        if user.id not in participant_ids:
            return Response(
                {"error": "Not a participant of this call."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Prefer the stored room when present; otherwise accept client channel
        # (legacy bookings may have an empty room_id until recreated).
        if booking.room_id and booking.room_id != channel:
            return Response(
                {"error": "Channel does not match this booking."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app_id = getattr(settings, "AGORA_APP_ID", "") or ""
        app_certificate = getattr(settings, "AGORA_APP_CERTIFICATE", "") or ""
        expire_seconds = int(getattr(settings, "AGORA_TOKEN_EXPIRE_SECONDS", 3600) or 3600)
        expire_at = int(time.time()) + expire_seconds
        uid = int(user.id)

        token = ""
        if app_id and app_certificate:
            try:
                from agora_token_builder import RtcTokenBuilder

                token = RtcTokenBuilder.buildTokenWithUid(
                    app_id,
                    app_certificate,
                    channel,
                    uid,
                    ROLE_PUBLISHER,
                    expire_at,
                )
            except Exception:
                logger.exception(
                    "agora token generation failed user_id=%s booking_id=%s",
                    user.id,
                    booking_id,
                )
                return Response(
                    {"error": "Unable to generate Agora token right now."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            logger.warning(
                "AGORA_APP_CERTIFICATE not set; returning empty token (App ID-only mode)"
            )

        return Response(
            {
                "token": token,
                "uid": uid,
                "channel": channel,
                "app_id": app_id,
                "expires_at": expire_at,
            },
            status=status.HTTP_200_OK,
        )
