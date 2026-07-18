from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, BasePermission, SAFE_METHODS, AllowAny, IsAdminUser
from rest_framework.views import APIView
from django.template.loader import render_to_string
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
import os
import uuid
import json
import time
import logging
from rest_framework.exceptions import ValidationError

User = get_user_model()
logger = logging.getLogger(__name__)

class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_staff

class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
            
        owner_attrs = ['created_by', 'created_by_id', 'user', 'user_id', 'therapist', 'therapist_id', 'patient', 'patient_id', 'doctor', 'doctor_id']
        for attr in owner_attrs:
            val = getattr(obj, attr, None)
            if val == user or (isinstance(val, int) and val == user.id):
                return True
        return False

def validate_file_extension(file_obj, allowed_extensions):
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f"File extension '{ext}' is not allowed. Allowed types: {', '.join(allowed_extensions)}")
from .models import (
    TherapistEarning, ContactForm, DoctorReason, Symptom, DoctorRequest,
    Feed, EmergencyResource, AgeGroup, AssignedTherapist, BestDoctor,
    VideoPlan, VideoCoupon, CouponUser, SubscribedVideo, UserSymptom,
    Setting, Disclaimer, PushNotification, File, Currency, RefundLog,
    Invoice, HomeContent, LoginHistory, TherapistApplication,
    Language, TherapistInvite
)
from .serializers import (
    TherapistEarningSerializer, ContactFormSerializer, DoctorReasonSerializer,
    SymptomSerializer, DoctorRequestSerializer, FeedSerializer,
    EmergencyResourceSerializer, AgeGroupSerializer, AssignedTherapistSerializer,
    BestDoctorSerializer, VideoPlanSerializer, VideoCouponSerializer,
    CouponUserSerializer, SubscribedVideoSerializer, UserSymptomSerializer,
    SettingSerializer, DisclaimerSerializer, PushNotificationSerializer,
    FileSerializer, CurrencySerializer, RefundLogSerializer, InvoiceSerializer,
    HomeContentSerializer, LoginHistorySerializer, TherapistApplicationSerializer,
    LanguageSerializer, TherapistInviteSerializer, TherapistOnboardingSerializer
)

class TherapistEarningViewSet(viewsets.ModelViewSet):
    queryset = TherapistEarning.objects.all()
    serializer_class = TherapistEarningSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return TherapistEarning.objects.none()
        if user.is_staff:
            return TherapistEarning.objects.all()
        return TherapistEarning.objects.filter(Q(therapist=user) | Q(patient=user) | Q(created_by=user))

class ContactFormViewSet(viewsets.ModelViewSet):
    queryset = ContactForm.objects.all()
    serializer_class = ContactFormSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAdminUser()]

class DoctorReasonViewSet(viewsets.ModelViewSet):
    queryset = DoctorReason.objects.all()
    serializer_class = DoctorReasonSerializer
    permission_classes = [IsAdminOrReadOnly]

class SymptomViewSet(viewsets.ModelViewSet):
    queryset = Symptom.objects.all()
    serializer_class = SymptomSerializer
    permission_classes = [IsAdminOrReadOnly]

class DoctorRequestViewSet(viewsets.ModelViewSet):
    queryset = DoctorRequest.objects.all()
    serializer_class = DoctorRequestSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return DoctorRequest.objects.none()
        if user.is_staff:
            return DoctorRequest.objects.all()
        return DoctorRequest.objects.filter(Q(created_by=user) | Q(doctor=user) | Q(patient=user))

class FeedViewSet(viewsets.ModelViewSet):
    queryset = Feed.objects.all()
    serializer_class = FeedSerializer
    permission_classes = [IsAdminOrReadOnly]

class EmergencyResourceViewSet(viewsets.ModelViewSet):
    queryset = EmergencyResource.objects.all()
    serializer_class = EmergencyResourceSerializer
    permission_classes = [IsAdminOrReadOnly]

class AgeGroupViewSet(viewsets.ModelViewSet):
    queryset = AgeGroup.objects.all()
    serializer_class = AgeGroupSerializer
    permission_classes = [IsAdminOrReadOnly]

class AssignedTherapistViewSet(viewsets.ModelViewSet):
    queryset = AssignedTherapist.objects.all()
    serializer_class = AssignedTherapistSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return AssignedTherapist.objects.none()
        if user.is_staff:
            return AssignedTherapist.objects.all()
        return AssignedTherapist.objects.filter(Q(created_by=user) | Q(doctor=user) | Q(patient=user))

