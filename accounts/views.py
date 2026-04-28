from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .serializers import UserSerializer, RegisterSerializer, CustomTokenObtainPairSerializer
from .models import HaLogins
from core.models import (
    ContactForm, LoginHistory, Symptom, UserSymptom, AgeGroup, 
    AssignedTherapist, Page, Faq
)
from availability.models import Notification
from core.serializers import SymptomSerializer, PageSerializer, FaqSerializer, TherapistEarningSerializer
from django.db import transaction
from django.db.models import Case, When, F, Q
import random
import logging
from django.utils import timezone
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from plans.models import Plan, SubscribedPlan
from django.core import signing
import hashlib
import secrets

logger = logging.getLogger(__name__)

User = get_user_model()
DEVICE_ANDROID = 1
DEVICE_IOS = 2
OTP_NOT_VERIFIED = 0

def _normalize_email(value) -> str:
    return (value or "").strip().lower()

def send_otp_via_email(email, otp):
    subject = "Spilbloo OTP Verification"
    message = f"Your OTP is {otp}. It is valid for 10 minutes."
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")
    sent = False
    try:
        send_mail(subject, message, from_email, [email], fail_silently=False)
        sent = True
    except Exception:
        # Keep auth flow resilient even when SMTP is not configured.
        pass
    logger.info("OTP email log: otp=%s", otp)


def _password_reset_cache_key(user_id: int) -> str:
    return f"spilbloo:password_reset:{user_id}"


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _build_password_reset_link(email: str, token: str) -> str:
    base_url = (
        getattr(settings, "PASSWORD_RESET_URL", "")
        or getattr(settings, "FRONTEND_URL", "")
        or "https://app.spilbloo.com/reset-password"
    )
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}email={email}&token={token}"


