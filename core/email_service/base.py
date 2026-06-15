from abc import ABC, abstractmethod

class BaseEmailAdapter(ABC):
    """
    Abstract interface for all email service providers.
    """
    @abstractmethod
    def send_email(self, subject: str, body: str, to_email: str, from_email: str = None) -> bool:
        """
        Send an email.
        
        :param subject: The email subject line.
        :param body: The plain text email body content.
        :param to_email: The recipient's email address.
        :param from_email: The sender's email address (optional, defaults to settings.DEFAULT_FROM_EMAIL).
        :return: True if the email was successfully sent/queued, False otherwise.
        """
        pass
