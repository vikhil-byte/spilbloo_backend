from django.core.mail import send_mail
from django.conf import settings
from .base import BaseEmailAdapter
import logging

logger = logging.getLogger(__name__)

class SMTPEmailAdapter(BaseEmailAdapter):
    """
    SMTP email client using Django's standard mail functions.
    Compatible with Gmail SMTP, custom SMTP servers, or AWS SES SMTP credentials.
    """
    def send_email(self, subject: str, body: str, to_email: str, from_email: str = None) -> bool:
        if not from_email:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")
        
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=from_email,
                recipient_list=[to_email],
                fail_silently=False
            )
            return True
        except Exception as e:
            logger.exception("SMTP Email sending failed to %s: %s", to_email, str(e))
            return False
