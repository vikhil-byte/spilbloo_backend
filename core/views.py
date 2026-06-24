from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.template.loader import render_to_string
from .models import (
    TherapistEarning, ContactForm, DoctorReason, Symptom, DoctorRequest,
    Feed, EmergencyResource, AgeGroup, AssignedTherapist, BestDoctor,
    VideoPlan, VideoCoupon, CouponUser, SubscribedVideo, UserSymptom,
    Setting, Disclaimer, PushNotification, File, Currency, RefundLog, 
    Invoice, HomeContent, LoginHistory, TherapistApplication
)
from .serializers import (
    TherapistEarningSerializer, ContactFormSerializer, DoctorReasonSerializer, 
    SymptomSerializer, DoctorRequestSerializer, FeedSerializer, 
    EmergencyResourceSerializer, AgeGroupSerializer, AssignedTherapistSerializer, 
    BestDoctorSerializer, VideoPlanSerializer, VideoCouponSerializer, 
    CouponUserSerializer, SubscribedVideoSerializer, UserSymptomSerializer,
    SettingSerializer, DisclaimerSerializer, PushNotificationSerializer, 
    FileSerializer, CurrencySerializer, RefundLogSerializer, InvoiceSerializer, 
    HomeContentSerializer, LoginHistorySerializer, TherapistApplicationSerializer
)

class TherapistEarningViewSet(viewsets.ModelViewSet):
    queryset = TherapistEarning.objects.all()
    serializer_class = TherapistEarningSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class ContactFormViewSet(viewsets.ModelViewSet):
    queryset = ContactForm.objects.all()
    serializer_class = ContactFormSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class DoctorReasonViewSet(viewsets.ModelViewSet):
    queryset = DoctorReason.objects.all()
    serializer_class = DoctorReasonSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class SymptomViewSet(viewsets.ModelViewSet):
    queryset = Symptom.objects.all()
    serializer_class = SymptomSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class DoctorRequestViewSet(viewsets.ModelViewSet):
    queryset = DoctorRequest.objects.all()
    serializer_class = DoctorRequestSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class FeedViewSet(viewsets.ModelViewSet):
    queryset = Feed.objects.all()
    serializer_class = FeedSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class EmergencyResourceViewSet(viewsets.ModelViewSet):
    queryset = EmergencyResource.objects.all()
    serializer_class = EmergencyResourceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class AgeGroupViewSet(viewsets.ModelViewSet):
    queryset = AgeGroup.objects.all()
    serializer_class = AgeGroupSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class AssignedTherapistViewSet(viewsets.ModelViewSet):
    queryset = AssignedTherapist.objects.all()
    serializer_class = AssignedTherapistSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class BestDoctorViewSet(viewsets.ModelViewSet):
    queryset = BestDoctor.objects.all()
    serializer_class = BestDoctorSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class VideoPlanViewSet(viewsets.ModelViewSet):
    queryset = VideoPlan.objects.all()
    serializer_class = VideoPlanSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class VideoCouponViewSet(viewsets.ModelViewSet):
    queryset = VideoCoupon.objects.all()
    serializer_class = VideoCouponSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class CouponUserViewSet(viewsets.ModelViewSet):
    queryset = CouponUser.objects.all()
    serializer_class = CouponUserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class SubscribedVideoViewSet(viewsets.ModelViewSet):
    queryset = SubscribedVideo.objects.all()
    serializer_class = SubscribedVideoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class UserSymptomViewSet(viewsets.ModelViewSet):
    queryset = UserSymptom.objects.all()
    serializer_class = UserSymptomSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class SettingViewSet(viewsets.ModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class DisclaimerViewSet(viewsets.ModelViewSet):
    queryset = Disclaimer.objects.all()
    serializer_class = DisclaimerSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class PushNotificationViewSet(viewsets.ModelViewSet):
    queryset = PushNotification.objects.all()
    serializer_class = PushNotificationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class RefundLogViewSet(viewsets.ModelViewSet):
    queryset = RefundLog.objects.all()
    serializer_class = RefundLogSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class HomeContentViewSet(viewsets.ModelViewSet):
    queryset = HomeContent.objects.all()
    serializer_class = HomeContentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class LoginHistoryViewSet(viewsets.ModelViewSet):
    queryset = LoginHistory.objects.all()
    serializer_class = LoginHistorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

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
            return []
        return [HasTherapistApplicationAccess()]

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
            filename = f"resume-{timestamp}-{resume_file_obj.name}"
            s3_key = upload_to_s3(resume_file_obj, filename)
            if s3_key:
                resume_key = s3_key
            else:
                from django.core.files.storage import default_storage
                saved_path = default_storage.save(f"resumes/{filename}", resume_file_obj)
                resume_key = saved_path
                
        if certs_file_obj:
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


