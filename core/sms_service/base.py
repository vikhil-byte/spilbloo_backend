from abc import ABC, abstractmethod
import re
import logging

logger = logging.getLogger(__name__)

try:
    import phonenumbers as _pn
except ImportError:
    _pn = None

class BaseSMSAdapter(ABC):
    """
    Abstract Base Adapter for SMS and Mobile OTP service providers.
    """

    def normalize_phone_number(self, phone_number: str, default_country_code: str = "91") -> str:
        """
        Sanitizes phone number to digits-only format suitable for SMS APIs (e.g. 919876543210).
        Uses phonenumbers library if available, falls back to regex.
        """
        if not phone_number:
            return ""

        if _pn is not None:
            raw = str(phone_number).strip()
            # Map common dial codes to region for parsing
            region_map = {"91": "IN", "1": "US", "44": "GB", "61": "AU", "971": "AE"}
            region = region_map.get(default_country_code, "IN")
            try:
                if raw.startswith("+"):
                    parsed = _pn.parse(raw, None)
                else:
                    parsed = _pn.parse(raw, region)
                if _pn.is_valid_number(parsed):
                    # E.164 without the '+' prefix — what MSG91 and most SMS APIs expect
                    e164 = _pn.format_number(parsed, _pn.PhoneNumberFormat.E164)
                    return e164.lstrip("+")
            except _pn.NumberParseException:
                pass

        # Fallback: regex-based normalization
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
