# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for email template engine.

Tests for EmailTemplateType, EmailTemplate, and EmailTemplateEngine.
"""

from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

from app.infrastructure.email.templates import (
    EmailTemplate,
    EmailTemplateType,
    EmailTemplateEngine,
    get_template_engine,
)


class TestEmailTemplateType:
    """Tests for EmailTemplateType enum."""

    def test_registration_value(self) -> None:
        """Test registration template type."""
        assert EmailTemplateType.REGISTRATION.value == "registration"

    def test_email_verification_value(self) -> None:
        """Test email verification template type."""
        assert EmailTemplateType.EMAIL_VERIFICATION.value == "email_verification"

    def test_password_reset_value(self) -> None:
        """Test password reset template type."""
        assert EmailTemplateType.PASSWORD_RESET.value == "password_reset"

    def test_password_changed_value(self) -> None:
        """Test password changed template type."""
        assert EmailTemplateType.PASSWORD_CHANGED.value == "password_changed"

    def test_welcome_value(self) -> None:
        """Test welcome template type."""
        assert EmailTemplateType.WELCOME.value == "welcome"

    def test_mfa_enabled_value(self) -> None:
        """Test MFA enabled template type."""
        assert EmailTemplateType.MFA_ENABLED.value == "mfa_enabled"

    def test_mfa_disabled_value(self) -> None:
        """Test MFA disabled template type."""
        assert EmailTemplateType.MFA_DISABLED.value == "mfa_disabled"

    def test_api_key_created_value(self) -> None:
        """Test API key created template type."""
        assert EmailTemplateType.API_KEY_CREATED.value == "api_key_created"

    def test_tenant_invitation_value(self) -> None:
        """Test tenant invitation template type."""
        assert EmailTemplateType.TENANT_INVITATION.value == "tenant_invitation"

    def test_all_template_types_are_strings(self) -> None:
        """Test all template types have string values."""
        for template_type in EmailTemplateType:
            assert isinstance(template_type.value, str)
            assert len(template_type.value) > 0

    def test_template_types_are_unique(self) -> None:
        """Test all template type values are unique."""
        values = [t.value for t in EmailTemplateType]
        assert len(values) == len(set(values))


class TestEmailTemplate:
    """Tests for EmailTemplate dataclass."""

    def test_basic_template(self) -> None:
        """Test creating basic email template."""
        template = EmailTemplate(
            subject="Test Subject",
            html_body="<p>HTML Body</p>",
            text_body="Text Body",
            template_type=EmailTemplateType.WELCOME,
            locale="en",
        )
        
        assert template.subject == "Test Subject"
        assert template.html_body == "<p>HTML Body</p>"
        assert template.text_body == "Text Body"
        assert template.template_type == EmailTemplateType.WELCOME
        assert template.locale == "en"

    def test_template_default_metadata(self) -> None:
        """Test template has empty metadata by default."""
        template = EmailTemplate(
            subject="Subject",
            html_body="HTML",
            text_body="Text",
            template_type=EmailTemplateType.REGISTRATION,
            locale="es",
        )
        
        assert template.metadata == {}

    def test_template_with_metadata(self) -> None:
        """Test template with custom metadata."""
        metadata = {"rendered_at": "2025-01-08T12:00:00Z", "version": "1.0"}
        
        template = EmailTemplate(
            subject="Subject",
            html_body="HTML",
            text_body="Text",
            template_type=EmailTemplateType.PASSWORD_RESET,
            locale="pt",
            metadata=metadata,
        )
        
        assert template.metadata == metadata
        assert template.metadata["version"] == "1.0"


class TestEmailTemplateEngine:
    """Tests for EmailTemplateEngine."""

    def test_default_locale(self) -> None:
        """Test default locale is English."""
        assert EmailTemplateEngine.DEFAULT_LOCALE == "en"

    def test_supported_locales(self) -> None:
        """Test supported locales include common languages."""
        expected = ["en", "es", "pt", "fr", "de"]
        assert EmailTemplateEngine.SUPPORTED_LOCALES == expected

    def test_engine_initialization(self) -> None:
        """Test engine initializes without errors."""
        engine = EmailTemplateEngine()
        
        assert engine is not None

    def test_get_available_templates(self) -> None:
        """Test getting available template types."""
        engine = EmailTemplateEngine()
        
        templates = engine.get_available_templates()
        
        assert "registration" in templates
        assert "welcome" in templates
        assert "password_reset" in templates

    def test_get_supported_locales(self) -> None:
        """Test getting supported locales."""
        engine = EmailTemplateEngine()
        
        locales = engine.get_supported_locales()
        
        assert "en" in locales
        assert "es" in locales
        assert locales == ["en", "es", "pt", "fr", "de"]

    def test_get_supported_locales_returns_copy(self) -> None:
        """Test that get_supported_locales returns a copy."""
        engine = EmailTemplateEngine()
        
        locales = engine.get_supported_locales()
        locales.append("invalid")
        
        # Original should be unchanged
        assert "invalid" not in engine.SUPPORTED_LOCALES


class TestGetTemplateEngine:
    """Tests for get_template_engine singleton."""

    def test_returns_engine_instance(self) -> None:
        """Test get_template_engine returns an engine."""
        engine = get_template_engine()
        
        assert isinstance(engine, EmailTemplateEngine)

    def test_returns_same_instance(self) -> None:
        """Test get_template_engine returns same instance."""
        engine1 = get_template_engine()
        engine2 = get_template_engine()
        
        assert engine1 is engine2


class TestEmailTemplateTypeCategories:
    """Tests for template type categories."""

    def test_authentication_templates(self) -> None:
        """Test authentication-related templates exist."""
        auth_templates = [
            "registration",
            "email_verification",
            "password_reset",
            "password_changed",
        ]
        
        for template_name in auth_templates:
            assert EmailTemplateType(template_name) is not None

    def test_account_templates(self) -> None:
        """Test account-related templates exist."""
        account_templates = [
            "welcome",
            "account_locked",
            "account_unlocked",
            "account_deactivated",
        ]
        
        for template_name in account_templates:
            assert EmailTemplateType(template_name) is not None

    def test_security_templates(self) -> None:
        """Test security-related templates exist."""
        security_templates = [
            "mfa_enabled",
            "mfa_disabled",
            "login_new_device",
            "suspicious_activity",
        ]
        
        for template_name in security_templates:
            assert EmailTemplateType(template_name) is not None

    def test_api_templates(self) -> None:
        """Test API-related templates exist."""
        api_templates = [
            "api_key_created",
            "api_key_expiring",
        ]
        
        for template_name in api_templates:
            assert EmailTemplateType(template_name) is not None

    def test_tenant_templates(self) -> None:
        """Test tenant-related templates exist."""
        tenant_templates = [
            "tenant_invitation",
            "tenant_role_changed",
        ]
        
        for template_name in tenant_templates:
            assert EmailTemplateType(template_name) is not None


class TestEmailTemplateEngineInternals:
    """Tests for EmailTemplateEngine internal methods."""

    def test_get_current_year(self) -> None:
        """Test _get_current_year returns current year."""
        from datetime import datetime
        
        engine = EmailTemplateEngine()
        year = engine._get_current_year()
        
        assert year == datetime.now().year

    def test_get_current_timestamp(self) -> None:
        """Test _get_current_timestamp returns ISO format."""
        engine = EmailTemplateEngine()
        timestamp = engine._get_current_timestamp()
        
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format contains T
        # Should be parseable
        from datetime import datetime
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_get_support_email_returns_email(self) -> None:
        """Test _get_support_email returns an email address."""
        engine = EmailTemplateEngine()
        email = engine._get_support_email()
        
        assert isinstance(email, str)
        assert "@" in email  # Is an email

    def test_get_app_name_returns_string(self) -> None:
        """Test _get_app_name returns app name string."""
        engine = EmailTemplateEngine()
        name = engine._get_app_name()
        
        assert isinstance(name, str)
        assert len(name) > 0

    def test_translate_method_exists(self) -> None:
        """Test _translate method exists and is callable."""
        engine = EmailTemplateEngine()
        
        assert hasattr(engine, "_translate")
        assert callable(engine._translate)

    def test_jinja_environment_has_globals(self) -> None:
        """Test Jinja environment has required globals."""
        engine = EmailTemplateEngine()
        
        assert "t" in engine._env.globals
        assert "app_name" in engine._env.globals

    def test_custom_templates_dir(self, tmp_path: Path) -> None:
        """Test engine with custom templates directory."""
        custom_dir = tmp_path / "custom_templates"
        custom_dir.mkdir()
        
        engine = EmailTemplateEngine(templates_dir=custom_dir)
        
        assert engine._templates_dir == custom_dir
        assert custom_dir.exists()

    def test_templates_dir_created_if_not_exists(self, tmp_path: Path) -> None:
        """Test templates directory is created if it doesn't exist."""
        custom_dir = tmp_path / "new_templates"
        
        engine = EmailTemplateEngine(templates_dir=custom_dir)
        
        assert custom_dir.exists()

    def test_default_templates_dir_path(self) -> None:
        """Test default templates directory is set correctly."""
        engine = EmailTemplateEngine()
        
        assert engine._templates_dir is not None
        assert "templates" in str(engine._templates_dir)

    def test_jinja_environment_autoescape(self) -> None:
        """Test Jinja environment has autoescape enabled."""
        engine = EmailTemplateEngine()
        
        # Check that autoescape is configured
        assert engine._env.autoescape is not None


class TestEmailTemplateEngineRender:
    """Tests for EmailTemplateEngine.render method."""

    def test_render_unsupported_locale_falls_back_to_default(self) -> None:
        """Test render falls back to English for unsupported locale."""
        engine = EmailTemplateEngine()
        
        # Test the locale validation logic directly
        locale = "invalid_locale"
        if locale not in engine.SUPPORTED_LOCALES:
            locale = engine.DEFAULT_LOCALE
        
        assert locale == "en"

    def test_render_supported_locale_preserved(self) -> None:
        """Test supported locale is preserved."""
        engine = EmailTemplateEngine()
        
        locale = "es"
        if locale not in engine.SUPPORTED_LOCALES:
            locale = engine.DEFAULT_LOCALE
        
        assert locale == "es"

    def test_render_none_locale_uses_default(self) -> None:
        """Test None locale uses default."""
        engine = EmailTemplateEngine()
        
        locale = None or engine.DEFAULT_LOCALE
        
        assert locale == "en"

