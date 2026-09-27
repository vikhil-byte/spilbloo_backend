from django.contrib import admin
from django.contrib import messages
from .models import CommunicationGateway, CommunicationTemplate, CommunicationLog
from .services.dispatcher import CommunicationService


@admin.register(CommunicationGateway)
class CommunicationGatewayAdmin(admin.ModelAdmin):
    list_display = ('name', 'channel', 'provider_type', 'priority', 'is_active', 'fallback_gateway', 'updated_on')
    list_filter = ('channel', 'provider_type', 'is_active')
    search_fields = ('name',)
    ordering = ('channel', 'priority', '-id')
    actions = ['test_gateway_connection']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'channel', 'provider_type', 'is_active', 'priority')
        }),
        ('Credentials & Configuration', {
            'description': 'Configure API keys, sender headers, and endpoints (stored as JSON). Example: {"auth_key": "...", "sender_id": "SPBLOO"}',
            'fields': ('credentials',)
        }),
        ('Failover / Fallback', {
            'fields': ('fallback_gateway',)
        }),
    )

    @admin.action(description="Test Gateway connection / mock send")
    def test_gateway_connection(self, request, queryset):
        success_count = 0
        for gateway in queryset:
            test_recipient = "919999999999" if gateway.channel in ('sms', 'whatsapp') else "test@example.com"
            ok, _ = CommunicationService.send(
                event_code="GATEWAY_TEST",
                recipient=test_recipient,
                context={"otp": "1234", "message": "Test ping"},
                channel=gateway.channel,
                override_gateway=gateway
            )
            if ok:
                success_count += 1
        messages.success(request, f"{success_count} gateway test dispatch(es) executed successfully.")


@admin.register(CommunicationTemplate)
class CommunicationTemplateAdmin(admin.ModelAdmin):
    list_display = ('event_code', 'channel', 'title', 'external_template_id', 'sender_override', 'is_active', 'updated_on')
    list_filter = ('channel', 'is_active', 'event_code')
    search_fields = ('event_code', 'title', 'external_template_id', 'body_template')
    ordering = ('event_code', 'channel')

    fieldsets = (
        ('Identification', {
            'fields': ('event_code', 'channel', 'title', 'is_active')
        }),
        ('Gateway Linking', {
            'description': 'Specify gateway-level template ID (e.g. MSG91 Template ID or WhatsApp template name) and custom sender header.',
            'fields': ('external_template_id', 'sender_override')
        }),
        ('Message Content', {
            'description': 'Use {{variable}} or ##variable## placeholders to dynamically insert variables (e.g. {{otp}}, {{user_name}}).',
            'fields': ('subject_template', 'body_template')
        }),
    )


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'channel', 'event_code', 'gateway', 'status', 'external_message_id', 'created_on')
    list_filter = ('channel', 'status', 'event_code', 'created_on')
    search_fields = ('recipient', 'event_code', 'external_message_id', 'rendered_body', 'error_message')
    readonly_fields = (
        'recipient', 'user', 'channel', 'event_code', 'gateway', 'template',
        'rendered_subject', 'rendered_body', 'status', 'external_message_id',
        'request_payload', 'gateway_response', 'error_message', 'retry_count',
        'created_on', 'updated_on'
    )
    ordering = ('-created_on',)
    actions = ['retry_selected_communications']

    @admin.action(description="Retry selected failed/queued communications")
    def retry_selected_communications(self, request, queryset):
        retried_count = 0
        success_count = 0
        for log in queryset:
            payload = log.request_payload.get("context", {})
            ok, new_log = CommunicationService.send(
                event_code=log.event_code,
                recipient=log.recipient,
                context=payload,
                channel=log.channel,
                user=log.user
            )
            log.retry_count += 1
            log.save(update_fields=['retry_count'])
            retried_count += 1
            if ok:
                success_count += 1

        messages.info(request, f"Retried {retried_count} communication(s): {success_count} succeeded.")
