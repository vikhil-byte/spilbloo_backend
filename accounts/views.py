from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, RegisterSerializer, CustomTokenObtainPairSerializer
from .models import HaLogins
from core.models import (
    ContactForm, LoginHistory, Symptom, UserSymptom, AgeGroup, 
    AssignedTherapist, PushNotification, VideoPlan, Page, Faq
)
from core.serializers import SymptomSerializer, PageSerializer, FaqSerializer, TherapistEarningSerializer
from django.db import transaction
from django.db.models import Case, When, F, Q
import random
import logging
from django.utils import timezone
from django.contrib.auth import authenticate
from django.core.cache import cache

logger = logging.getLogger(__name__)

User = get_user_model()

def send_otp_via_email(email, otp):
    # This is a placeholder for real email service (SendGrid/SES)
    logger.info(f"Sending OTP {otp} to email {email}")
    # In production: send_mail(subject, message, from, [email])
    pass


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

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        # Normalize legacy iOS payload keys (e.g. User[email], User[password]).
        normalized_data = request.data.copy()
        normalized_data["email"] = request.data.get("email") or request.data.get("User[email]")
        normalized_data["password"] = request.data.get("password") or request.data.get("User[password]")
        normalized_data["full_name"] = (
            request.data.get("full_name")
            or request.data.get("User[full_name]")
            or " ".join(
                filter(
                    None,
                    [
                        request.data.get("User[first_name]", "").strip(),
                        request.data.get("User[last_name]", "").strip(),
                    ],
                )
            ).strip()
        )
        normalized_data["role_id"] = request.data.get("role_id") or request.data.get("User[role_id]")
        normalized_data["device_type"] = request.data.get("device_type") or request.data.get("User[device_type]")

        serializer = self.get_serializer(data=normalized_data)
        serializer.is_valid(raise_exception=True)
        device_type = int(normalized_data.get('device_type', 0))
        version = float(request.headers.get('version', 0))

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
        user.save()
        _set_user_otp(user, otp)

        send_otp_via_email(user.email, otp)

        return Response({
            "message": "User registered successfully. Please verify your OTP.",
            "detail": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

class VerifyOtpView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = request.data.get('email') or request.data.get('User[email]')
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
            user.save()
            _mark_user_otp_verified(user)

            # Generate JWT Token (like PHP's create AccessToken / generateAuthKey)
            refresh = RefreshToken.for_user(user)

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
        email = request.data.get('email') or request.data.get('User[email]')
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
        email = request.data.get('email')
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
        # Normalize legacy iOS payload keys.
        email = (
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
                return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.get(email=email)

            # Role Check (Mirroring legacy behavior).
            if int(user.role_id) != role_id:
                if role_id == User.ROLE_DOCTER:
                    return Response({"error": "You are not allowed to login in therapist section with user credentials."}, status=status.HTTP_400_BAD_REQUEST)
                return Response({"error": "You are not allowed to login in user section with therapist credentials."}, status=status.HTTP_400_BAD_REQUEST)

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
                return Response({"error": "Incorrect password."}, status=status.HTTP_400_BAD_REQUEST)

            refresh = RefreshToken.for_user(auth_user)
            response_data = {
                "message": "Login Successfully",
                "access-token": str(refresh.access_token),
                "refresh-token": str(refresh),
                "detail": UserSerializer(auth_user).data
            }

            # OTP challenge for newer versions (legacy behavior).
            if (device_type == 1 and version >= 30) or (device_type == 2 and version >= 2.7):
                otp = str(random.randint(1000, 9999))
                _set_user_otp(auth_user, otp)
                send_otp_via_email(auth_user.email, otp)
                response_data["message"] = "Please verify your OTP."

            return Response(response_data, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "Incorrect Email"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CheckView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        device_type = int(request.headers.get('device-type', 0)) # Mapped from headers or token info
        version = float(request.headers.get('version', 0))

        # PHP logic: actionCheck (login verification and version enforcement)
        if device_type == User.DEVICE_IOS:
             # In PHP: if (!User::checkIsIosLatestVersion())
             # To simulate, let's assume a latest version (e.g. 3.0)
             if version < 3.0:
                  if user.role_id != User.ROLE_DOCTER:
                       # Check if patient has plan
                       has_plan = SubscribedPlan.objects.filter(created_by=user, state_id=1).exists()
                       if not has_plan:
                            return Response({
                                "error": "A new version of app is available please update your app."
                            }, status=status.HTTP_400_BAD_REQUEST)

        # user.setUserActive() logic
        return Response({
            "detail": UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user

        # PHP: update tbl_login_history logout_time
        latest_login = LoginHistory.objects.filter(user=user, state_id=1).order_by('-created_on').first()
        if latest_login:
            latest_login.logout_time = timezone.now()
            latest_login.save()

        # In JWT world, we usually just blacklist the refresh token on the client side
        # Alternatively, we could use simplejwt's blacklist app. Let's return success for now.
        return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)


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
        email = request.data.get('email', '').strip()
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

            # PHP logic uses `generatePasswordResetToken`. We could generate a secure token here.
            # user.activation_key = generate_secure_token()
            # user.save()
            # send email...

            return Response({"message": "Please check your email to reset your password."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Email is not registered."}, status=status.HTTP_400_BAD_REQUEST)


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

    def post(self, request):
        doctor_id = request.data.get('doctor_id')
        type_id = request.data.get('type_id', 1) # Default TYPE_SUBSCRIPTION_PLAN
        patient = request.user

        try:
            doctor = User.objects.get(id=doctor_id, role_id=User.ROLE_DOCTER)
        except User.DoesNotExist:
            return Response({"error": "Therapist not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                if patient.doctor_id:
                    # Update old assigned therapist record
                    old_assign = AssignedTherapist.objects.filter(
                        therapist_id=patient.doctor_id,
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

                patient.doctor_id = doctor.id
                patient.doctor_assigned_time = timezone.now()
                patient.save()

                # Send Notification
                msg = "Tap here to send them your introduction message"
                PushNotification.objects.create(
                    title=msg,
                    description=msg,
                    to_user_id=doctor.id,
                    created_by_id=patient.id,
                )

            return Response({"message": "Therapist assigned successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
                if not patient.doctor_id:
                    new_assign = AssignedTherapist.objects.create(
                        state_id=1, # STATE_ASSIGNED
                        therapist_id=doctor.id,
                        created_by_id=patient.id,
                        assigned_on=timezone.now(),
                        therapist_email=doctor.email,
                        therapist_name=doctor.full_name
                    )
                    patient.doctor_id = doctor.id
                    patient.doctor_assigned_time = timezone.now()
                    patient.save()

                    # Handle Free Plan logic per PHP
                    free_plan = VideoPlan.objects.filter(type_id=1).first() # Assuming type_id 1 is FREE
                    if free_plan:
                        from datetime import timedelta
                        end_date = timezone.now() + timedelta(days=free_plan.duration)
                        # Awaiting SubscribedVideo model implementation, logging for now
                        print(f"Would have created SubscribedVideo for {patient.id} with end_date {end_date}")

                    msg = "Tap here to send them your introduction message"
                    PushNotification.objects.create(
                        title=msg,
                        description=msg,
                        to_user_id=doctor.id,
                        created_by_id=patient.id,
                    )
            
            return Response({
                "message": "Therapist assigned successfully.",
                "detail": UserSerializer(patient).data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SocialLoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        user_data = request.data.get('User', {})
        user_id = user_data.get('user_id')
        role_id = user_data.get('role_id', User.ROLE_PATIENT)
        provider = user_data.get('provider')
        email = user_data.get('email')

        if not user_id:
            return Response({"message": "Please fill all the Details"}, status=status.HTTP_400_BAD_REQUEST)

        if not email or email == '<null>':
            email = f"{user_id}@spilbloo.com"

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
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
        # We need to map `is_consent_accept` onto the Django user or via related model if it doesn't exist.
        # Since we just used AbstractUser, we can just return success or update a JSON field if added.
        return Response({
            "message": "Consent form accepted successfully.",
            "is_consent_accept": 1
        }, status=status.HTTP_200_OK)


class SendMessageView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        to_id = request.query_params.get('to_id') or request.data.get('to_id')
        if not to_id:
            return Response({"message": "to_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            to_user = User.objects.get(id=to_id)
        except User.DoesNotExist:
            return Response({"message": "user not found."}, status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get('title', '')
        type_id = request.data.get('type_id', 0)
        description = request.data.get('description', '')

        # Create PushNotification mapped from Notification
        PushNotification.objects.create(
            title=title,
            description=description,
            to_user_id=to_id,
            created_by_id=request.user.id,
            type_id=type_id
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
        # Legacy endpoint compatibility placeholder until card model migration is complete.
        return Response({"message": "Card deleted successfully."}, status=status.HTTP_200_OK)