def send_password_reset_email(email: str, reset_link: str):
    subject = "Reset your Spilbloo password"
    message = (
        "We received a request to reset your password.\n\n"
        f"Use this link to set a new password:\n{reset_link}\n\n"
        "This link expires in 30 minutes."
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")
    try:
        send_mail(subject, message, from_email, [email], fail_silently=False)
    except Exception:
        logger.info("Password reset email fallback log: email=%s", email)


def _otp_cache_key(user_id: int) -> str:
    return f"spilbloo:otp:{user_id}"


def _set_user_otp(user, otp: str) -> None:
    otp_str = str(otp)
    if hasattr(user, "otp"):
        user.otp = otp_str
        if hasattr(user, "otp_verified"):
            user.otp_verified = 0
        user.save()
        return
    cache.set(_otp_cache_key(user.id), otp_str, timeout=600)


def _get_user_otp(user):
    if hasattr(user, "otp"):
        return getattr(user, "otp", None)
    return cache.get(_otp_cache_key(user.id))


def _mark_user_otp_verified(user) -> None:
    if hasattr(user, "otp"):
        if hasattr(user, "otp_verified"):
            user.otp_verified = 1
        user.otp = None
        user.save()
        return
    cache.delete(_otp_cache_key(user.id))


def _enforce_ios_version_gate(user, device_type: int, version: float):
    """
    Mirror legacy PHP check/login version gate for iOS users.
    """
    if device_type != DEVICE_IOS:
        return None
    if version >= 3.0:
        return None
    if user.role_id == User.ROLE_DOCTER:
        return None
    if SubscribedPlan.objects.filter(created_by=user, state_id=1).exists():
        return None
    return Response(
        {"error": "A new version of app is available please update your app."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _safe_int(value, default=0):
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_str(value, default=""):
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _legacy_user_detail(user):
    """
    Build compatibility payload expected by legacy iOS user model parsing.
    """
    otp_verified = getattr(user, "otp_verified", None)
    if otp_verified is None:
        # Legacy behavior: active users are treated as verified unless explicitly unverified.
        otp_verified = 1 if user.state_id == User.STATE_ACTIVE else 0

    active_paid_subscription = (
        SubscribedPlan.objects.filter(created_by=user, state_id=1, plan_type=1)
        .select_related("plan")
        .order_by("-id")
        .first()
    )
    subscribed_plan = None
    if active_paid_subscription:
        plan_obj = active_paid_subscription.plan
        plan_detail = {}
        if plan_obj:
            total_price = float(plan_obj.total_price or 0)
            weekly_price = total_price / 4 if total_price else 0
            plan_detail = {
                "id": plan_obj.id,
                "plan_id": plan_obj.plan_id or "",
                "title": plan_obj.title or "",
                "description": plan_obj.description or "",
                "video_description": "",
                "no_of_video_session": plan_obj.no_of_video_session or 0,
                "no_of_free_trial_days": plan_obj.no_of_free_trial_days or 0,
                "discounted_price": str(plan_obj.total_price or "0"),
                "discounted_price_calculated": int(round(total_price)),
                "total_price": str(plan_obj.total_price or "0"),
                "tax_price": str(plan_obj.tax_price or "0"),
                "tax_percentage": "18",
                "final_price": str(plan_obj.final_price or "0"),
                "weekly_price": "{:.2f}".format(weekly_price) if weekly_price else "0",
                "is_recommended": plan_obj.is_recommended or 0,
                "plan_type": plan_obj.plan_type or 1,
                "duration": plan_obj.duration or 30,
                "currency_code": plan_obj.currency_code or "INR",
                "company_name": "",
            }

        subscribed_plan = {
            "id": active_paid_subscription.id,
            "state_id": active_paid_subscription.state_id,
            "upcoming_state": active_paid_subscription.upcoming_state or 0,
            "plan_id": plan_obj.id if plan_obj else 0,
            "renewal_date": active_paid_subscription.renewal_date.isoformat() if active_paid_subscription.renewal_date else "",
            "start_date": active_paid_subscription.start_date.isoformat() if active_paid_subscription.start_date else "",
            "end_date": active_paid_subscription.end_date.isoformat() if active_paid_subscription.end_date else "",
            "plan_detail": plan_detail,
        }

    return {
        "id": user.id,
        "email": user.email or "",
        "full_name": user.full_name or "",
        "first_name": getattr(user, "first_name", "") or "",
        "last_name": getattr(user, "last_name", "") or "",
        "role_id": user.role_id,
        "state_id": user.state_id,
        "contact_no": getattr(user, "contact_no", "") or "",
        "address": getattr(user, "address", "") or "",
        "city": getattr(user, "city", "") or "",
        "country": getattr(user, "country", "") or "",
        "profile_file": getattr(user, "profile_file", "") or "",
        "doctor_id": _safe_str(getattr(user, "doctor_id", "") or ""),
        "provider": 0,
        "isOnline": _safe_str(getattr(user, "online", "") or ""),
        "otp_verified": otp_verified,
        "otp": _safe_str(getattr(user, "otp", "") or ""),
        "is_ios_app_update": False,
        "is_subscribed_user": bool(active_paid_subscription),
        "is_buy_subscripion": bool(active_paid_subscription),
        "is_buy_video_credits": False,
        "video_credits": 0,
        "subscribed_plan": subscribed_plan or {},
    }

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        if not request.data:
            logger.warning("Signup rejected: empty payload")
            return Response({"error": "Data not posted."}, status=status.HTTP_400_BAD_REQUEST)

        user_payload = request.data.get("User")
        if not isinstance(user_payload, dict):
            user_payload = {}

        # Normalize legacy iOS payload keys (e.g. User[email], User[password]).
        normalized_data = request.data.copy()
        normalized_data["email"] = (
            request.data.get("email")
            or request.data.get("User[email]")
            or user_payload.get("email")
        )
        normalized_data["password"] = (
            request.data.get("password")
            or request.data.get("User[password]")
            or user_payload.get("password")
        )
        normalized_data["full_name"] = (
            request.data.get("full_name")
            or request.data.get("User[full_name]")
            or user_payload.get("full_name")
            or " ".join(
                filter(
                    None,
                    [
                        request.data.get("User[first_name]", "").strip(),
                        request.data.get("User[last_name]", "").strip(),
                        (user_payload.get("first_name") or "").strip(),
                        (user_payload.get("last_name") or "").strip(),
                    ],
                )
            ).strip()
        )
        normalized_data["role_id"] = (
            request.data.get("role_id")
            or request.data.get("User[role_id]")
            or user_payload.get("role_id")
        )
        normalized_data["device_type"] = (
            request.data.get("device_type")
            or request.data.get("User[device_type]")
            or user_payload.get("device_type")
        )

        # Prevent null values from tripping serializer validation; match PHP defaults.
        if normalized_data.get("role_id") in (None, ""):
            normalized_data["role_id"] = User.ROLE_PATIENT
        if normalized_data.get("password") is None:
            normalized_data["password"] = ""

        email = _normalize_email(normalized_data.get("email"))
        normalized_data["email"] = email
        if email and User.objects.filter(email=email).exists():
            logger.warning("Signup rejected: duplicate email=%s", email)
            return Response({"error": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=normalized_data)
        if not serializer.is_valid():
            error_messages = []
            for errors in serializer.errors.values():
                if isinstance(errors, (list, tuple)):
                    error_messages.extend(str(err) for err in errors)
                else:
                    error_messages.append(str(errors))
            # Never log password values. Keep payload diagnostics minimal and safe.
            logger.warning(
                "Signup validation failed: errors=%s email=%s has_password=%s payload_keys=%s",
                serializer.errors,
                normalized_data.get("email"),
                bool(normalized_data.get("password")),
                sorted(list(request.data.keys())),
            )
            return Response(
                {"error": ",".join(error_messages) or "Data not posted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_type = _safe_int(normalized_data.get('device_type'), 0)
        version = _safe_float(request.headers.get('version', 0), 0.0)

        # PHP logic: (deviceType == 1 && version >= 30) || (deviceType == 2 && version >= 2.7)
        # device_type 1 = Android, 2 = iOS (or vice versa depending on mapping, let's assume 1=Android, 2=iOS)
        # However, looking at UserController.php lines 278, it checks device_type 1 and 2.
        # Let's mirror exactly:
        if (device_type == 1 and version >= 30) or (device_type == 2 and version >= 2.7):
             # Generate random password if it's a newer app version
             password = User.objects.make_random_password()
        else:
             password = normalized_data.get('password')

        user = serializer.save()
        user.set_password(password)

        otp = str(random.randint(1000, 9999))
        user.role_id = User.ROLE_PATIENT # Default role from PHP signup
        user.state_id = User.STATE_INACTIVE
        if hasattr(user, "otp_verified"):
            user.otp_verified = OTP_NOT_VERIFIED
        if hasattr(user, "email_verified"):
            user.email_verified = 0
        user.save()
        _set_user_otp(user, otp)

        send_otp_via_email(user.email, otp)
        logger.info("Signup success: user_id=%s email=%s", user.id, user.email)

        return Response({
            "message": "Please verify your OTP.",
            "detail": UserSerializer(user).data
        }, status=status.HTTP_200_OK)

class VerifyOtpView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = _normalize_email(request.data.get('email') or request.data.get('User[email]'))
        otp = request.data.get('otp') or request.data.get('User[otp]')

        if not email or not otp:
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Incorrect Email"}, status=status.HTTP_400_BAD_REQUEST)

        stored_otp = _get_user_otp(user)
        if str(stored_otp) == str(otp):
            user.state_id = User.STATE_ACTIVE
            refresh = RefreshToken.for_user(user)
            # Legacy node auth checks activation_key as bearer token.
            user.activation_key = str(refresh.access_token)
            user.save()
            _mark_user_otp_verified(user)

            # Log history
            LoginHistory.objects.create(
                user=user,
                state_id=1, # STATE_SUCCESS
                type_id=1 # TYPE_API
            )

            return Response({
                "message": "Your account successfully verified!",
                "access-token": str(refresh.access_token),
                "refresh-token": str(refresh),
                "detail": UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Incorrect OTP"}, status=status.HTTP_400_BAD_REQUEST)

class ResendOtpView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = _normalize_email(request.data.get('email') or request.data.get('User[email]'))
        if not email:
            return Response({"error": "No data posted"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            otp = str(random.randint(1000, 9999))
            _set_user_otp(user, otp)

            send_otp_via_email(user.email, otp)

            return Response({
                "message": "Verification code sent successfully"
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "No User found"}, status=status.HTTP_400_BAD_REQUEST)

class DoctorContactView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        # Migrating `actionDoctorContact()`
        email = _normalize_email(request.data.get('email'))
        if ContactForm.objects.filter(email=email).exists():
             return Response({"error": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Serialize and save using DRF core serializer (we will need to import it here or create manually)
        # For simplicity of custom logic view, creating manually:
        form = ContactForm.objects.create(
            full_name=request.data.get('full_name'),
            email=email,
            contact_no=request.data.get('contact_no'),
            reason=request.data.get('reason'),
            description=request.data.get('description'),
            state_id=0 # STATE_INACTIVE
        )
        return Response({
            "message": "Your information submitted successfully.",
            "detail": {
                "id": form.id,
                "email": form.email
            }
        }, status=status.HTTP_200_OK)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        if not request.data:
            # Legacy PHP actionLogin() when model load fails.
            return Response({"error": "No data posted."}, status=status.HTTP_400_BAD_REQUEST)

        # Normalize legacy iOS payload keys.
        email = _normalize_email(
            request.data.get('email')
            or request.data.get('username')
            or request.data.get('LoginForm[username]')
        )
        password = request.data.get('password') or request.data.get('LoginForm[password]')
        role_id = int(request.data.get('role_id') or request.data.get('LoginForm[role_id]') or 0)
        device_type = int(request.data.get('device_type') or request.data.get('LoginForm[device_type]') or 0)
        version = float(request.headers.get('version', 0))

        try:
            if not email:
                return Response({"error": "No data posted."}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.get(email=email)

            legacy_version_gate_error = _enforce_ios_version_gate(user, device_type, version)
            if legacy_version_gate_error:
                return legacy_version_gate_error

            # Role Check (Mirroring legacy behavior).
            if int(user.role_id) != role_id:
                if role_id == User.ROLE_DOCTER:
                    return Response({"error": "You are not allowed to login in therapist section with user credentials."}, status=status.HTTP_400_BAD_REQUEST)
                return Response({"error": "You are not allowed to login in user section with therapist credentials."}, status=status.HTTP_400_BAD_REQUEST)

            # Legacy LoginForm.loginuser() blocks admin logins in API flow.
            if user.role_id == User.ROLE_ADMIN:
                return Response({"error": "You are not allowed to login."}, status=status.HTTP_400_BAD_REQUEST)

            # Legacy branch parity:
            # - inactive + otp not verified => 200 guidance response
            # - inactive otherwise => error
            if user.state_id == User.STATE_INACTIVE:
                if getattr(user, "otp_verified", OTP_NOT_VERIFIED) == OTP_NOT_VERIFIED:
                    return Response(
                        {
                            "message": "Details already exist. You need to verify your otp first",
                            "detail": UserSerializer(user).data,
                        },
                        status=status.HTTP_200_OK,
                    )
                return Response({"error": " User is not active"}, status=status.HTTP_400_BAD_REQUEST)

            # Legacy iOS OTP-login flow: password can be empty and still return OTP challenge.
            if not (password or "").strip():
                otp = str(random.randint(1000, 9999))
                _set_user_otp(user, otp)
                send_otp_via_email(user.email, otp)
                return Response({
                    "message": "Please verify your OTP.",
                    "detail": UserSerializer(user).data
                }, status=status.HTTP_200_OK)

            auth_user = authenticate(request, username=email, password=password) or authenticate(request, email=email, password=password)
            if not auth_user:
                return Response({"error": "Incorrect Email Or Password."}, status=status.HTTP_400_BAD_REQUEST)

            refresh = RefreshToken.for_user(auth_user)
            # Legacy node auth checks activation_key as bearer token.
            auth_user.activation_key = str(refresh.access_token)
            auth_user.save(update_fields=["activation_key"])
            response_data = {
                "message": "Login Successfully",
                "access-token": str(refresh.access_token),
                "refresh-token": str(refresh),
                "detail": UserSerializer(auth_user).data
            }

            # OTP challenge for newer versions (legacy behavior).
            otp_required = (device_type == 1 and version >= 30) or (device_type == 2 and version >= 2.7)
            logger.info(
                "Login OTP decision: email=%s device_type=%s version=%s required=%s",
                auth_user.email,
                device_type,
                version,
                otp_required,
            )
            if otp_required:
                otp = str(random.randint(1000, 9999))
                _set_user_otp(auth_user, otp)
                send_otp_via_email(auth_user.email, otp)
                response_data["message"] = "Please verify your OTP."

            return Response(response_data, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "Incorrect Email"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("login failed unexpectedly for email=%s", email)
            return Response({"error": "Unable to process login request."}, status=status.HTTP_400_BAD_REQUEST)

class CheckView(APIView):
    permission_classes = (AllowAny,)

    def handle_exception(self, exc):
        if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            auth_header = self.request.headers.get("Authorization", "")
            auth_preview = ""
            if auth_header:
                parts = auth_header.split(" ", 1)
                if len(parts) == 2:
                    scheme, token = parts
                    auth_preview = f"{scheme} {token[:12]}..."
                else:
                    auth_preview = f"{auth_header[:20]}..."
            logger.warning(
                "check auth failed: reason=%s has_auth=%s auth_preview=%s method=%s path=%s user_agent=%s content_type=%s",
                str(exc),
                bool(auth_header),
                auth_preview,
                self.request.method,
                self.request.path,
                self.request.headers.get("User-Agent", ""),
                self.request.content_type,
            )
            # Legacy PHP actionCheck returns guest payload instead of 401
            # when user is unauthenticated/expired.
            return Response(
                {"message": "User not authenticated. No device token found"},
                status=status.HTTP_200_OK,
            )
        return super().handle_exception(exc)

    def _handle_check(self, request):
        if not request.user.is_authenticated:
            # Match legacy PHP actionCheck guest response shape.
            return Response(
                {"message": "User not authenticated. No device token found"},
                status=status.HTTP_200_OK,
            )

        user = request.user
        device_type = int(request.headers.get('device-type', 0))
        version = float(request.headers.get('version', 0))

        legacy_version_gate_error = _enforce_ios_version_gate(user, device_type, version)
        if legacy_version_gate_error:
            return legacy_version_gate_error

        # Legacy setUserActive equivalent.
        user.last_action_time = timezone.now()
        user.save(update_fields=["last_action_time"])

        return Response({
            "detail": _legacy_user_detail(user)
        }, status=status.HTTP_200_OK)

    def get(self, request):
        return self._handle_check(request)

    def post(self, request):
        # Legacy clients call this endpoint with POST; keep behavior identical to GET.
        return self._handle_check(request)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user

        # PHP: update tbl_login_history logout_time
        latest_login = LoginHistory.objects.filter(user=user, state_id=1).order_by('-created_on').first()
        if latest_login:
            latest_login.logout_time = timezone.now()
            latest_login.save()

        refresh_token = request.data.get("refresh-token") or request.data.get("refresh_token")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except (TokenError, AttributeError):
                # AttributeError occurs if blacklist app isn't installed.
                logger.warning("logout blacklist skipped for user_id=%s", getattr(user, "id", None))

        if hasattr(user, "activation_key"):
            user.activation_key = None
            user.save(update_fields=["activation_key"])
        return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)

    def get(self, request):
        # Legacy iOS flow may call logout as GET.
        return self.post(request)


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        # PHP: actionUpdateProfile allows updating user details
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            "detail": serializer.data
        }, status=status.HTTP_200_OK)


class DetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({"detail": serializer.data}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Data Not Found"}, status=status.HTTP_400_BAD_REQUEST)


# The Page model has not been implemented in Django core yet

# The Page model has not been implemented in Django core yet
class GetPageView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        type_id = request.query_params.get('type_id')
        if not type_id:
             return Response({"error": "type_id required"}, status=status.HTTP_400_BAD_REQUEST)

        page = Page.objects.filter(type_id=type_id, state_id=1).first()
        if page:
            return Response({"detail": PageSerializer(page).data}, status=status.HTTP_200_OK)
        return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)

class ForgotPasswordView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = _normalize_email(request.data.get('email'))
        role_id = request.data.get('role_id')

        if not email:
            return Response({"error": "Email cannot be blank"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            if str(user.role_id) != str(role_id):
                if int(role_id) == User.ROLE_PATIENT:
                    return Response({"message": "You cannot reset password with patient email."}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "You cannot reset password with therapist email."}, status=status.HTTP_200_OK)

            # Secure, expiring reset token without DB schema changes:
            # - sign a random nonce with timestamp
            # - store only token hash in cache
            # - email link to user
            nonce = secrets.token_urlsafe(24)
            signed_token = signing.TimestampSigner(salt="spilbloo-password-reset").sign(nonce)
            cache.set(_password_reset_cache_key(user.id), _hash_reset_token(signed_token), timeout=1800)
            reset_link = _build_password_reset_link(user.email, signed_token)
            send_password_reset_email(user.email, reset_link)

            return Response({"message": "Please check your email to reset your password."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Email is not registered."}, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordConfirmView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = _normalize_email(request.data.get("email"))
        token = (request.data.get("token") or "").strip()
        new_password = request.data.get("new_password") or request.data.get("password")

        if not email or not token or not new_password:
            return Response({"error": "email, token and new_password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            signing.TimestampSigner(salt="spilbloo-password-reset").unsign(token, max_age=1800)
        except signing.BadSignature:
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)
        except signing.SignatureExpired:
            return Response({"error": "Reset link expired."}, status=status.HTTP_400_BAD_REQUEST)

        expected_hash = cache.get(_password_reset_cache_key(user.id))
        if not expected_hash or not secrets.compare_digest(expected_hash, _hash_reset_token(token)):
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.last_password_change = timezone.now()
        user.save(update_fields=["password", "last_password_change"])
        cache.delete(_password_reset_cache_key(user.id))

        return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)


class SymptomListView(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SymptomSerializer

    def get_queryset(self):
        # PHP `Symptom::findActive()` usually means state_id = 1
        return Symptom.objects.filter(state_id=1).order_by('-id')


class MatchesListView(APIView):
    permission_classes = (AllowAny,) # PHP roles allow ?, *, @

    def post(self, request):
        symptom_ids_str = request.data.get('symptom', '')
        if not symptom_ids_str:
            return Response({"error": "No data posted."}, status=status.HTTP_400_BAD_REQUEST)

        symptom_ids = [sid.strip() for sid in symptom_ids_str.split(',') if sid.strip()]
        user = request.user

        # 1. Update User Symptoms if authenticated (actionMatchesList 676-687)
        if user.is_authenticated:
            with transaction.atomic():
                UserSymptom.objects.filter(created_by_id=user.id).delete()
                for s_id in symptom_ids:
                    UserSymptom.objects.create(
                        symptom_id=s_id,
                        created_by_id=user.id
                    )
        
        # 2. Find matching doctors
        matching_doctor_ids = UserSymptom.objects.filter(
            symptom_id__in=symptom_ids
        ).values_list('created_by_id', flat=True).distinct()

        # 3. Build Doctor Query
        doctors = User.objects.filter(
            state_id=User.STATE_ACTIVE,
            role_id=User.ROLE_DOCTER,
            id__in=matching_doctor_ids,
            is_available=1 # IS_AVAILABLE_YES
        )

        # 4. Remove currently assigned doctor
        if user.is_authenticated and user.doctor_id:
            doctors = doctors.exclude(id=user.doctor_id)

        # 5. Sorting (actionMatchesList 711-730)
        # Priority 1: User's Gender Preference
        if user.is_authenticated and user.therapist_gender:
            doctors = doctors.order_by(
                Case(When(gender=user.therapist_gender, then=0), default=1)
            )

        # Priority 2: Age Group Matching (Simplified equivalent)
        # Note: PHP uses FIELD() on group_id. 
        # Here we just ensure we get doctors.

        # Priority 3: Random
        doctors = doctors.order_by('?')

        return Response({
            "list": UserSerializer(doctors[:3], many=True).data
        }, status=status.HTTP_200_OK)

class FaqView(APIView):
    permission_classes = (AllowAny,)
    
    def get(self, request):
        type_id = request.query_params.get('type_id') # e.g. User Role
        faqs = Faq.objects.filter(state_id=1)
        if type_id:
            faqs = faqs.filter(type_id=type_id)
            
        return Response({"list": FaqSerializer(faqs, many=True).data}, status=status.HTTP_200_OK)

class AssignDoctorView(APIView):
    permission_classes = (IsAuthenticated,)

    def _assign(self, request):
        doctor_id = request.data.get('doctor_id') or request.query_params.get('doctor_id')
        type_id = request.data.get('type_id', 1) # Default TYPE_SUBSCRIPTION_PLAN
        patient = request.user

        try:
            doctor = User.objects.get(id=doctor_id, role_id=User.ROLE_DOCTER)
        except User.DoesNotExist:
            return Response({"error": "Therapist not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                current_doctor_id = getattr(patient, "doctor_id", None)
                if current_doctor_id:
                    # Update old assigned therapist record
                    old_assign = AssignedTherapist.objects.filter(
                        therapist_id=current_doctor_id,
                        created_by_id=patient.id
                    ).first()
                    
                    if old_assign:
                        old_assign.changed_on = timezone.now()
                        old_assign.state_id = 2 # STATE_CHANGED
                        old_assign.save()
                        # old_assign.sendPatientLeaveMailToDoctor()

                # Record new therapist
                new_assign = AssignedTherapist.objects.create(
                    state_id=1, # STATE_ASSIGNED
                    therapist_id=doctor.id,
                    created_by_id=patient.id,
                    assigned_on=timezone.now(),
                    therapist_email=doctor.email,
                    therapist_name=doctor.full_name
                )

                updated_user_fields = []
                if hasattr(patient, "doctor_id"):
                    patient.doctor_id = doctor.id
                    updated_user_fields.append("doctor_id")
                if hasattr(patient, "doctor_assigned_time"):
                    patient.doctor_assigned_time = timezone.now()
                    updated_user_fields.append("doctor_assigned_time")
                if updated_user_fields:
                    patient.save(update_fields=updated_user_fields)

                # Legacy PHP uses tbl_notification (per-user), not tbl_push_notification.
                msg = "Tap here to send them your introduction message"
                Notification.objects.create(
                    title=msg,
                    html=msg,
                    to_user_id=doctor.id,
                    created_by_id=patient.id,
                )

            return Response({"message": "Therapist assigned successfully."}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("assign-doctor failed: user_id=%s doctor_id=%s", getattr(request.user, "id", None), doctor_id)
            return Response({"error": "Unable to assign therapist right now."}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        return self._assign(request)

    def get(self, request):
        # Legacy iOS flow calls assign-doctor with query params.
        return self._assign(request)

class AssignVideoDoctorView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        doctor_id = request.data.get('doctor_id')
        patient = request.user

        try:
            doctor = User.objects.get(id=doctor_id, role_id=User.ROLE_DOCTER)
        except User.DoesNotExist:
            return Response({"error": "Therapist not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                if not getattr(patient, "doctor_id", None):
                    new_assign = AssignedTherapist.objects.create(
                        state_id=1, # STATE_ASSIGNED
                        therapist_id=doctor.id,
                        created_by_id=patient.id,
                        assigned_on=timezone.now(),
                        therapist_email=doctor.email,
                        therapist_name=doctor.full_name
                    )
                    updated_user_fields = []
                    if hasattr(patient, "doctor_id"):
                        patient.doctor_id = doctor.id
                        updated_user_fields.append("doctor_id")
                    if hasattr(patient, "doctor_assigned_time"):
                        patient.doctor_assigned_time = timezone.now()
                        updated_user_fields.append("doctor_assigned_time")
                    if updated_user_fields:
                        patient.save(update_fields=updated_user_fields)

                    # Handle free subscription seed per PHP assign-video-doctor flow.
                    free_plan = Plan.objects.filter(plan_type=0, state_id=1).order_by("id").first()
                    if free_plan and not SubscribedPlan.objects.filter(
                        created_by=patient,
                        plan=free_plan,
                        plan_type=0,
                        state_id=1,
                    ).exists():
                        from datetime import timedelta

                        start_date = timezone.now()
                        end_date = start_date + timedelta(days=int(free_plan.duration or 0))
                        SubscribedPlan.objects.create(
                            plan=free_plan,
                            plan_type=0,
                            state_id=1,
                            start_date=start_date,
                            end_date=end_date,
                            renewal_date=end_date,
                            subscription_id=str(free_plan.id),
                            plan_price=free_plan.total_price,
                            gst_price=free_plan.tax_price,
                            final_price=free_plan.final_price,
                            coupon_free_trial_days=0,
                            type_id=2,
                            upcoming_plan_id=free_plan.id,
                            upcoming_state=1,
                            created_by=patient,
                        )

                    msg = "Tap here to send them your introduction message"
                    Notification.objects.create(
                        title=msg,
                        html=msg,
                        to_user_id=doctor.id,
                        created_by_id=patient.id,
                    )
            
            return Response({
                "message": "Therapist assigned successfully.",
                "detail": UserSerializer(patient).data
            }, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("assign-video-doctor failed: user_id=%s doctor_id=%s", getattr(request.user, "id", None), doctor_id)
            return Response({"error": "Unable to assign therapist right now."}, status=status.HTTP_400_BAD_REQUEST)

class SocialLoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        user_data = request.data.get('User', {})
        user_id = user_data.get('user_id')
        role_id = user_data.get('role_id', User.ROLE_PATIENT)
        provider = user_data.get('provider')
        email = _normalize_email(user_data.get('email'))

        if not user_id:
            return Response({"message": "Please fill all the Details"}, status=status.HTTP_400_BAD_REQUEST)

        if not email or email == '<null>':
            email = _normalize_email(f"{user_id}@spilbloo.com")

        auth = HaLogins.objects.filter(user_id_str=str(user_id)).first()

        try:
            with transaction.atomic():
                if not auth:
                    # Not exist, register
                    user = User.objects.filter(email=email).first()
                    if not user:
                        user = User.objects.create_user(
                            email=email,
                            password=str(user_id), # PHP uses user_id as password hash initially
                            role_id=role_id,
                            state_id=User.STATE_ACTIVE
                        )
                        first_name = user_data.get('first_name', 'Default')
                        last_name = user_data.get('last_name', 'Name')
                        user.full_name = f"{first_name} {last_name}"
                        user.save()

                    auth = HaLogins.objects.create(
                        user_id_str=str(user_id),
                        login_provider=provider,
                        login_provider_identifier=user_id, # Simplified hash
                        created_by_id=user.id,
                        user=user
                    )
                else:
                    # Already exists
                    user = auth.user
                    if user.state_id == User.STATE_BANNED:
                        return Response({"message": "Your account is blocked, Please contact Particulars Admin"}, status=status.HTTP_403_FORBIDDEN)
                    if user.state_id == User.STATE_INACTIVE:
                        return Response({"message": "Your account is not verified by admin"}, status=status.HTTP_403_FORBIDDEN)
                    
                if int(user.role_id) != int(role_id):
                    return Response({"message": "You are not allowed to login."}, status=status.HTTP_403_FORBIDDEN)

                # Generate Token
                refresh = RefreshToken.for_user(user)
                return Response({
                    "message": "Login Successfully" if auth else "Signup",
                    "access-token": str(refresh.access_token),
                    "refresh-token": str(refresh),
                    "is_login": 1 if auth else 0,
                    "detail": UserSerializer(user).data
                }, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("social-login failed for provider=%s user_id=%s", provider, user_id)
            return Response({"error": "Unable to process social login."}, status=status.HTTP_400_BAD_REQUEST)


class EarningsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        if int(user.role_id) != User.ROLE_DOCTER:
             return Response({"error": "Only therapists have earnings."}, status=status.HTTP_403_FORBIDDEN)
             
        earnings = TherapistEarning.objects.filter(therapist=user, state_id=1).order_by('-date')
        
        total_earning = sum([float(e.amount or 0) for e in earnings])
        
        # Pagination simplified
        return Response({
            "total_earning": "{:.2f}".format(total_earning),
            "list": TherapistEarningSerializer(earnings[:50], many=True).data
        }, status=status.HTTP_200_OK)


class AcceptConsentView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        # PHP parity: persist consent acceptance on user when fields exist.
        update_fields = []
        if hasattr(user, "is_consent_accept"):
            user.is_consent_accept = 1
            update_fields.append("is_consent_accept")
        if hasattr(user, "consent_accepted_on"):
            user.consent_accepted_on = timezone.now()
            update_fields.append("consent_accepted_on")
        if update_fields:
            user.save(update_fields=update_fields)

        return Response({
            "message": "Consent form accepted successfully.",
            "is_consent_accept": getattr(user, "is_consent_accept", 1)
        }, status=status.HTTP_200_OK)

    def get(self, request):
        # Legacy iOS flow calls accept-consent as GET.
        return self.post(request)


class SendMessageView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        to_id = request.query_params.get('to_id') or request.data.get('to_id')
        if not to_id:
            return Response({"message": "to_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not User.objects.filter(id=to_id).exists():
            return Response({"message": "user not found."}, status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get('title', '')
        description = request.data.get('description', '')

        # Direct message alert is a per-user notification row.
        Notification.objects.create(
            title=title,
            html=description,
            to_user_id=to_id,
            created_by_id=request.user.id,
        )

        return Response({"message": "sent"}, status=status.HTTP_200_OK)


class GetCountryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        search = request.query_params.get("name", "").strip()
        countries_qs = User.objects.exclude(country__isnull=True).exclude(country__exact="")
        if search:
            countries_qs = countries_qs.filter(country__icontains=search)
        countries = (
            countries_qs.values_list("country", flat=True)
            .distinct()
            .order_by("country")
        )
        return Response({"list": [{"name": country} for country in countries]}, status=status.HTTP_200_OK)


class GetCityView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        search = request.query_params.get("name", "").strip()
        country = request.query_params.get("country_id", "").strip()

        cities_qs = User.objects.exclude(city__isnull=True).exclude(city__exact="")
        if country:
            cities_qs = cities_qs.filter(country__iexact=country)
        if search:
            cities_qs = cities_qs.filter(city__icontains=search)

        cities = (
            cities_qs.values_list("city", flat=True)
            .distinct()
            .order_by("city")
        )
        return Response({"list": [{"name": city} for city in cities]}, status=status.HTTP_200_OK)


class UserSearchView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        users = User.objects.filter(state_id=User.STATE_ACTIVE)
        if search:
            users = users.filter(
                Q(full_name__icontains=search)
                | Q(email__icontains=search)
            )
        users = users.order_by("id")[:50]
        data = [
            {
                "id": user.id,
                "full_name": user.full_name or "",
                "email": user.email or "",
                "profile_file": user.profile_file or "",
            }
            for user in users
        ]
        return Response({"list": data}, status=status.HTTP_200_OK)


class DefaultAddressView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # Legacy endpoint compatibility: backend currently stores only a single address on User.
        return Response(
            {
                "message": "Default address is your current profile address.",
                "detail": {
                    "address": request.user.address or "",
                    "city": request.user.city or "",
                    "country": request.user.country or "",
                },
            },
            status=status.HTTP_200_OK,
        )


class CardDeleteView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        # Best-effort cleanup across legacy naming variants.
        card_fields = [
            "card_id",
            "stripe_card_id",
            "stripe_customer_id",
            "customer_id",
            "payment_method_id",
            "card_last4",
            "card_brand",
            "card_token",
        ]
        update_fields = []
        for field in card_fields:
            if hasattr(user, field):
                setattr(user, field, "")
                update_fields.append(field)
        if update_fields:
            user.save(update_fields=update_fields)
        return Response({"message": "Card deleted successfully."}, status=status.HTTP_200_OK)

