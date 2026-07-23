from django.contrib import admin
from django.utils.html import format_html
from core.s3_utils import get_file_url
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

# Custom branding
admin.site.site_header = "Spilbloo Administration"
admin.site.site_title = "Spilbloo Admin Portal"
admin.site.index_title = "Welcome to Spilbloo Admin"

# Standard simple registrations
admin.site.register(DoctorReason)
admin.site.register(Symptom)
admin.site.register(DoctorRequest)
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
admin.site.register(File)
admin.site.register(Page)
admin.site.register(Category)
admin.site.register(NodeSubscriptionPlan)
admin.site.register(NodeUserSelectedTherapistPlan)
admin.site.register(HomeCard)
admin.site.register(DailyJournal)
admin.site.register(DailyCheckinQuestion)
admin.site.register(DailyCheckinAnswer)
admin.site.register(DailyCheckinQuestionAndAnswer)
admin.site.register(UserAppReview)
admin.site.register(ChatsHistory)

# Optimized Custom ModelAdmins
@admin.register(ApiAccessToken)
class ApiAccessTokenAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_info', 'device_type_badge', 'device_name',
        'device_token_preview', 'access_token_preview', 'created_on'
    )
    list_filter = ('device_type', 'created_on')
    search_fields = (
        'created_by__email', 'created_by__full_name', 'created_by__id',
        'device_token', 'access_token', 'device_name'
    )
    ordering = ('-id',)
    raw_id_fields = ('created_by',)
    actions = ['send_test_push_notification']

    @admin.display(description="User")
    def user_info(self, obj):
        if obj.created_by:
            return format_html(
                "<strong>{}</strong><br><small style='color: #666;'>ID: {} | {}</small>",
                obj.created_by.email or "No Email",
                obj.created_by.id,
                obj.created_by.full_name or ""
            )
        return "-"

    @admin.display(description="Device Type")
    def device_type_badge(self, obj):
        dtype = str(obj.device_type or "").strip()
        if dtype == "1":
            return format_html("<span style='background:#e0f2fe; color:#0369a1; padding:2px 8px; border-radius:12px; font-weight:bold;'>📱 iOS</span>")
        elif dtype == "2":
            return format_html("<span style='background:#dcfce7; color:#15803d; padding:2px 8px; border-radius:12px; font-weight:bold;'>🤖 Android</span>")
        return format_html("<span style='background:#f3f4f6; color:#374151; padding:2px 8px; border-radius:12px;'>Unknown ({})</span>", dtype)

    @admin.display(description="Device Token")
    def device_token_preview(self, obj):
        if not obj.device_token:
            return format_html("<span style='color:#ef4444;'>Empty</span>")
        tok = obj.device_token
        short_tok = f"{tok[:15]}...{tok[-10:]}" if len(tok) > 25 else tok
        return format_html("<code title='{}'>{}</code>", tok, short_tok)

    @admin.display(description="Access Token")
    def access_token_preview(self, obj):
        if not obj.access_token:
            return format_html("<span style='color:#9ca3af;'>None</span>")
        tok = obj.access_token
        short_tok = f"{tok[:15]}..." if len(tok) > 15 else tok
        return format_html("<code title='{}'>{}</code>", tok, short_tok)

    @admin.action(description="🚀 Send Test Push Notification to selected devices")
    def send_test_push_notification(self, request, queryset):
        from core.firebase import _send_fcm
        sent = 0
        failed = 0
        for record in queryset:
            if record.device_token:
                res = _send_fcm(record.device_token, "Admin Test Push", "This is a test notification sent from Admin Panel.")
                if res:
                    sent += 1
                else:
                    failed += 1
        self.message_user(
            request,
            f"Push dispatch complete: {sent} succeeded, {failed} failed."
        )

# Optimized Custom ModelAdmins
@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'model_type', 'model_id', 'created_on', 'get_content_preview')
    list_filter = ('model_type', 'created_on')
    search_fields = ('content', 'user_ip', 'user_agent')
    ordering = ('-created_on',)
    
    # Query optimizations for large tables
    show_full_result_count = False
    list_select_related = ('created_by',)
    raw_id_fields = ('created_by',)

    def get_content_preview(self, obj):
        if obj.content:
            return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
        return ""
    get_content_preview.short_description = 'Content Preview'

@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user_ip', 'user_agent', 'created_on')
    list_filter = ('created_on',)
    search_fields = ('user_ip', 'user_agent')
    ordering = ('-created_on',)
    
    # Query optimizations for large tables
    show_full_result_count = False
    list_select_related = ('user',)
    raw_id_fields = ('user',)

@admin.register(TherapistEarning)
class TherapistEarningAdmin(admin.ModelAdmin):
    list_display = ('id', 'therapist', 'patient', 'amount', 'date', 'state_id', 'created_on')
    list_filter = ('state_id', 'created_on')
    search_fields = ('amount',)
    ordering = ('-created_on',)
    
    # Query optimizations for large tables
    show_full_result_count = False
    list_select_related = ('therapist', 'patient')
    raw_id_fields = ('therapist', 'patient')

@admin.register(Faq)
class FaqAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'category', 'state_id', 'created_on')
    list_filter = ('category', 'state_id', 'created_on')
    search_fields = ('question', 'answer')
    ordering = ('-created_on',)
    list_select_related = ('category',)

@admin.register(ContactForm)
class ContactFormAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'contact_no', 'state_id', 'created_on')
    list_filter = ('state_id', 'created_on')
    search_fields = ('name', 'email', 'contact_no')
    ordering = ('-created_on',)

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'title', 'value', 'type_id', 'state_id')
    search_fields = ('key', 'title', 'value')

@admin.register(Disclaimer)
class DisclaimerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'state_id', 'created_on')

@admin.register(PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'role_type', 'state_id', 'created_on')
    list_filter = ('state_id', 'created_on')
    search_fields = ('title', 'description')

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

    def save_model(self, request, obj, form, change):
        old_state = None
        if change:
            try:
                old_state = TherapistApplication.objects.get(pk=obj.pk).state_id
            except TherapistApplication.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)
        if change and old_state != obj.state_id and obj.state_id in [
            TherapistApplication.STATE_ACCEPT,
            TherapistApplication.STATE_REJECT,
        ]:
            try:
                from core.tasks import send_therapist_application_status_email
                send_therapist_application_status_email.delay(obj.id, obj.state_id)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.exception("Failed to queue therapist application status email Celery task from admin: %s", str(e))

