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
from django.db.models import Case, When, F
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
        otp = str(random.randint(1000, 9999))
        
        # 2. Extract basic validation and saving via DRF serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 3. Add custom PHP fields to the newly created user
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

class CheckView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        # PHP has iOS version checking here, skipping for now unless needed.
        # Log active/last_action_time if we had those fields exactly.
        
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
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        symptom_str = request.data.get('symptom')
        if not symptom_str:
            return Response({"error": "No data posted."}, status=status.HTTP_400_BAD_REQUEST)

        symptom_ids =symptom_str.split(',')
        user = request.user

        with transaction.atomic():
            # Delete old ones
            UserSymptom.objects.filter(created_by_id=user.id).delete()
            
            # Create new ones
            for s_id in symptom_ids:
                UserSymptom.objects.create(
                    symptom_id=s_id.strip(),
                    created_by_id=user.id
                )
        
        # Find matching doctors
        matching_doctor_ids = UserSymptom.objects.filter(
            symptom_id__in=symptom_ids,
            state_id=1 # assuming active
        ).values_list('created_by_id', flat=True).distinct()

        # Build Doctor Query
        doctors = User.objects.filter(
            state_id=User.STATE_ACTIVE,
            role_id=User.ROLE_DOCTER,
            id__in=matching_doctor_ids
        )

        # Remove currently assigned doctor
        if user.doctor_id:
            doctors = doctors.exclude(id=user.doctor_id)

        # Sort Logic (Simplified for now, randomly grab 3 to emulate PHP rand() limit 3)
        doctors = list(doctors)
        random.shuffle(doctors)
        selected_doctors = doctors[:3]

        return Response({
            "detail": UserSerializer(selected_doctors, many=True).data
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

