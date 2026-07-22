from django.conf import settings
from .smtp_adapter import SMTPEmailAdapter
from .ses_adapter import SESEmailAdapter
from .console_adapter import ConsoleEmailAdapter

def get_email_client():
    """
    Factory function to retrieve the configured email adapter based on Django settings.
    """
    provider = getattr(settings, "EMAIL_SERVICE_PROVIDER", "smtp").lower()
    
    if provider == "ses":
        return SESEmailAdapter()
    elif provider == "console":
        return ConsoleEmailAdapter()
    else:
        return SMTPEmailAdapter()
