from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from .models import Call
from .serializers import CallSerializer
from availability.views import send_push_notification
from availability.models import SlotBooking, Notification
from accounts.models import User
import logging
import time

logger = logging.getLogger(__name__)

ROLE_PUBLISHER = 1


def _request_value(request, *keys):
    """Read a value from query params or body, supporting Yii-style nested keys."""
    for key in keys:
        value = request.query_params.get(key)
        if value not in (None, ""):
            return value
        value = request.data.get(key)
        if value not in (None, ""):
            return value
    return None


class JoinView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        booking_id = _request_value(
            request, "booking_id", "Call[booking_id]", "Call[booking_id]]"
        )
        session_id = _request_value(request, "session_id", "Call[session_id]")
        if not booking_id or not session_id:
            return Response({"error": "Data not posted."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = SlotBooking.objects.get(id=booking_id, room_id=session_id)
            
            # Identify receiver
            if user.role_id == User.ROLE_DOCTER:
                receiver_user_id = booking.created_by_id
                name = getattr(user, 'first_name', user.full_name) # Fallback
            else:
                receiver_user_id = booking.doctor_id
                name = user.full_name

            receiver_user = User.objects.get(id=receiver_user_id)

            call = Call.objects.create(
                state_id=1, # JOIN
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
                    model_type='Call'
                )
                send_push_notification(receiver_user, "Incoming Call", message)

            return Response({
                "message": "Joined Successfully.",
                "detail": CallSerializer(call).data
            }, status=status.HTTP_200_OK)

        except SlotBooking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "Receiver user not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("join-call failed user_id=%s booking_id=%s", getattr(user, "id", None), booking_id)
            return Response({"error": "Unable to join call right now."}, status=status.HTTP_400_BAD_REQUEST)


class LeaveView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        booking_id = _request_value(
            request, "booking_id", "Call[booking_id]", "Call[booking_id]]"
        )
        session_id = _request_value(request, "session_id", "Call[session_id]")
        duration = _request_value(request, "duration", "Call[duration]") or 0
        duration_millisec = _request_value(
            request, "duration_millisec", "Call[duration_millisec]"
        ) or 0

        try:
            booking = SlotBooking.objects.get(id=booking_id, room_id=session_id)
            
            call = Call.objects.create(
                state_id=2, # LEFT
                booking_id=booking.id,
                session_id=session_id,
                end_time=timezone.now(),
                duration=duration,
                duration_millisec=duration_millisec,
                created_by=user
            )

            booking.call_duration = duration
            booking.duration_millisec = duration_millisec
            booking.is_call_end = 1 # YES
            booking.save()

            return Response({
                "message": "Room leave Successfully.",
                "detail": CallSerializer(call).data
            }, status=status.HTTP_200_OK)

        except SlotBooking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("leave-call failed user_id=%s booking_id=%s", getattr(user, "id", None), booking_id)
            return Response({"error": "Unable to leave call right now."}, status=status.HTTP_400_BAD_REQUEST)


class CompleteBookingView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, booking_id=None):
        user = request.user
        booking_id = booking_id or request.data.get("booking_id") or request.query_params.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            booking = SlotBooking.objects.get(id=booking_id)
            
            call = Call.objects.create(
                state_id=3, # COMPLETED
                booking_id=booking.id,
                session_id=booking.room_id,
                created_by=user
            )

            booking.state_id = SlotBooking.STATE_COMPLETED
            booking.is_active = 0 # NO
            booking.complete_reason = "Therapist change the state to completed"
            booking.save()

            message = "Your booking completed successfully"
            Notification.objects.create(
                to_user_id=booking.created_by_id,
                created_by=user,
                title=message,
                model_type='SlotBooking'
            )

            return Response({
                "message": "Booking completed successfully",
            }, status=status.HTTP_200_OK)

        except SlotBooking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("complete-booking failed user_id=%s booking_id=%s", getattr(user, "id", None), booking_id)
            return Response({"error": "Unable to complete booking right now."}, status=status.HTTP_400_BAD_REQUEST)


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
        booking_id = _request_value(
            request, "booking_id", "Call[booking_id]", "Call[booking_id]]"
        )
        channel = _request_value(
            request, "channel", "session_id", "Call[session_id]", "room_id"
        )
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
