import logging
from django.conf import settings
from .base import BaseSMSAdapter
from .msg91_adapter import MSG91SMSAdapter
from .sns_adapter import AWSSNSAdapter
from .console_adapter import ConsoleSMSAdapter

logger = logging.getLogger(__name__)

def get_sms_client() -> BaseSMSAdapter:
    """
    Factory function to retrieve the configured SMS adapter based on Django settings.
    Supported providers:
      - 'msg91' (default in production)
      - 'sns' (AWS SNS)
      - 'console' (local testing / mock)
    """
    provider = getattr(settings, "SMS_SERVICE_PROVIDER", getattr(settings, "SMS_PROVIDER", "msg91")).lower()

    if provider == "msg91":
        return MSG91SMSAdapter()
    elif provider in ("sns", "aws_sns"):
        return AWSSNSAdapter()
    elif provider in ("console", "mock"):
        return ConsoleSMSAdapter()
    else:
        logger.warning("Unrecognized SMS_SERVICE_PROVIDER '%s', defaulting to MSG91SMSAdapter", provider)
        return MSG91SMSAdapter()
