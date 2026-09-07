import re
import logging
from typing import Any, Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone

from communication.models import CommunicationGateway, CommunicationTemplate, CommunicationLog
from core.sms_service.msg91_adapter import MSG91SMSAdapter
from core.sms_service.console_adapter import ConsoleSMSAdapter
from core.sms_service.sns_adapter import AWSSNSAdapter
from core.email_service.factory import get_email_client

logger = logging.getLogger(__name__)


class CommunicationService:
    """
    Unified communication dispatch engine.
    Fetches DB-configured Gateways and Templates, interpolates variables,
    dispatches outbound messages, and records comprehensive audit logs.
    """

    @staticmethod
    def render_content(template_str: Optional[str], context: Dict[str, Any]) -> str:
        """
        Renders template placeholders supporting both Jinja/Mustache {{var}}
        and DLT ##var## formats.
        """
        if not template_str:
            return ""

        rendered = template_str
        for key, value in context.items():
            str_val = str(value) if value is not None else ""
            # Replace {{key}} and {{ key }}
            pattern_braces = re.compile(r'\{\{\s*' + re.escape(key) + r'\s*\}\}')
            rendered = pattern_braces.sub(str_val, rendered)
            # Replace ##key##
            pattern_hash = re.compile(r'##\s*' + re.escape(key) + r'\s*##')
            rendered = pattern_hash.sub(str_val, rendered)

        return rendered

    @classmethod
    def get_template(cls, event_code: str, channel: str) -> Optional[CommunicationTemplate]:
        return CommunicationTemplate.objects.filter(
            event_code=event_code,
            channel=channel,
            is_active=True
        ).first()

    @classmethod
    def get_gateway(cls, channel: str) -> Optional[CommunicationGateway]:
        return CommunicationGateway.objects.filter(
            channel=channel,
            is_active=True
        ).order_by('priority', '-id').first()

    @classmethod
    def send(
        cls,
        event_code: str,
        recipient: str,
        context: Optional[Dict[str, Any]] = None,
        channel: str = CommunicationGateway.CHANNEL_SMS,
        user=None,
        override_gateway: Optional[CommunicationGateway] = None,
        **kwargs
    ) -> Tuple[bool, CommunicationLog]:
        """
        Main entry point for dispatching messages.
        """
        context = context or {}
        template = cls.get_template(event_code, channel)
        gateway = override_gateway or cls.get_gateway(channel)

        rendered_subject = None
        rendered_body = ""

        if template:
            rendered_subject = cls.render_content(template.subject_template, context)
            rendered_body = cls.render_content(template.body_template, context)
        elif "body" in context or "message" in context:
            rendered_body = str(context.get("body") or context.get("message"))
            rendered_subject = str(context.get("subject") or "")

        # Create initial audit log entry
        log_entry = CommunicationLog.objects.create(
            recipient=recipient,
            user=user,
            channel=channel,
            event_code=event_code,
            gateway=gateway,
            template=template,
            rendered_subject=rendered_subject,
            rendered_body=rendered_body,
            status=CommunicationLog.STATUS_QUEUED,
            request_payload={"context": context, "recipient": recipient}
        )

        success = False
        gateway_to_try = gateway

        while gateway_to_try:
            success, response_data, ext_id, error_msg = cls._dispatch_via_gateway(
                gateway=gateway_to_try,
                channel=channel,
                recipient=recipient,
                rendered_body=rendered_body,
                rendered_subject=rendered_subject,
                template=template,
                context=context,
                **kwargs
            )

            if success:
                log_entry.status = CommunicationLog.STATUS_SENT
                log_entry.external_message_id = ext_id
                log_entry.gateway_response = response_data
                log_entry.error_message = None
                log_entry.gateway = gateway_to_try
                log_entry.save()
                logger.info(
                    "[CommunicationHub] Dispatched %s to %s via %s (Log #%s, ExtID: %s)",
                    event_code, recipient, gateway_to_try.name, log_entry.id, ext_id
                )
                return True, log_entry

            logger.warning(
                "[CommunicationHub] Gateway '%s' failed for %s to %s. Error: %s",
                gateway_to_try.name, event_code, recipient, error_msg
            )

            # Check fallback gateway
            gateway_to_try = gateway_to_try.fallback_gateway

        # If we reach here, all gateways failed (or no gateway configured in DB)
        # Attempt fallback to settings-based adapter so app never stops functioning
        if not success:
            logger.info("[CommunicationHub] Attempting fallback to settings-based client for %s", channel)
            success, response_data, ext_id, error_msg = cls._dispatch_via_settings_fallback(
                channel=channel,
                recipient=recipient,
                context=context,
                rendered_body=rendered_body,
                rendered_subject=rendered_subject,
                template=template,
                **kwargs
            )

            log_entry.status = CommunicationLog.STATUS_SENT if success else CommunicationLog.STATUS_FAILED
            log_entry.external_message_id = ext_id
            log_entry.gateway_response = response_data
            log_entry.error_message = error_msg
            log_entry.save()

        return success, log_entry

    @classmethod
    def _dispatch_via_gateway(
        cls,
        gateway: CommunicationGateway,
        channel: str,
        recipient: str,
        rendered_body: str,
        rendered_subject: Optional[str],
        template: Optional[CommunicationTemplate],
        context: Dict[str, Any],
        **kwargs
    ) -> Tuple[bool, Dict[str, Any], Optional[str], Optional[str]]:
        creds = gateway.credentials or {}
        provider = gateway.provider_type

        try:
            if provider == CommunicationGateway.PROVIDER_MSG91:
                auth_key = creds.get("auth_key") or getattr(settings, "MSG91_AUTH_KEY", "")
                sender_id = (
                    (template.sender_override if template and template.sender_override else None)
                    or creds.get("sender_id")
                    or getattr(settings, "MSG91_SENDER_ID", "SPBLOO")
                )
                template_id = (
                    (template.external_template_id if template and template.external_template_id else None)
                    or creds.get("template_id")
                    or getattr(settings, "MSG91_OTP_TEMPLATE_ID", None)
                )

                adapter = MSG91SMSAdapter(
                    auth_key=auth_key,
                    otp_template_id=template_id,
                    sender_id=sender_id
                )

                otp = context.get("otp") or context.get("number") or "0000"
                # Pass all context keys as extra variables for template placeholders
                extra_vars = {**context}
                ok = adapter.send_otp(
                    phone_number=recipient,
                    otp=str(otp),
                    extra_variables=extra_vars
                )

                last_resp = getattr(adapter, "last_response", {}) or {}
                ext_id = last_resp.get("request_id") if isinstance(last_resp, dict) else None

                if ok:
                    resp_data = {"provider": "msg91", "sender": sender_id, "template_id": template_id, **(last_resp if isinstance(last_resp, dict) else {})}
                    return True, resp_data, ext_id, None
                return False, last_resp, ext_id, "MSG91 dispatch returned False"

            elif provider == CommunicationGateway.PROVIDER_CONSOLE:
                adapter = ConsoleSMSAdapter()
                otp = context.get("otp") or context.get("number") or "0000"
                adapter.send_otp(recipient, str(otp))
                return True, {"provider": "console", "mock": True}, "MOCK-MSG", None

            elif provider == CommunicationGateway.PROVIDER_AWS_SNS:
                adapter = AWSSNSAdapter()
                otp = context.get("otp") or context.get("number") or "0000"
                ok = adapter.send_otp(recipient, str(otp))
                return ok, {"provider": "aws_sns"}, None, None if ok else "SNS returned False"

            elif provider in (CommunicationGateway.PROVIDER_AWS_SES, CommunicationGateway.PROVIDER_SMTP):
                email_client = get_email_client()
                from_email = creds.get("from_email") or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")
                subject = rendered_subject or "Spilbloo Notification"
                body = rendered_body or str(context.get("message", ""))
                html_body = kwargs.get("html_body") or context.get("html_body")

                email_client.send_email(
                    subject=subject,
                    body=body,
                    to_email=recipient,
                    from_email=from_email,
                    html_body=html_body
                )
                return True, {"provider": provider, "from_email": from_email}, None, None

            else:
                return False, {}, None, f"Unsupported provider_type '{provider}'"

        except Exception as e:
            logger.exception("[CommunicationHub] Exception during dispatch via %s: %s", gateway.name, str(e))
            return False, {}, None, str(e)

    @classmethod
    def _dispatch_via_settings_fallback(
        cls,
        channel: str,
        recipient: str,
        context: Dict[str, Any],
        rendered_body: str,
        rendered_subject: Optional[str],
        template: Optional[CommunicationTemplate],
        **kwargs
    ) -> Tuple[bool, Dict[str, Any], Optional[str], Optional[str]]:
        try:
            if channel == CommunicationGateway.CHANNEL_SMS:
                from core.sms_service.factory import get_sms_client
                client = get_sms_client()
                otp = context.get("otp") or context.get("number") or "0000"
                ok = client.send_otp(recipient, str(otp), extra_variables=context)
                return ok, {"fallback": "settings_sms_client"}, None, None if ok else "SMS fallback failed"

            elif channel == CommunicationGateway.CHANNEL_EMAIL:
                email_client = get_email_client()
                from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@spilbloo.com")
                subject = rendered_subject or "Spilbloo Notification"
                body = rendered_body or str(context.get("message", ""))
                html_body = kwargs.get("html_body") or context.get("html_body")

                email_client.send_email(
                    subject=subject,
                    body=body,
                    to_email=recipient,
                    from_email=from_email,
                    html_body=html_body
                )
                return True, {"fallback": "settings_email_client"}, None, None

            return False, {}, None, f"No settings fallback available for channel '{channel}'"
        except Exception as e:
            return False, {}, None, str(e)


def send_communication(event_code: str, recipient: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> bool:
    """
    Convenience function returning simple boolean success while persisting audit logs.
    """
    success, _ = CommunicationService.send(event_code, recipient, context, **kwargs)
    return success
