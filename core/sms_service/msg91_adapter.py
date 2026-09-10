import logging
import requests
from django.conf import settings
from .base import BaseSMSAdapter

logger = logging.getLogger(__name__)

class MSG91SMSAdapter(BaseSMSAdapter):
    """
    Adapter for MSG91 SMS & OTP Service.
    Communicates with MSG91 v5 APIs (OTP and Flow endpoints).
    """

    OTP_API_URL = "https://control.msg91.com/api/v5/otp"
    FLOW_API_URL = "https://control.msg91.com/api/v5/flow"

    def __init__(self, auth_key: str = None, otp_template_id: str = None, sender_id: str = None):
        self.auth_key = auth_key or getattr(settings, "MSG91_AUTH_KEY", "")
        self.otp_template_id = (
            otp_template_id
            or getattr(settings, "MSG91_OTP_TEMPLATE_ID", None)
            or getattr(settings, "MSG91_DLT_TE_ID", "")
        )
        self.sender_id = sender_id or getattr(settings, "MSG91_SENDER_ID", "SPBLOO")
        self.timeout = getattr(settings, "MSG91_HTTP_TIMEOUT", 10)

    def send_otp(self, phone_number: str, otp: str, **kwargs) -> bool:
        """
        Dispatches OTP via MSG91 OTP API (https://control.msg91.com/api/v5/otp).
        """
        normalized_mobile = self.normalize_phone_number(phone_number)
        if not normalized_mobile:
            logger.error("[MSG91] Cannot send OTP: Invalid phone number '%s'", phone_number)
            return False

        if not self.auth_key:
            logger.warning("[MSG91] MSG91_AUTH_KEY is not configured. Falling back to console log.")
            logger.info("[MSG91 MOCK] To: %s | OTP: %s", normalized_mobile, otp)
            return True

        # If template_id is a 24-character hex string, it is a MSG91 Flow/Campaign template
        is_flow_template = bool(
            self.otp_template_id
            and len(self.otp_template_id) == 24
            and all(c in '0123456789abcdefABCDEF' for c in self.otp_template_id)
        )

        if is_flow_template:
            payload = {
                "template_id": self.otp_template_id,
                "short_url": "0",
                "sender": self.sender_id,
                "recipients": [
                    {
                        "mobiles": normalized_mobile,
                        "otp": str(otp),
                        "number": str(otp),
                        "OTP": str(otp),
                        **kwargs.get("extra_variables", {})
                    }
                ]
            }
            headers = {
                "Content-Type": "application/json",
                "authkey": self.auth_key,
            }
            try:
                response = requests.post(
                    self.FLOW_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                response_json = response.json() if response.content else {}
                if isinstance(response_json, dict) and "message" in response_json and "request_id" not in response_json:
                    response_json["request_id"] = response_json["message"]
                self.last_response = response_json
                if response.status_code == 200 and response_json.get("type") != "error":
                    logger.info("[MSG91 Flow] OTP sent successfully to %s: %s", normalized_mobile, response_json)
                    return True
                else:
                    logger.error("[MSG91 Flow] OTP send failed for %s. Status: %s, Response: %s",
                                 normalized_mobile, response.status_code, response_json)
                    return False
            except Exception as e:
                logger.exception("[MSG91 Flow] Network error dispatching OTP to %s: %s", normalized_mobile, str(e))
                return False

        # Fallback to standard SendOTP v5 API for non-Flow template IDs
        params = {
            "mobile": normalized_mobile,
            "authkey": self.auth_key,
            "otp": str(otp),
            "otp_expiry": kwargs.get("otp_expiry", 10),
        }
        if self.otp_template_id:
            params["template_id"] = self.otp_template_id
        if self.sender_id:
            params["sender"] = self.sender_id

        headers = {
            "Content-Type": "application/json",
            "authkey": self.auth_key,
        }
        payload = {
            "otp": str(otp),
            "number": str(otp),
            **kwargs.get("extra_variables", {})
        }

        try:
            response = requests.post(
                self.OTP_API_URL,
                params=params,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response_json = response.json() if response.content else {}

            self.last_response = response_json
            if response.status_code == 200 and response_json.get("type") != "error":
                logger.info("[MSG91] OTP sent successfully to %s: %s", normalized_mobile, response_json)
                return True
            else:
                logger.error("[MSG91] OTP send failed for %s. Status: %s, Response: %s",
                             normalized_mobile, response.status_code, response_json)
                return False
        except Exception as e:
            logger.exception("[MSG91] Network error dispatching OTP to %s: %s", normalized_mobile, str(e))
            return False

    def send_sms(self, phone_number: str, message: str, **kwargs) -> bool:
        """
        Dispatches transactional SMS via MSG91 Flow API.
        """
        normalized_mobile = self.normalize_phone_number(phone_number)
        if not normalized_mobile:
            logger.error("[MSG91] Cannot send SMS: Invalid phone number '%s'", phone_number)
            return False

        if not self.auth_key:
            logger.warning("[MSG91] MSG91_AUTH_KEY is not configured. Falling back to console log.")
            logger.info("[MSG91 MOCK SMS] To: %s | Message: %s", normalized_mobile, message)
            return True

        template_id = kwargs.get("template_id") or self.otp_template_id
        payload = {
            "template_id": template_id,
            "short_url": "0",
            "recipients": [
                {
                    "mobiles": normalized_mobile,
                    "message": message,
                    **kwargs.get("extra_variables", {})
                }
            ]
        }
        headers = {
            "Content-Type": "application/json",
            "authkey": self.auth_key,
        }

        try:
            response = requests.post(
                self.FLOW_API_URL,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response_json = response.json() if response.content else {}

            if response.status_code == 200 and response_json.get("type") != "error":
                logger.info("[MSG91] SMS sent successfully to %s: %s", normalized_mobile, response_json)
                return True
            else:
                logger.error("[MSG91] SMS send failed for %s. Status: %s, Response: %s",
                             normalized_mobile, response.status_code, response_json)
                return False
        except Exception as e:
            logger.exception("[MSG91] Network error dispatching SMS to %s: %s", normalized_mobile, str(e))
            return False
