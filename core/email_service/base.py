from abc import ABC, abstractmethod

class BaseEmailAdapter(ABC):
    """
    Abstract interface for all email service providers.
    """
    @abstractmethod
    def send_email(self, subject: str, body: str, to_email: str, from_email: str = None, html_body: str = None, cc: list = None, bcc: list = None) -> bool:
        """
        Send an email.
        
        :param subject: The email subject line.
        :param body: The plain text email body content.
        :param to_email: The recipient's email address.
        :param from_email: The sender's email address (optional, defaults to settings.DEFAULT_FROM_EMAIL).
        :param html_body: The HTML content of the email (optional).
        :param cc: A list of CC recipient email addresses (optional).
        :param bcc: A list of BCC recipient email addresses (optional).
        :return: True if the email was successfully sent/queued, False otherwise.
        """
        pass

