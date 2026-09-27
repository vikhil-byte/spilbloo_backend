import os
from django.db import migrations
from django.conf import settings


def seed_communication_defaults(apps, schema_editor):
    CommunicationGateway = apps.get_model('communication', 'CommunicationGateway')
    CommunicationTemplate = apps.get_model('communication', 'CommunicationTemplate')

    # Read dynamically from environment / settings so credentials are never committed to git
    msg91_auth_key = os.environ.get('MSG91_AUTH_KEY', getattr(settings, 'MSG91_AUTH_KEY', ''))
    msg91_sender_id = os.environ.get('MSG91_SENDER_ID', getattr(settings, 'MSG91_SENDER_ID', 'SPBLOO'))
    msg91_template_id = os.environ.get('MSG91_OTP_TEMPLATE_ID', getattr(settings, 'MSG91_OTP_TEMPLATE_ID', ''))
    default_from_email = os.environ.get('DEFAULT_FROM_EMAIL', getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@spilbloo.com'))

    # 1. Seed MSG91 SMS Gateway using env settings
    CommunicationGateway.objects.get_or_create(
        name="MSG91 Production SMS",
        channel="sms",
        defaults={
            "provider_type": "msg91",
            "is_active": True,
            "priority": 1,
            "credentials": {
                "auth_key": msg91_auth_key,
                "sender_id": msg91_sender_id,
                "template_id": msg91_template_id,
            }
        }
    )

    # 2. Seed Email Gateway using env settings
    CommunicationGateway.objects.get_or_create(
        name="Primary Email Gateway (SES/SMTP)",
        channel="email",
        defaults={
            "provider_type": "aws_ses",
            "is_active": True,
            "priority": 1,
            "credentials": {
                "from_email": default_from_email
            }
        }
    )

    # 3. Seed SMS OTP Template
    CommunicationTemplate.objects.get_or_create(
        event_code="AUTH_OTP",
        channel="sms",
        defaults={
            "title": "User Authentication Mobile OTP",
            "external_template_id": msg91_template_id,
            "sender_override": msg91_sender_id,
            "body_template": "Dear User, your Spilbloo verification OTP is ##number##. It is valid for 10 minutes. Please do not share this OTP with anyone. - SPILBLOO",
            "is_active": True
        }
    )

    # 4. Seed Email OTP Template
    CommunicationTemplate.objects.get_or_create(
        event_code="AUTH_EMAIL_OTP",
        channel="email",
        defaults={
            "title": "User Authentication Email OTP",
            "subject_template": "Spilbloo OTP Verification",
            "body_template": "Your OTP is {{otp}}. It is valid for 10 minutes.",
            "is_active": True
        }
    )


def rollback_communication_defaults(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('communication', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_communication_defaults, rollback_communication_defaults),
    ]