class BestDoctorViewSet(viewsets.ModelViewSet):
    queryset = BestDoctor.objects.all()
    serializer_class = BestDoctorSerializer
    permission_classes = [IsAdminOrReadOnly]

class VideoPlanViewSet(viewsets.ModelViewSet):
    queryset = VideoPlan.objects.all()
    serializer_class = VideoPlanSerializer
    permission_classes = [IsAdminOrReadOnly]

class VideoCouponViewSet(viewsets.ModelViewSet):
    queryset = VideoCoupon.objects.all()
    serializer_class = VideoCouponSerializer
    permission_classes = [IsAdminOrReadOnly]

class CouponUserViewSet(viewsets.ModelViewSet):
    queryset = CouponUser.objects.all()
    serializer_class = CouponUserSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return CouponUser.objects.none()
        if user.is_staff:
            return CouponUser.objects.all()
          
        return CouponUser.objects.filter(created_by=user)

class SubscribedVideoViewSet(viewsets.ModelViewSet):
    queryset = SubscribedVideo.objects.all()
    serializer_class = SubscribedVideoSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return SubscribedVideo.objects.none()
        if user.is_staff:
            return SubscribedVideo.objects.all()
        return SubscribedVideo.objects.filter(created_by=user)

class UserSymptomViewSet(viewsets.ModelViewSet):
    queryset = UserSymptom.objects.all()
    serializer_class = UserSymptomSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return UserSymptom.objects.none()
        if user.is_staff:
            return UserSymptom.objects.all()
        return UserSymptom.objects.filter(created_by=user)

class SettingViewSet(viewsets.ModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAdminOrReadOnly]

class DisclaimerViewSet(viewsets.ModelViewSet):
    queryset = Disclaimer.objects.all()
    serializer_class = DisclaimerSerializer
    permission_classes = [IsAdminOrReadOnly]

class PushNotificationViewSet(viewsets.ModelViewSet):
    queryset = PushNotification.objects.all()
    serializer_class = PushNotificationSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return PushNotification.objects.none()
        if user.is_staff:
            return PushNotification.objects.all()
        return PushNotification.objects.filter(Q(created_by=user) | Q(user=user))

class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return File.objects.none()
        if user.is_staff:
            return File.objects.all()
        return File.objects.filter(created_by=user)

class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [IsAdminOrReadOnly]

class RefundLogViewSet(viewsets.ModelViewSet):
    queryset = RefundLog.objects.all()
    serializer_class = RefundLogSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return RefundLog.objects.none()
        if user.is_staff:
            return RefundLog.objects.all()
        return RefundLog.objects.filter(Q(created_by=user) | Q(doctor=user))

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Invoice.objects.none()
        if user.is_staff:
            return Invoice.objects.all()
        return Invoice.objects.filter(Q(created_by=user) | Q(user=user))

class HomeContentViewSet(viewsets.ModelViewSet):
    queryset = HomeContent.objects.all()
    serializer_class = HomeContentSerializer
    permission_classes = [IsAdminOrReadOnly]

class LoginHistoryViewSet(viewsets.ModelViewSet):
    queryset = LoginHistory.objects.all()
    serializer_class = LoginHistorySerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return LoginHistory.objects.none()
        if user.is_staff:
            return LoginHistory.objects.all()
        return LoginHistory.objects.filter(user=user)

from rest_framework.permissions import BasePermission

class HasTherapistApplicationAccess(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or 
            request.user.has_perm('core.view_therapistapplication')
        )

