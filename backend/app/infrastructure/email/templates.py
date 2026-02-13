# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Email template engine with i18n support.

Provides Jinja2-based email templates with multi-language support.
"""

from dataclasses import dataclass, field
from datetime import UTC
from enum import Enum
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.infrastructure.i18n import get_i18n


class EmailTemplateType(str, Enum):
    """Available email template types."""

    # Authentication
    REGISTRATION = "registration"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    PASSWORD_CHANGED = "password_changed"

    # Account
    WELCOME = "welcome"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    ACCOUNT_DEACTIVATED = "account_deactivated"

    # Security
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    LOGIN_NEW_DEVICE = "login_new_device"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    EMAIL_OTP = "email_otp"

    # API
    API_KEY_CREATED = "api_key_created"
    API_KEY_EXPIRING = "api_key_expiring"

    # Tenant/Organization
    TENANT_INVITATION = "tenant_invitation"
    TENANT_ROLE_CHANGED = "tenant_role_changed"

    # Notifications
    GENERIC_NOTIFICATION = "generic_notification"


@dataclass
class EmailTemplate:
    """
    Represents a rendered email template.

    Attributes:
        subject: Email subject line
        html_body: HTML content of the email
        text_body: Plain text content of the email
        template_type: Type of email template used
        locale: Language locale used for rendering
    """

    subject: str
    html_body: str
    text_body: str
    template_type: EmailTemplateType
    locale: str
    metadata: dict[str, Any] = field(default_factory=dict)


class EmailTemplateEngine:
    """
    Email template engine with Jinja2 and i18n support.

    Renders email templates in multiple languages using Jinja2
    templating and the i18n translation system.

    Usage:
        engine = EmailTemplateEngine()
        template = engine.render(
            template_type=EmailTemplateType.EMAIL_VERIFICATION,
            locale="es",
            context={"verification_url": "https://..."}
        )
    """

    DEFAULT_LOCALE = "en"

    # Use canonical locale list from settings to avoid desynchronization
    @property
    def supported_locales(self) -> list[str]:
        """Get supported locales from app settings (single source of truth)."""
        from app.config import settings

        return settings.SUPPORTED_LOCALES

    def __init__(self, templates_dir: Path | None = None) -> None:
        """
        Initialize the email template engine.

        Args:
            templates_dir: Directory containing email templates.
                          Defaults to infrastructure/email/templates
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"

        self._templates_dir = templates_dir
        self._i18n = get_i18n()

        # Create templates directory if it doesn't exist
        self._templates_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self._env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=select_autoescape(default=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add translation function to templates
        self._env.globals["t"] = self._translate
        self._env.globals["app_name"] = self._get_app_name

    def _get_app_name(self) -> str:
        """Get application name from settings."""
        from app.config import settings

        return settings.APP_NAME

    def _translate(self, key: str, **kwargs: Any) -> str:
        """
        Translation function available in templates.

        The locale is set per-render via thread-local or context.
        """
        return self._i18n.t(key, locale=self._current_locale, **kwargs)

    def render(
        self,
        template_type: EmailTemplateType,
        locale: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> EmailTemplate:
        """
        Render an email template.

        Args:
            template_type: Type of email template to render
            locale: Target language locale (defaults to 'en')
            context: Variables to pass to the template

        Returns:
            EmailTemplate with rendered subject and body

        Raises:
            FileNotFoundError: If template files don't exist
        """
        locale = locale or self.DEFAULT_LOCALE
        if locale not in self.supported_locales:
            locale = self.DEFAULT_LOCALE

        context = context or {}
        self._current_locale = locale

        # Add common context
        context.update(
            {
                "locale": locale,
                "year": self._get_current_year(),
                "app_name": self._get_app_name(),
                "support_email": self._get_support_email(),
            }
        )

        # Render HTML template
        html_template = self._env.get_template(f"{template_type.value}/html.jinja2")
        html_body = html_template.render(**context)

        # Render text template
        text_template = self._env.get_template(f"{template_type.value}/text.jinja2")
        text_body = text_template.render(**context)

        # Get subject from translations (exclude locale from context to avoid duplicate kwarg)
        i18n_context = {k: v for k, v in context.items() if k != "locale"}
        subject = self._i18n.t(
            f"email.{template_type.value}.subject", locale=locale, **i18n_context
        )

        return EmailTemplate(
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            template_type=template_type,
            locale=locale,
            metadata={"rendered_at": self._get_current_timestamp()},
        )

    def _get_current_year(self) -> int:
        """Get current year for copyright."""
        from datetime import UTC, datetime

        return datetime.now(UTC).year

    def _get_current_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now(UTC).isoformat()

    def _get_support_email(self) -> str:
        """Get support email from settings."""
        from app.config import settings

        return getattr(settings, "SUPPORT_EMAIL", "support@example.com")

    def get_available_templates(self) -> list[str]:
        """Get list of available template types."""
        return [t.value for t in EmailTemplateType]

    def get_supported_locales(self) -> list[str]:
        """Get list of supported locales."""
        return self.supported_locales.copy()


# Singleton instance
_engine: EmailTemplateEngine | None = None


def get_template_engine() -> EmailTemplateEngine:
    """Get or create the email template engine singleton."""
    global _engine
    if _engine is None:
        _engine = EmailTemplateEngine()
    return _engine
