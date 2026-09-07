import logging
import boto3
from django.conf import settings
from .base import BaseSMSAdapter

logger = logging.getLogger(__name__)

class AWSSNSAdapter(BaseSMSAdapter):
    """
    Adapter for AWS SNS SMS & OTP Service.
    """

    def _get_sns_client(self):
        kwargs = {}
        if getattr(settings, 'AWS_ACCESS_KEY_ID', None):
            kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
        if getattr(settings, 'AWS_SECRET_ACCESS_KEY', None):
            kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY

        region = getattr(settings, 'AWS_SES_REGION_NAME', None) or getattr(settings, 'AWS_S3_REGION_NAME', 'ap-south-1')
        kwargs['region_name'] = region
        return boto3.client('sns', **kwargs)

    def send_otp(self, phone_number: str, otp: str, **kwargs) -> bool:
        message = kwargs.get("message") or f"Your Spilbloo verification code is {otp}. Valid for 10 minutes."
        return self.send_sms(phone_number, message, **kwargs)

    def send_sms(self, phone_number: str, message: str, **kwargs) -> bool:
        phone_e164 = self.format_e164(phone_number)
        if not phone_e164:
            logger.error("[AWS SNS] Cannot send SMS: Invalid phone number '%s'", phone_number)
            return False

        try:
            sns = self._get_sns_client()
            response = sns.publish(
                PhoneNumber=phone_e164,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'Value': 'Transactional'
                    }
                }
            )
            logger.info("[AWS SNS] SMS sent to %s. MessageId: %s", phone_e164, response.get('MessageId'))
            return True
        except Exception as e:
            logger.exception("[AWS SNS] Failed to send SMS to %s: %s", phone_e164, str(e))
            return False