class TherapistApplicationViewSet(viewsets.ModelViewSet):
    queryset = TherapistApplication.objects.all()
    serializer_class = TherapistApplicationSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [HasTherapistApplicationAccess()]

    @action(detail=True, methods=['post'], url_path='send-schedule-email')
    def send_schedule_email(self, request, pk=None):
        instance = self.get_object()
        if instance.state_id != TherapistApplication.STATE_ACCEPT:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("This candidate has not been accepted.")
        
        try:
            from core.tasks import send_therapist_application_schedule_email
            send_therapist_application_schedule_email.delay(instance.id)
            return Response({"detail": "Schedule interview email has been queued."}, status=200)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Failed to queue schedule interview email Celery task: %s", str(e))
            return Response({"detail": "Failed to queue schedule interview email."}, status=500)

    def perform_update(self, serializer):
        instance = self.get_object()
        old_state = instance.state_id
        updated_instance = serializer.save()
        new_state = updated_instance.state_id
        
        if old_state != new_state and new_state in [
            TherapistApplication.STATE_ACCEPT,
            TherapistApplication.STATE_REJECT,
        ]:
            try:
                from core.tasks import send_therapist_application_status_email
                send_therapist_application_status_email.delay(updated_instance.id, new_state)
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Queued therapist application status email (state: %s) for ID: %s", new_state, updated_instance.id)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.exception("Failed to queue therapist application status email Celery task: %s", str(e))

    def perform_create(self, serializer):
        email = serializer.validated_data.get('email')
        if TherapistApplication.objects.filter(email=email).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"email": ["An application with this email address has already been submitted."]})

        request = self.request
        resume_file_obj = request.FILES.get('resume_file')
        certs_file_obj = request.FILES.get('certifications_file')
        
        resume_key = ""
        certs_key = ""
        
        from core.s3_utils import upload_to_s3
        import time
        
        timestamp = int(time.time())
        if resume_file_obj:
            validate_file_extension(resume_file_obj, {'.pdf', '.doc', '.docx'})
            filename = f"resume-{timestamp}-{resume_file_obj.name}"
            s3_key = upload_to_s3(resume_file_obj, filename)
            if s3_key:
                resume_key = s3_key
            else:
                from django.core.files.storage import default_storage
                saved_path = default_storage.save(f"resumes/{filename}", resume_file_obj)
                resume_key = saved_path
                
        if certs_file_obj:
            validate_file_extension(certs_file_obj, {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'})
            filename = f"certs-{timestamp}-{certs_file_obj.name}"
            s3_key = upload_to_s3(certs_file_obj, filename)
            if s3_key:
                certs_key = s3_key
            else:
                from django.core.files.storage import default_storage
                saved_path = default_storage.save(f"certifications/{filename}", certs_file_obj)
                certs_key = saved_path

        from django.utils import timezone
        created_by_user = request.user if request.user and request.user.is_authenticated else None
        instance = serializer.save(
            resume_file=resume_key,
            certifications_file=certs_key,
            consent_given=True,
            consent_date_time=timezone.now(),
            created_by=created_by_user
        )
        try:
            from core.tasks import send_therapist_application_emails
            send_therapist_application_emails.delay(instance.id)
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Queued therapist application emails Celery task for ID: %s", instance.id)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Failed to queue therapist application emails Celery task: %s", str(e))


class LanguageViewSet(viewsets.ModelViewSet):
    queryset = Language.objects.all().order_by('name')
    serializer_class = LanguageSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAdminUser()]


class TherapistInviteViewSet(viewsets.ModelViewSet):
    queryset = TherapistInvite.objects.all().order_by('-created_on')
    serializer_class = TherapistInviteSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        email = serializer.validated_data['email']
        token = uuid.uuid4()

        # Default expiry: 7 days from now
        from datetime import timedelta
        expires_at = timezone.now() + timedelta(days=7)

        invite = TherapistInvite.objects.create(
            email=email,
            token=token,
            expires_at=expires_at,
            created_by=self.request.user,
        )
        serializer.instance = invite

        # Send invite email
        try:
            onboarding_url = f"{getattr(settings, 'SITE_URL', '')}/therapist-onboarding?token={token}"
            subject = "You're Invited to Join Spilbloo as a Therapist"
            html_message = render_to_string('emails/therapist_invite.html', {
                'onboarding_url': onboarding_url,
                'expires_at': expires_at.strftime('%B %d, %Y at %I:%M %p'),
            })
            from core.email_service import get_email_client
            get_email_client().send_email(
                subject=subject,
                body=f"Complete your therapist onboarding at: {onboarding_url}",
                to_email=email,
                html_body=html_message,
            )
            logger.info("Therapist invite sent to %s", email)
        except Exception:
            logger.exception("Failed to send therapist invite email to %s", email)

    def get_queryset(self):
        return TherapistInvite.objects.all().order_by('-created_on')


