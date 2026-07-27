from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.utils import timezone
from .models import Call
from .serializers import CallSerializer
from availability.views import send_push_notification
from availability.models import SlotBooking, Notification
from accounts.models import User
import logging

logger = logging.getLogger(__name__)

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


class JoinView(APIView):
    permission_classes = (IsAuthenticated,)

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
            logger.warning("JoinView Bad Request: Missing both booking_id and session_id (booking_id=%s, session_id=%s)", booking_id, session_id)
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
                logger.warning("JoinView Bad Request: Booking id=%s session_id=%s does not exist", booking_id, session_id)
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
            return Response({"error": "Receiver user not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("join-call failed user_id=%s booking_id=%s", getattr(user, "id", None), booking_id)
            return Response({"error": "Unable to join call right now."}, status=status.HTTP_400_BAD_REQUEST)

class LeaveView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        data = request.data or {}
        query_params = request.query_params or {}

        booking_id = _extract_param(data, query_params, 'booking_id')
        session_id = _extract_param(data, query_params, 'session_id', 'room_id')
        duration = _extract_param(data, query_params, 'duration') or 0
        duration_millisec = _extract_param(data, query_params, 'duration_millisec') or 0

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
                # "detail": SlotBookingSerializer(booking).data # Omitted to save imports, or add if needed
            }, status=status.HTTP_200_OK)

        except SlotBooking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("complete-booking failed user_id=%s booking_id=%s", getattr(user, "id", None), booking_id)
            return Response({"error": "Unable to complete booking right now."}, status=status.HTTP_400_BAD_REQUEST)
