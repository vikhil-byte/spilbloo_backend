from abc import ABC, abstractmethod
import re
import logging

logger = logging.getLogger(__name__)

class BaseSMSAdapter(ABC):
    """
    Abstract Base Adapter for SMS and Mobile OTP service providers.
    """

    def normalize_phone_number(self, phone_number: str, default_country_code: str = "91") -> str:
        """
        Sanitizes phone number by removing whitespace, hyphens, and non-digits.
        If a 10-digit number is provided without a country code, prepends the default country code (e.g. 91).
        """
        if not phone_number:
            return ""
        digits = re.sub(r"\D", "", str(phone_number).strip())
        if len(digits) == 10:
            return f"{default_country_code}{digits}"
        return digits

    def format_e164(self, phone_number: str, default_country_code: str = "91") -> str:
        """
        Formats normalized phone number into standard E.164 format (+919876543210).
        """
        normalized = self.normalize_phone_number(phone_number, default_country_code=default_country_code)
        if not normalized:
            return ""
        if not normalized.startswith("+"):
            return f"+{normalized}"
        return normalized

    @abstractmethod
    def send_otp(self, phone_number: str, otp: str, **kwargs) -> bool:
        """
        Send an OTP verification code to a mobile phone number.

        :param phone_number: Destination mobile number.
        :param otp: The OTP verification code.
        :param kwargs: Additional template variables or provider-specific parameters.
        :return: True if dispatch succeeded, False otherwise.
        """
        pass

    @abstractmethod
    def send_sms(self, phone_number: str, message: str, **kwargs) -> bool:
        """
        Send a transactional SMS message to a mobile phone number.

        :param phone_number: Destination mobile number.
        :param message: SMS body text.
        :param kwargs: Additional provider-specific parameters.
        :return: True if dispatch succeeded, False otherwise.
        """
        pass
