from .base import BaseEmailAdapter
import logging

logger = logging.getLogger(__name__)

class ConsoleEmailAdapter(BaseEmailAdapter):
    """
    Mock/Console email client that logs emails to standard output/logs.
    Useful for local development and testing.
    """
    def send_email(self, subject: str, body: str, to_email: str, from_email: str = None, html_body: str = None, cc: list = None, bcc: list = None) -> bool:
        logger.info(
            "\n"
            "=================== CONSOLE EMAIL ADAPTER ===================\n"
            "From: %s\n"
            "To: %s\n"
            "CC: %s\n"
            "BCC: %s\n"
            "Subject: %s\n"
            "Body:\n%s\n"
            "HTML Body:\n%s\n"
            "=============================================================",
            from_email or "default", to_email, cc or "None", bcc or "None", subject, body, html_body
        )
        return True

