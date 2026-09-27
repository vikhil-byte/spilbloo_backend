from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class CommunicationGateway(models.Model):
    CHANNEL_SMS = 'sms'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_EMAIL = 'email'
    CHANNEL_PUSH = 'push'

    CHANNEL_CHOICES = (
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_WHATSAPP, 'WhatsApp'),
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_PUSH, 'Push Notification'),
    )

    PROVIDER_MSG91 = 'msg91'
    PROVIDER_WHATSAPP_CLOUD = 'whatsapp_cloud'
    PROVIDER_AWS_SES = 'aws_ses'
    PROVIDER_SMTP = 'smtp'
    PROVIDER_AWS_SNS = 'aws_sns'
    PROVIDER_FIREBASE = 'firebase'
    PROVIDER_CONSOLE = 'console'

    PROVIDER_CHOICES = (
        (PROVIDER_MSG91, 'MSG91 (SMS & OTP)'),
        (PROVIDER_WHATSAPP_CLOUD, 'Meta WhatsApp Cloud API'),
        (PROVIDER_AWS_SES, 'AWS SES (Email)'),
        (PROVIDER_SMTP, 'SMTP (Email)'),
        (PROVIDER_AWS_SNS, 'AWS SNS (SMS)'),
        (PROVIDER_FIREBASE, 'Firebase Cloud Messaging (FCM)'),
        (PROVIDER_CONSOLE, 'Console / Mock Testing'),
    )

    name = models.CharField(max_length=128, help_text="Friendly name e.g. MSG91 Production")
    channel = models.CharField(max_length=32, choices=CHANNEL_CHOICES, db_index=True)
    provider_type = models.CharField(max_length=64, choices=PROVIDER_CHOICES)
    is_active = models.BooleanField(default=True, db_index=True)
    priority = models.PositiveIntegerField(default=1, help_text="Priority ordering (1 is highest priority)")
    credentials = models.JSONField(
        default=dict,
        blank=True,
        help_text="Gateway configuration JSON (e.g. auth_key, sender_id, api_token, timeout, etc.)"
    )
    fallback_gateway = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fallback_for',
        help_text="Optional fallback gateway if this gateway encounters an error"
    )
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_communication_gateway'
        ordering = ['channel', 'priority', '-id']
        verbose_name = 'Gateway / Provider'
        verbose_name_plural = 'Gateways & Providers'

    def __str__(self):
        status_label = "Active" if self.is_active else "Inactive"
        return f"{self.name} [{self.get_channel_display()}] ({status_label})"


class CommunicationTemplate(models.Model):
    CHANNEL_CHOICES = CommunicationGateway.CHANNEL_CHOICES

    event_code = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Event trigger key e.g. AUTH_OTP, BOOKING_CONFIRMATION, SESSION_REMINDER"
    )
    channel = models.CharField(max_length=32, choices=CHANNEL_CHOICES, db_index=True)
    title = models.CharField(max_length=128, help_text="Template title for administrative reference")
    external_template_id = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="Gateway/DLT Template ID (e.g. MSG91 Flow/Template ID or WhatsApp template name)"
    )
    sender_override = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="Custom Sender ID/Header (e.g. SPBLOO) overriding gateway default"
    )
    subject_template = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        help_text="Email Subject line or Push notification title. Supports {{variables}}."
    )
    body_template = models.TextField(
        help_text="Message body. Supports {{variable}} or ##variable## dynamic placeholders."
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_communication_template'
        unique_together = ('event_code', 'channel')
        verbose_name = 'Message Template'
        verbose_name_plural = 'Message Templates'

    def __str__(self):
        return f"{self.event_code} - {self.get_channel_display()} ({self.title})"


class CommunicationLog(models.Model):
    STATUS_QUEUED = 'queued'
    STATUS_SENT = 'sent'
    STATUS_DELIVERED = 'delivered'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = (
        (STATUS_QUEUED, 'Queued'),
        (STATUS_SENT, 'Sent / Dispatched'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_FAILED, 'Failed'),
    )

    recipient = models.CharField(max_length=256, db_index=True, help_text="Recipient phone number, email address, or device token")
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='communication_logs'
    )
    channel = models.CharField(max_length=32, choices=CommunicationGateway.CHANNEL_CHOICES, db_index=True)
    event_code = models.CharField(max_length=64, db_index=True)
    gateway = models.ForeignKey(
        CommunicationGateway,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    template = models.ForeignKey(
        CommunicationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    rendered_subject = models.CharField(max_length=256, blank=True, null=True)
    rendered_body = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    external_message_id = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        db_index=True,
        help_text="Gateway transaction ID (e.g. MSG91 request_id, SES MessageId)"
    )
    request_payload = models.JSONField(default=dict, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)
    created_on = models.DateTimeField(default=timezone.now, db_index=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_communication_log'
        ordering = ['-created_on']
        verbose_name = 'Delivery Log'
        verbose_name_plural = 'Delivery Logs'

    def __str__(self):
        return f"[{self.get_channel_display()}] To: {self.recipient} | Event: {self.event_code} | Status: {self.status}"
