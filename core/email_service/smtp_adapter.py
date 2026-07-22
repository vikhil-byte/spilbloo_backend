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
    def send_email(self, subject: str, body: str, to_email: str, from_email: str = None, html_body: str = None, cc: list = None, bcc: list = None) -> bool:
        if not from_email:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")
        
        try:
            from django.core.mail import EmailMultiAlternatives
            email = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=from_email,
                to=[to_email],
                cc=cc if cc else None,
                bcc=bcc if bcc else None
            )
            if html_body:
                email.attach_alternative(html_body, "text/html")
            email.send(fail_silently=False)
            return True
        except Exception as e:
            logger.exception("SMTP Email sending failed to %s: %s", to_email, str(e))
            return False

