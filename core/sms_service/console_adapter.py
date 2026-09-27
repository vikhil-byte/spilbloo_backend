import logging
from .base import BaseSMSAdapter

logger = logging.getLogger(__name__)

class ConsoleSMSAdapter(BaseSMSAdapter):
    """
    Mock / Console Adapter for development and testing environments.
    Prints OTP and SMS to logger without making third-party API calls.
    """

    def send_otp(self, phone_number: str, otp: str, **kwargs) -> bool:
        normalized = self.normalize_phone_number(phone_number)
        logger.info("[SMS CONSOLE ADAPTER] [OTP] Destination: %s | OTP Code: %s", normalized, otp)
        return True

    def send_sms(self, phone_number: str, message: str, **kwargs) -> bool:
        normalized = self.normalize_phone_number(phone_number)
        logger.info("[SMS CONSOLE ADAPTER] [SMS] Destination: %s | Message: %s", normalized, message)
        return True
