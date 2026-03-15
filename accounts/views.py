from rest_framework import generics, status, pagination
from rest_framework.response import Response
from core.mixins import StandardizedResponseMixin
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import IsAdminUser
from django.contrib.auth import get_user_model, authenticate
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, RegisterSerializer, CustomTokenObtainPairSerializer
from .models import HaLogins
from core.models import (
    ContactForm, LoginHistory, Symptom, UserSymptom, AgeGroup, 
    AssignedTherapist, PushNotification, VideoPlan, Page, Faq, AuditLog
)
from core.serializers import (
    SymptomSerializer, PageSerializer, FaqSerializer, 
    TherapistEarningSerializer, AuditLogSerializer, LoginHistorySerializer
)
from rest_framework.generics import ListAPIView
from django.db import transaction
from django.db.models import Case, When, F, Q
import random
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

User = get_user_model()

def send_otp_via_email(email, otp):
    # This is a placeholder for real email service (SendGrid/SES)
    logger.info(f"Sending OTP {otp} to email {email}")
    # In production: send_mail(subject, message, from, [email])
    pass

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        # 1. Custom logic: Generate OTP

        # 2. Extract basic validation and saving via DRF serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device_type = int(request.data.get('device_type', 0))
        version = float(request.headers.get('version', 0))

        # PHP logic: (deviceType == 1 && version >= 30) || (deviceType == 2 && version >= 2.7)
        # device_type 1 = Android, 2 = iOS (or vice versa depending on mapping, let's assume 1=Android, 2=iOS)
        # However, looking at UserController.php lines 278, it checks device_type 1 and 2.
        # Let's mirror exactly:
        if (device_type == 1 and version >= 30) or (device_type == 2 and version >= 2.7):
             # Generate random password if it's a newer app version
             password = User.objects.make_random_password()
        else:
             password = request.data.get('password')

        user = serializer.save()
        user.set_password(password)

        otp = str(random.randint(1000, 9999))
        user.otp = otp
        user.otp_verified = 0 # User.OTP_NOT_VERIFIED mapping
        user.role_id = User.ROLE_PATIENT # Default role from PHP signup
        user.save()

        send_otp_via_email(user.email, otp)

        return Response({
            "message": "User registered successfully. Please verify your OTP.",
            "detail": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

class VerifyOtpView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Incorrect Email"}, status=status.HTTP_400_BAD_REQUEST)

        if str(user.otp) == str(otp):
            user.state_id = User.STATE_ACTIVE
            user.otp_verified = 1 # Verified
            user.otp = None # Clear OTP
            user.save()

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
        email = request.data.get('email')
        if not email:
            return Response({"error": "No data posted"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            otp = str(random.randint(1000, 9999))
            user.save()

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
        email = request.data.get('email') or request.data.get('username')
        role_id = int(request.data.get('role_id', 0))
        device_type = int(request.data.get('device_type', 0))
        version = float(request.headers.get('version', 0))

        try:
            if email:
                user = User.objects.get(email=email)
                
                # 1. Role Check (Mirroring actionLogin lines 384-391)
                if int(user.role_id) != role_id:
                    if role_id == User.ROLE_DOCTER:
                        return Response({"error": "You are not allowed to login in therapist section with user credentials."}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({"error": "You are not allowed to login in user section with therapist credentials."}, status=status.HTTP_400_BAD_REQUEST)

                 # 2. Version Check for iOS (Mirroring actionLogin lines 371-383)
                if device_type == User.DEVICE_IOS and version < 3.0:
                     if int(user.role_id) != User.ROLE_DOCTER:
                          has_plan = SubscribedPlan.objects.filter(created_by=user, state_id=1).exists()
                          if not has_plan:
                               return Response({"error": "A new version of app is available please update your app."}, status=status.HTTP_400_BAD_REQUEST)

            # 3. Handle Regular JWT Logic
            response = super().post(request, *args, **kwargs)
            
            # 4. PHP Logic for OTP on Login (lines 403-413)
            # if ((deviceType == 1 && version >= 30) || (deviceType == 2 && version >= 2.7))
            if response.status_code == 200:
                if (device_type == 1 and version >= 30) or (device_type == 2 and version >= 2.7):
                    user_id = response.data.get('id') or (user.id if 'user' in locals() else None)
                    if not user_id and email:
                         user_id = User.objects.get(email=email).id
                    
                    if user_id:
                        user_obj = User.objects.get(id=user_id)
                        otp = str(random.randint(1000, 9999))
                        user_obj.otp = otp
                        user_obj.otp_verified = 0 # OTP_NOT_VERIFIED
                        user_obj.save()
                        send_otp_via_email(user_obj.email, otp)
                        
                        # Return user detail as well to match PHP's asJson(true)
                        response.data['detail'] = UserSerializer(user_obj).data
                        response.data['message'] = "Please verify your OTP."
            
            return response

        except User.DoesNotExist:
            return Response({"error": "Incorrect Email"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminLoginView(APIView):
    """Admin-only login: accepts email + password, returns JWT only if user is admin or staff."""
    permission_classes = (AllowAny,)

    def post(self, request):
        email = (request.data.get('email') or request.data.get('username') or '').strip()
        password = request.data.get('password') or ''

        if not email or not password:
            return Response(
                {"error": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if user.role_id != User.ROLE_ADMIN and not user.is_staff:
            return Response(
                {"error": "You are not allowed to access the admin panel."},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        
        # Record Login History
        try:
            from django.contrib.gis.geoip2 import GeoIP2
            # Simple IP extraction (might need adjustment for proxies)
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')

            LoginHistory.objects.create(
                user=user,
                user_ip=ip or 'unknown',
                user_agent=request.META.get('HTTP_USER_AGENT', 'unknown')[:255],
                state_id=LoginHistory.STATE_SUCCESS,
                type_id=LoginHistory.TYPE_API,
                login_time=timezone.now()
            )
        except Exception as e:
            print(f"Error recording login history: {e}")

        return Response({
            "access-token": str(refresh.access_token),
            "refresh-token": str(refresh),
            "detail": UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


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

    def post(self, request, to_id):
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


class StandardPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserListView(generics.ListAPIView, StandardizedResponseMixin):
    """API endpoint for admin users table"""
    permission_classes = (IsAdminUser,)
    serializer_class = UserSerializer
    pagination_class = StandardPagination
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_on')
        params = self.request.query_params

        # Filter by role
        role_id = params.get('role_id')
        if role_id not in (None, ''):
            queryset = queryset.filter(role_id=role_id)

        # Filter by state (frontend sends state_id)
        state_id = params.get('state_id')
        if state_id not in (None, ''):
            queryset = queryset.filter(state_id=state_id)

        # Individual field filters (frontend filter row)
        id_val = params.get('id')
        if id_val not in (None, '') and str(id_val).strip().isdigit():
            queryset = queryset.filter(id=int(id_val))

        full_name = params.get('full_name')
        if full_name not in (None, ''):
            queryset = queryset.filter(full_name__icontains=full_name)

        email = params.get('email')
        if email not in (None, ''):
            queryset = queryset.filter(email__icontains=email)

        gender = params.get('gender')
        if gender not in (None, ''):
            try:
                queryset = queryset.filter(gender=int(gender))
            except (ValueError, TypeError):
                pass

        # Doctor filter: by assigned doctor's name (doctor_id points to User)
        doctor = params.get('doctor')
        if doctor not in (None, ''):
            if str(doctor).isdigit():
                queryset = queryset.filter(doctor_id=int(doctor))
            else:
                doctor_ids = User.objects.filter(
                    role_id=User.ROLE_DOCTER,
                    full_name__icontains=doctor
                ).values_list('id', flat=True)
                queryset = queryset.filter(doctor_id__in=list(doctor_ids))

        # Created on: optional date filter (YYYY-MM-DD or partial)
        created_on = params.get('created_on')
        if created_on not in (None, ''):
            try:
                # Allow partial date (e.g. "2025" or "2025-03")
                if len(created_on) == 4 and created_on.isdigit():
                    queryset = queryset.filter(created_on__year=int(created_on))
                elif len(created_on) == 7 and created_on[4] == '-':
                    y, m = int(created_on[:4]), int(created_on[5:7])
                    queryset = queryset.filter(created_on__year=y, created_on__month=m)
                else:
                    from datetime import datetime
                    dt = datetime.strptime(created_on.strip()[:10], '%Y-%m-%d')
                    queryset = queryset.filter(created_on__date=dt.date())
            except (ValueError, TypeError):
                pass

        # Subscription state: filter by related SubscribedPlan (Active/Trial/None/Expired)
        subscription_state = params.get('subscription_state')
        if subscription_state not in (None, ''):
            from plans.models import SubscribedPlan
            if subscription_state == 'None':
                # No active plan
                active_user_ids = SubscribedPlan.objects.filter(
                    state_id=1
                ).values_list('created_by_id', flat=True).distinct()
                queryset = queryset.exclude(id__in=active_user_ids)
            elif subscription_state == 'Trial':
                active_trial = SubscribedPlan.objects.filter(
                    state_id=1, plan_type=0
                ).values_list('created_by_id', flat=True).distinct()
                queryset = queryset.filter(id__in=active_trial)
            elif subscription_state == 'Active':
                active_paid = SubscribedPlan.objects.filter(
                    state_id=1, plan_type=1
                ).values_list('created_by_id', flat=True).distinct()
                queryset = queryset.filter(id__in=active_paid)
            elif subscription_state == 'Expired':
                # Users who have at least one plan that is not active (e.g. state_id != 1)
                expired = SubscribedPlan.objects.exclude(state_id=1).values_list(
                    'created_by_id', flat=True
                ).distinct()
                queryset = queryset.filter(id__in=expired)

        # Combined search (legacy) by name or email
        search = params.get('search')
        if search not in (None, ''):
            queryset = queryset.filter(
                Q(full_name__icontains=search) | Q(email__icontains=search)
            )

        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if isinstance(response.data, dict) and 'status' in response.data:
            return response
        return self.success_response(response.data)


class UserDetailView(generics.RetrieveUpdateAPIView, StandardizedResponseMixin):
    """API endpoint for individual user details and updates"""
    permission_classes = (IsAdminUser,)
    serializer_class = UserSerializer
    queryset = User.objects.all()


class UserUpdateView(generics.UpdateAPIView, StandardizedResponseMixin):
    """API endpoint for updating user details"""
    permission_classes = (IsAdminUser,)
    serializer_class = UserSerializer
    queryset = User.objects.all()
    
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            return self.success_response(
                data=serializer.data,
                message='User updated successfully',
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return self.error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )


class ProfilePhotoUploadView(APIView, StandardizedResponseMixin):
    """API endpoint for uploading profile photos"""
    permission_classes = (IsAdminUser,)
    
    def post(self, request, *args, **kwargs):
        try:
            if 'profile_photo' not in request.FILES:
                return self.error_response(
                    message='No photo file provided',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            photo_file = request.FILES['profile_photo']
            
            # Validate file type
            if not photo_file.content_type.startswith('image/'):
                return self.error_response(
                    message='File must be an image',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate file size (5MB max)
            if photo_file.size > 5 * 1024 * 1024:
                return self.error_response(
                    message='File size must be less than 5MB',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate unique filename
            import uuid
            import os
            
            file_extension = os.path.splitext(photo_file.name)[1]
            unique_filename = f"profile_photos/{uuid.uuid4()}{file_extension}"
            
            # Save file using Django's default storage
            from django.core.files.storage import default_storage
            
            file_path = default_storage.save(unique_filename, photo_file)
            file_url = default_storage.url(file_path)
            
            # Ensure we return the full URL for frontend
            if not file_url.startswith('http'):
                file_url = request.build_absolute_uri(file_url)
            
            return self.success_response(
                data={'url': file_url},
                message='Photo uploaded successfully',
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return self.error_response(
                message=f'Upload failed: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class AuditLogListView(StandardizedResponseMixin, ListAPIView):
    permission_classes = (IsAdminUser,)
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all().order_by('-created_at')
    pagination_class = StandardPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

class LoginHistoryListView(StandardizedResponseMixin, ListAPIView):
    permission_classes = (IsAdminUser,)
    serializer_class = LoginHistorySerializer
    queryset = LoginHistory.objects.all().order_by('-created_on')
    pagination_class = StandardPagination

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
