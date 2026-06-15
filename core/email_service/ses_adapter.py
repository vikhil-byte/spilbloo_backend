from django.conf import settings
from .base import BaseEmailAdapter
import logging

logger = logging.getLogger(__name__)

class SESEmailAdapter(BaseEmailAdapter):
    """
    Direct AWS SES API email client using boto3 SDK.
    """
    def send_email(self, subject: str, body: str, to_email: str, from_email: str = None) -> bool:
        try:
            import boto3
        except ImportError:
            logger.error("boto3 is not installed. Please install boto3 to use the AWS SES API adapter.")
            return False

        if not from_email:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")

        # Load SES-specific configurations from Django settings
        region_name = getattr(settings, "AWS_SES_REGION_NAME", "us-east-1")
        access_key = getattr(settings, "AWS_ACCESS_KEY_ID", None)
        secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)

        try:
            if access_key and secret_key:
                client = boto3.client(
                    'ses',
                    region_name=region_name,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key
                )
            else:
                # Fallback to IAM Instance Profile/Role or local AWS credentials file
                client = boto3.client('ses', region_name=region_name)

            response = client.send_email(
                Destination={
                    'ToAddresses': [to_email],
                },
                Message={
                    'Body': {
                        'Text': {
                            'Charset': 'UTF-8',
                            'Data': body,
                        },
                    },
                    'Subject': {
                        'Charset': 'UTF-8',
                        'Data': subject,
                    },
                },
                Source=from_email,
            )
            logger.info("AWS SES Email sent successfully to %s. MessageId: %s", to_email, response.get('MessageId'))
            return True
        except Exception as e:
            logger.exception("AWS SES API Email sending failed to %s: %s", to_email, str(e))
            return False
