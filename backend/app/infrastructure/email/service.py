# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Email service for sending emails.

Provides async email sending with template support.
Supports multiple backends: SMTP, SendGrid, AWS SES, Console (dev).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.infrastructure.email.templates import (
    EmailTemplateEngine,
    EmailTemplateType,
    get_template_engine,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class EmailBackend(str, Enum):
    """Available email backends."""

    CONSOLE = "console"  # Development - prints to console
    SMTP = "smtp"


@dataclass
class EmailRecipient:
    """Email recipient information."""

    email: str
    name: str | None = None

    def formatted(self) -> str:
        """Return formatted email address."""
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


@dataclass
class EmailMessage:
    """Email message ready to send."""

    to: list[EmailRecipient]
    subject: str
    html_body: str
    text_body: str
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    cc: list[EmailRecipient] | None = None
    bcc: list[EmailRecipient] | None = None
    headers: dict[str, str] | None = None
    attachments: list[dict[str, Any]] | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class EmailSenderPort(ABC):
    """Abstract port for email sending backends."""

    @abstractmethod
    async def send(self, message: EmailMessage) -> bool:
        """
        Send an email message.

        Args:
            message: The email message to send

        Returns:
            True if sent successfully, False otherwise
        """

    @abstractmethod
    async def send_batch(self, messages: list[EmailMessage]) -> dict[str, bool]:
        """
        Send multiple email messages.

        Args:
            messages: List of email messages to send

        Returns:
            Dict mapping recipient emails to success status
        """


class ConsoleEmailSender(EmailSenderPort):
    """
    Console email sender for development.

    Prints emails to console/logs instead of sending.
    """

    async def send(self, message: EmailMessage) -> bool:
        """Print email to console."""
        recipients = ", ".join(r.formatted() for r in message.to)

        logger.info("=" * 60)
        logger.info("📧 EMAIL (Console Mode - Not Actually Sent)")
        logger.info("=" * 60)
        logger.info("To: %s", recipients)
        logger.info("Subject: %s", message.subject)
        logger.info("-" * 60)
        logger.info("TEXT BODY:")
        logger.info(
            message.text_body[:500] + "..."
            if len(message.text_body) > 500
            else message.text_body
        )
        logger.info("=" * 60)

        return True

    async def send_batch(self, messages: list[EmailMessage]) -> dict[str, bool]:
        """Print all emails to console."""
        results = {}
        for message in messages:
            success = await self.send(message)
            for recipient in message.to:
                results[recipient.email] = success
        return results


class SMTPEmailSender(EmailSenderPort):
    """
    SMTP email sender.

    Uses aiosmtplib for async SMTP sending.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        start_tls: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.start_tls = start_tls

    async def send(self, message: EmailMessage) -> bool:
        """Send email via SMTP."""
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            import aiosmtplib

            # Build MIME message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            from_email = message.from_email or "noreply@example.com"
            msg["From"] = (
                f"{message.from_name} <{from_email}>"
                if message.from_name
                else from_email
            )
            msg["To"] = ", ".join(r.formatted() for r in message.to)

            if message.reply_to:
                msg["Reply-To"] = message.reply_to

            # Attach text and HTML parts
            msg.attach(MIMEText(message.text_body, "plain", "utf-8"))
            msg.attach(MIMEText(message.html_body, "html", "utf-8"))

            # Send
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
                start_tls=self.start_tls,
            )

            logger.info("Email sent successfully to %d recipient(s)", len(message.to))
            return True

        except Exception as e:
            logger.error("Failed to send email: %s", type(e).__name__)
            return False

    async def send_batch(self, messages: list[EmailMessage]) -> dict[str, bool]:
        """Send multiple emails via SMTP."""
        results = {}
        for message in messages:
            success = await self.send(message)
            for recipient in message.to:
                results[recipient.email] = success
        return results


class EmailService:
    """
    Main email service with template support.

    Combines template engine with email sending backend.

    Usage:
        service = get_email_service()

        await service.send_verification_email(
            to_email="user@example.com",
            to_name="John Doe",
            verification_url="https://...",
            locale="es",
        )
    """

    def __init__(
        self,
        sender: EmailSenderPort | None = None,
        template_engine: EmailTemplateEngine | None = None,
    ) -> None:
        """
        Initialize email service.

        Args:
            sender: Email backend to use (defaults to console in dev)
            template_engine: Template engine instance
        """
        self._sender = sender or self._create_default_sender()
        self._template_engine = template_engine or get_template_engine()
        self._default_from_email = self._get_default_from_email()
        self._default_from_name = self._get_default_from_name()

    def _create_default_sender(self) -> EmailSenderPort:
        """Create default email sender based on settings."""
        from app.config import settings

        backend = getattr(settings, "EMAIL_BACKEND", "console")

        if backend == EmailBackend.SMTP.value:
            return SMTPEmailSender(
                host=getattr(settings, "SMTP_HOST", "localhost"),
                port=getattr(settings, "SMTP_PORT", 587),
                username=getattr(settings, "SMTP_USERNAME", None),
                password=getattr(settings, "SMTP_PASSWORD", None),
                use_tls=getattr(settings, "SMTP_TLS", True),
            )

        # Default to console for development
        return ConsoleEmailSender()

    def _get_default_from_email(self) -> str:
        """Get default from email."""
        from app.config import settings

        return getattr(settings, "EMAIL_FROM", "noreply@example.com")

    def _get_default_from_name(self) -> str:
        """Get default from name."""
        from app.config import settings

        return getattr(settings, "EMAIL_FROM_NAME", settings.APP_NAME)

    async def send_template_email(
        self,
        template_type: EmailTemplateType,
        to_email: str,
        to_name: str | None = None,
        locale: str = "en",
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        Send an email using a template.

        Args:
            template_type: Type of email template
            to_email: Recipient email address
            to_name: Recipient name (optional)
            locale: Language locale for template
            context: Additional context for template
            **kwargs: Additional email options

        Returns:
            True if sent successfully
        """
        # Merge context
        full_context = context or {}
        full_context["recipient_name"] = to_name or to_email.split("@")[0]
        full_context["recipient_email"] = to_email

        # Render template
        template = self._template_engine.render(
            template_type=template_type,
            locale=locale,
            context=full_context,
        )

        # Build message
        message = EmailMessage(
            to=[EmailRecipient(email=to_email, name=to_name)],
            subject=template.subject,
            html_body=template.html_body,
            text_body=template.text_body,
            from_email=kwargs.get("from_email", self._default_from_email),
            from_name=kwargs.get("from_name", self._default_from_name),
            reply_to=kwargs.get("reply_to"),
            tags=[template_type.value],
            metadata={"locale": locale, "template": template_type.value},
        )

        return await self._sender.send(message)

    # ===========================================
    # Convenience Methods for Common Emails
    # ===========================================

    async def send_registration_email(
        self,
        to_email: str,
        to_name: str | None = None,
        locale: str = "en",
        **context: Any,
    ) -> bool:
        """Send registration confirmation email."""
        return await self.send_template_email(
            template_type=EmailTemplateType.REGISTRATION,
            to_email=to_email,
            to_name=to_name,
            locale=locale,
            context=context,
        )

    async def send_verification_email(
        self,
        to_email: str,
        verification_url: str,
        to_name: str | None = None,
        locale: str = "en",
        expires_in_hours: int = 24,
    ) -> bool:
        """Send email verification link."""
        return await self.send_template_email(
            template_type=EmailTemplateType.EMAIL_VERIFICATION,
            to_email=to_email,
            to_name=to_name,
            locale=locale,
            context={
                "verification_url": verification_url,
                "expires_in_hours": expires_in_hours,
            },
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_url: str,
        to_name: str | None = None,
        locale: str = "en",
        expires_in_hours: int = 1,
    ) -> bool:
        """Send password reset email."""
        return await self.send_template_email(
            template_type=EmailTemplateType.PASSWORD_RESET,
            to_email=to_email,
            to_name=to_name,
            locale=locale,
            context={
                "reset_url": reset_url,
                "expires_in_hours": expires_in_hours,
            },
        )

    async def send_password_changed_email(
        self,
        to_email: str,
        to_name: str | None = None,
        locale: str = "en",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """Send password changed notification."""
        return await self.send_template_email(
            template_type=EmailTemplateType.PASSWORD_CHANGED,
            to_email=to_email,
            to_name=to_name,
            locale=locale,
            context={
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        )

    async def send_welcome_email(
        self,
        to_email: str,
        to_name: str | None = None,
        locale: str = "en",
        login_url: str | None = None,
    ) -> bool:
        """Send welcome email after verification."""
        return await self.send_template_email(
            template_type=EmailTemplateType.WELCOME,
            to_email=to_email,
            to_name=to_name,
            locale=locale,
            context={"login_url": login_url},
        )

    async def send_login_new_device_email(
        self,
        to_email: str,
        to_name: str | None = None,
        locale: str = "en",
        device_info: str | None = None,
        location: str | None = None,
        ip_address: str | None = None,
        login_time: str | None = None,
    ) -> bool:
        """Send notification of login from new device."""
        return await self.send_template_email(
            template_type=EmailTemplateType.LOGIN_NEW_DEVICE,
            to_email=to_email,
            to_name=to_name,
            locale=locale,
            context={
                "device_info": device_info,
                "location": location,
                "ip_address": ip_address,
                "login_time": login_time,
            },
        )

    async def send_account_locked_email(
        self,
        to_email: str,
        to_name: str | None = None,
        locale: str = "en",
        unlock_url: str | None = None,
        reason: str | None = None,
    ) -> bool:
        """Send account locked notification."""
        return await self.send_template_email(
            template_type=EmailTemplateType.ACCOUNT_LOCKED,
            to_email=to_email,
            to_name=to_name,
            locale=locale,
            context={
                "unlock_url": unlock_url,
                "reason": reason,
            },
        )

    async def send_mfa_enabled_email(
        self,
        to_email: str,
        to_name: str | None = None,
        locale: str = "en",
    ) -> bool:
        """Send MFA enabled notification."""
        return await self.send_template_email(
            template_type=EmailTemplateType.MFA_ENABLED,
            to_email=to_email,
            to_name=to_name,
            locale=locale,
        )

    async def send_tenant_invitation_email(
        self,
        to_email: str,
        to_name: str | None = None,
        locale: str = "en",
        tenant_name: str | None = None,
        inviter_name: str | None = None,
        invitation_url: str | None = None,
        role: str | None = None,
    ) -> bool:
        """Send tenant/organization invitation."""
        return await self.send_template_email(
            template_type=EmailTemplateType.TENANT_INVITATION,
            to_email=to_email,
            to_name=to_name,
            locale=locale,
            context={
                "tenant_name": tenant_name,
                "inviter_name": inviter_name,
                "invitation_url": invitation_url,
                "role": role,
            },
        )


# Singleton instance
_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get or create the email service singleton."""
    global _service
    if _service is None:
        _service = EmailService()
    return _service