class TherapistOnboardingView(APIView):
    permission_classes = [AllowAny]

    def _validate_token(self, request):
        """Validate the invite token from query params. Returns invite or raises."""
        token_str = request.query_params.get('token') or request.data.get('token', '')
        if not token_str:
            raise ValidationError({"token": ["Invite token is required."]})
        try:
            invite = TherapistInvite.objects.get(token=token_str)
        except TherapistInvite.DoesNotExist:
            raise ValidationError({"token": ["Invalid invite token."]})
        if invite.used:
            raise ValidationError({"token": ["This invite has already been used."]})
        if invite.is_expired():
            raise ValidationError({"token": ["This invite link has expired. Please request a new one."]})
        return invite

    def get(self, request):
        """Check if invite token is valid — used by frontend to pre-fill email."""
        try:
            invite = self._validate_token(request)
            return Response({
                'valid': True,
                'email': invite.email,
                'expires_at': invite.expires_at.isoformat(),
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({'valid': False, 'detail': e.detail}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """Complete therapist onboarding: create User + TherapistApplication."""
        invite = None
        try:
            invite = self._validate_token(request)

            serializer = TherapistOnboardingSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            # Email must match invite
            if data['email'].lower() != invite.email.lower():
                raise ValidationError(
                    {"email": ["Email does not match the invited email address."]}
                )

            with transaction.atomic():
                # Create User account
                user = User.objects.create_user(
                    email=data['email'],
                    password=data['password'],
                    full_name=data['full_name'],
                    role_id=User.ROLE_DOCTER,
                    state_id=User.STATE_ACTIVE,
                    experience=data['experience'],
                    sessions_completed=data['sessions_completed'],
                    email_verified=1,
                )

                # Set language
                try:
                    language_obj = Language.objects.get(id=data['language_id'])
                    user.language = language_obj.name
                    user.save(update_fields=['language'])
                except Language.DoesNotExist:
                    pass

                # Create UserSymptom associations
                for symptom_id in data.get('symptoms', []):
                    UserSymptom.objects.create(
                        symptom_id=symptom_id,
                        created_by=user,
                    )

                # Handle file uploads
                from core.s3_utils import upload_to_s3
                profile_key = ""
                resume_key = ""
                certs_key = ""

                profile_file = request.FILES.get('profile_image')
                if profile_file:
                    filename = f"profile-{int(time.time())}-{profile_file.name}"
                    s3_key = upload_to_s3(profile_file, filename)
                    if s3_key:
                        profile_key = s3_key
                    user.profile_file = profile_key
                    user.save(update_fields=['profile_file'])

                resume_file = request.FILES.get('resume_file')
                if resume_file:
                    ext = os.path.splitext(resume_file.name)[1].lower()
                    if ext not in {'.pdf', '.doc', '.docx'}:
                        raise ValidationError(
                            {"resume_file": ["Allowed file types: .pdf, .doc, .docx"]}
                        )
                    filename = f"resume-{int(time.time())}-{resume_file.name}"
                    s3_key = upload_to_s3(resume_file, filename)
                    if s3_key:
                        resume_key = s3_key

                certs_file = request.FILES.get('certifications_file')
                if certs_file:
                    ext = os.path.splitext(certs_file.name)[1].lower()
                    if ext not in {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'}:
                        raise ValidationError(
                            {"certifications_file": ["Allowed file types: .pdf, .doc, .docx, .jpg, .jpeg, .png"]}
                        )
                    filename = f"certs-{int(time.time())}-{certs_file.name}"
                    s3_key = upload_to_s3(certs_file, filename)
                    if s3_key:
                        certs_key = s3_key

                # Create TherapistApplication record
                TherapistApplication.objects.create(
                    name=data['full_name'],
                    email=data['email'],
                    experience=str(data['experience']),
                    qualification='',
                    symptoms=json.dumps(data.get('symptoms', [])),
                    language_id=data['language_id'],
                    resume_file=resume_key,
                    certifications_file=certs_key or None,
                    consent_given=True,
                    consent_date_time=timezone.now(),
                    state_id=TherapistApplication.STATE_ADD,
                    created_by=user,
                )

                # Mark invite as used
                invite.used = True
                invite.save(update_fields=['used'])

            return Response(
                {
                    'message': 'Onboarding completed successfully.',
                    'user_id': user.id,
                    'email': user.email,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response({'detail': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Therapist onboarding failed for email=%s",
                             getattr(invite, 'email', None))
            return Response(
                {'detail': 'An error occurred during onboarding. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


