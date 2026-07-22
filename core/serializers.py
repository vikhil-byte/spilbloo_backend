from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    TherapistEarning, ContactForm, DoctorReason, Symptom, DoctorRequest,
    Feed, EmergencyResource, AgeGroup, AssignedTherapist, BestDoctor,
    VideoPlan, VideoCoupon, CouponUser, SubscribedVideo, UserSymptom,
    Setting, Disclaimer, PushNotification, File, Currency, RefundLog,
    Invoice, HomeContent, LoginHistory, Page, Category, Faq, TherapistApplication,
    Language, TherapistInvite
)

class TherapistEarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = TherapistEarning
        fields = '__all__'

class ContactFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactForm
        fields = '__all__'

class DoctorReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorReason
        fields = '__all__'

class SymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symptom
        fields = '__all__'

class DoctorRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorRequest
        fields = '__all__'

class FeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feed
        fields = '__all__'

class EmergencyResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyResource
        fields = '__all__'

class AgeGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeGroup
        fields = '__all__'

class AssignedTherapistSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignedTherapist
        fields = '__all__'

class BestDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = BestDoctor
        fields = '__all__'

class VideoPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoPlan
        fields = '__all__'

class VideoCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoCoupon
        fields = '__all__'

class CouponUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponUser
        fields = '__all__'

class SubscribedVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscribedVideo
        fields = '__all__'

class UserSymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSymptom
        fields = '__all__'

class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = '__all__'

class DisclaimerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disclaimer
        fields = '__all__'

class PushNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushNotification
        fields = '__all__'

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = '__all__'

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = '__all__'

class RefundLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundLog
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'

class HomeContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeContent
        fields = '__all__'

class LoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginHistory
        fields = '__all__'

class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class FaqSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.title')
    class Meta:
        model = Faq
        fields = '__all__'

class TherapistApplicationSerializer(serializers.ModelSerializer):
    resume_file = serializers.FileField(required=True, write_only=True)
    certifications_file = serializers.FileField(required=False, allow_null=True, write_only=True)
    rci_file = serializers.FileField(required=False, allow_null=True, write_only=True)
    resume_file_path = serializers.CharField(source='resume_file', read_only=True)
    certifications_file_path = serializers.CharField(source='certifications_file', read_only=True)
    rci_file_path = serializers.CharField(source='rci_file', read_only=True)
    resume_url = serializers.SerializerMethodField()
    certifications_url = serializers.SerializerMethodField()
    rci_url = serializers.SerializerMethodField()

    # Frontend aliases and display mappings
    state = serializers.CharField(source='get_state_id_display', read_only=True)
    rciRegistered = serializers.CharField(source='rci_registered', read_only=True)
    employmentStatus = serializers.CharField(source='employment_status', read_only=True)
    hoursPerWeek = serializers.CharField(source='hours_available', read_only=True)
    daysPerWeek = serializers.CharField(source='days_available', read_only=True)
    whyInterested = serializers.CharField(source='motivation', read_only=True)
    distressCase = serializers.CharField(source='distress_situation', read_only=True)
    linkedin = serializers.CharField(source='linkedin_profile', read_only=True)

    class Meta:
        model = TherapistApplication
        fields = '__all__'

    def get_resume_url(self, obj):
        from core.s3_utils import get_file_url
        return get_file_url(obj.resume_file)

    def get_certifications_url(self, obj):
        from core.s3_utils import get_file_url
        return get_file_url(obj.certifications_file)

    def get_rci_url(self, obj):
        from core.s3_utils import get_file_url
        return get_file_url(obj.rci_file)


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ('id', 'name', 'code', 'state_id')


class TherapistInviteSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = TherapistInvite
        fields = ('id', 'email', 'token', 'expires_at', 'used', 'status', 'created_on', 'created_by')
        read_only_fields = ('id', 'token', 'expires_at', 'used', 'status', 'created_on', 'created_by')

    def get_status(self, obj):
        if obj.used:
            return 'used'
        if obj.is_expired():
            return 'expired'
        return 'pending'


class TherapistOnboardingSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=50, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    contact_no = serializers.CharField(max_length=50, required=True)
    date_of_birth = serializers.DateField(required=True, allow_null=True)
    gender = serializers.ChoiceField(choices=['male', 'female', 'other', 'prefer_not_to_say'], required=False, default='')
    city = serializers.CharField(max_length=100, required=False, default='')
    country = serializers.CharField(max_length=100, required=False, default='')
    about_me = serializers.CharField(required=False, default='')
    experience = serializers.IntegerField(required=True, min_value=0, max_value=50)
    sessions_completed = serializers.IntegerField(required=True, min_value=0)
    language_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        min_length=1,
    )
    symptoms = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )

    def validate_password(self, value):
        """Enforce strong password: uppercase, lowercase, digit, special char."""
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter."
            )
        if not any(c.islower() for c in value):
            raise serializers.ValidationError(
                "Password must contain at least one lowercase letter."
            )
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError(
                "Password must contain at least one digit."
            )
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in value):
            raise serializers.ValidationError(
                "Password must contain at least one special character."
            )
        return value

    def validate_language_id(self, value):
        if not Language.objects.filter(id=value, state_id=Language.STATE_ACTIVE).exists():
            raise serializers.ValidationError("Invalid language selection.")
        return value

    def validate_symptoms(self, value):
        """Ensure all symptom IDs are valid."""
        for sid in value:
            if not Symptom.objects.filter(id=sid, state_id=Symptom.STATE_ACTIVE).exists():
                raise serializers.ValidationError(f"Invalid symptom ID: {sid}")
        return value


