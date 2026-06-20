from django.contrib import admin
from .models import (
    TherapistEarning, ContactForm, DoctorReason, Symptom, DoctorRequest,
    Feed, EmergencyResource, AgeGroup, AssignedTherapist, BestDoctor,
    VideoPlan, VideoCoupon, CouponUser, SubscribedVideo, UserSymptom,
    Currency, RefundLog, Invoice, HomeContent, LoginHistory, TherapistApplication,
    Setting, Disclaimer, PushNotification, File, Page, Category, Faq,
    NodeSubscriptionPlan, NodeUserSelectedTherapistPlan, HomeCard, DailyJournal,
    DailyCheckinQuestion, DailyCheckinAnswer, DailyCheckinQuestionAndAnswer,
    UserAppReview, ChatsHistory, ApiAccessToken
)

# Register your models here.
admin.site.register(TherapistEarning)
admin.site.register(ContactForm)
admin.site.register(DoctorReason)
admin.site.register(Symptom)
admin.site.register(DoctorRequest)
admin.site.register(Feed)
admin.site.register(EmergencyResource)
admin.site.register(AgeGroup)
admin.site.register(AssignedTherapist)
admin.site.register(BestDoctor)
admin.site.register(VideoPlan)
admin.site.register(VideoCoupon)
admin.site.register(CouponUser)
admin.site.register(SubscribedVideo)
admin.site.register(UserSymptom)
admin.site.register(Currency)
admin.site.register(RefundLog)
admin.site.register(Invoice)
admin.site.register(HomeContent)
admin.site.register(LoginHistory)
admin.site.register(Setting)
admin.site.register(Disclaimer)
admin.site.register(PushNotification)
admin.site.register(File)
admin.site.register(Page)
admin.site.register(Category)
admin.site.register(Faq)
admin.site.register(NodeSubscriptionPlan)
admin.site.register(NodeUserSelectedTherapistPlan)
admin.site.register(HomeCard)
admin.site.register(DailyJournal)
admin.site.register(DailyCheckinQuestion)
admin.site.register(DailyCheckinAnswer)
admin.site.register(DailyCheckinQuestionAndAnswer)
admin.site.register(UserAppReview)
admin.site.register(ChatsHistory)
admin.site.register(ApiAccessToken)
from django.utils.html import format_html
from core.s3_utils import get_file_url

@admin.register(TherapistApplication)
class TherapistApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'contact_no', 'qualification', 'rci_registered', 'state_id', 'consent_given', 'consent_date_time', 'created_on', 'view_resume', 'view_certs')
    list_filter = ('state_id', 'rci_registered', 'qualification', 'consent_given', 'created_on')
    search_fields = ('name', 'email', 'contact_no', 'address', 'qualification')
    ordering = ('-created_on',)
    
    readonly_fields = ('created_on', 'consent_date_time')
    
    fieldsets = (
        ('Personal Info', {
            'fields': ('name', 'email', 'contact_no', 'address', 'linkedin_profile')
        }),
        ('Professional Credentials', {
            'fields': ('experience', 'qualification', 'rci_registered', 'employment_status', 'modalities')
        }),
        ('Availability & Details', {
            'fields': ('hours_available', 'days_available', 'motivation', 'distress_situation')
        }),
        ('Attachments', {
            'fields': ('resume_file', 'certifications_file')
        }),
        ('Status', {
            'fields': ('state_id', 'type_id', 'consent_given', 'consent_date_time', 'created_on', 'created_by')
        }),
    )

    def view_resume(self, obj):
        url = get_file_url(obj.resume_file)
        if url:
            return format_html('<a href="{}" target="_blank">📄 Resume</a>', url)
        return "-"
    view_resume.short_description = 'Resume'

    def view_certs(self, obj):
        url = get_file_url(obj.certifications_file)
        if url:
            return format_html('<a href="{}" target="_blank">📜 Certs</a>', url)
        return "-"
    view_certs.short_description = 'Certifications'

