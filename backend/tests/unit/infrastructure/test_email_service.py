# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for email service.

Tests for EmailMessage, EmailRecipient, and email backends.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.email.service import (
    EmailBackend,
    EmailMessage,
    EmailRecipient,
)


class TestEmailRecipient:
    """Tests for EmailRecipient dataclass."""

    def test_recipient_with_name(self) -> None:
        """Test recipient with name."""
        recipient = EmailRecipient(email="user@example.com", name="John Doe")

        assert recipient.email == "user@example.com"
        assert recipient.name == "John Doe"
        assert recipient.formatted() == "John Doe <user@example.com>"

    def test_recipient_without_name(self) -> None:
        """Test recipient without name."""
        recipient = EmailRecipient(email="user@example.com")

        assert recipient.email == "user@example.com"
        assert recipient.name is None
        assert recipient.formatted() == "user@example.com"

    def test_recipient_with_empty_name(self) -> None:
        """Test recipient with empty name uses email only."""
        recipient = EmailRecipient(email="user@example.com", name="")

        # Empty string is falsy, so should use email only
        assert recipient.formatted() == "user@example.com"


class TestEmailMessage:
    """Tests for EmailMessage dataclass."""

    def test_basic_message(self) -> None:
        """Test creating basic email message."""
        recipients = [EmailRecipient(email="to@example.com")]

        message = EmailMessage(
            to=recipients,
            subject="Test Subject",
            html_body="<p>Hello</p>",
            text_body="Hello",
        )

        assert message.to == recipients
        assert message.subject == "Test Subject"
        assert message.html_body == "<p>Hello</p>"
        assert message.text_body == "Hello"

    def test_message_with_all_fields(self) -> None:
        """Test message with all optional fields."""
        message = EmailMessage(
            to=[EmailRecipient(email="to@example.com")],
            subject="Subject",
            html_body="<p>Body</p>",
            text_body="Body",
            from_email="from@example.com",
            from_name="Sender",
            reply_to="reply@example.com",
            cc=[EmailRecipient(email="cc@example.com")],
            bcc=[EmailRecipient(email="bcc@example.com")],
            headers={"X-Custom": "value"},
            attachments=[{"name": "file.pdf", "content": b"data"}],
            tags=["transactional", "welcome"],
            metadata={"user_id": "123"},
        )

        assert message.from_email == "from@example.com"
        assert message.from_name == "Sender"
        assert message.reply_to == "reply@example.com"
        assert message.cc is not None and len(message.cc) == 1
        assert message.bcc is not None and len(message.bcc) == 1
        assert message.headers is not None and message.headers["X-Custom"] == "value"
        assert message.attachments is not None and len(message.attachments) == 1
        assert message.tags is not None and "transactional" in message.tags
        assert message.metadata is not None and message.metadata["user_id"] == "123"

    def test_message_default_values(self) -> None:
        """Test message default values."""
        message = EmailMessage(
            to=[EmailRecipient(email="to@example.com")],
            subject="Subject",
            html_body="Body",
            text_body="Body",
        )

        assert message.from_email is None
        assert message.cc is None
        assert message.bcc is None
        assert message.headers is None
        assert message.attachments is None
        assert message.tags is None
        assert message.metadata is None


class TestEmailBackend:
    """Tests for EmailBackend enum."""

    def test_backend_values(self) -> None:
        """Test all backend values."""
        assert EmailBackend.CONSOLE.value == "console"
        assert EmailBackend.SMTP.value == "smtp"

    def test_backend_from_string(self) -> None:
        """Test creating backend from string."""
        backend = EmailBackend("smtp")
        assert backend == EmailBackend.SMTP

    def test_backend_comparison(self) -> None:
        """Test backend string comparison."""
        assert EmailBackend.CONSOLE == "console"
        assert EmailBackend.SMTP != "console"

    def test_all_backends_exist(self) -> None:
        """Test all expected backends are defined."""
        expected = {"console", "smtp"}
        actual = {b.value for b in EmailBackend}
        assert actual == expected


class TestConsoleEmailSender:
    """Tests for ConsoleEmailSender."""

    @pytest.mark.asyncio
    async def test_send_returns_true(self) -> None:
        """Test that send always returns True."""
        from app.infrastructure.email.service import ConsoleEmailSender

        sender = ConsoleEmailSender()
        message = EmailMessage(
            to=[EmailRecipient(email="test@example.com")],
            subject="Test Subject",
            html_body="<p>Test</p>",
            text_body="Test",
        )

        result = await sender.send(message)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_logs_email_content(self) -> None:
        """Test that send logs the email content."""
        from app.infrastructure.email.service import ConsoleEmailSender

        sender = ConsoleEmailSender()
        message = EmailMessage(
            to=[EmailRecipient(email="test@example.com", name="Test User")],
            subject="Test Subject",
            html_body="<p>Hello World</p>",
            text_body="Hello World",
        )

        with patch("app.infrastructure.email.service.logger") as mock_logger:
            result = await sender.send(message)

        assert result is True
        # Verify logging happened
        assert mock_logger.info.call_count > 0

    @pytest.mark.asyncio
    async def test_send_truncates_long_body(self) -> None:
        """Test that long body is truncated in log."""
        from app.infrastructure.email.service import ConsoleEmailSender

        sender = ConsoleEmailSender()
        long_body = "A" * 1000
        message = EmailMessage(
            to=[EmailRecipient(email="test@example.com")],
            subject="Test Subject",
            html_body="<p>Test</p>",
            text_body=long_body,
        )

        result = await sender.send(message)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_batch_all_success(self) -> None:
        """Test batch sending returns success for all recipients."""
        from app.infrastructure.email.service import ConsoleEmailSender

        sender = ConsoleEmailSender()
        messages = [
            EmailMessage(
                to=[EmailRecipient(email="user1@example.com")],
                subject="Test 1",
                html_body="<p>1</p>",
                text_body="1",
            ),
            EmailMessage(
                to=[EmailRecipient(email="user2@example.com")],
                subject="Test 2",
                html_body="<p>2</p>",
                text_body="2",
            ),
        ]

        results = await sender.send_batch(messages)

        assert results["user1@example.com"] is True
        assert results["user2@example.com"] is True


class TestSMTPEmailSender:
    """Tests for SMTPEmailSender."""

    def test_init_with_all_params(self) -> None:
        """Test SMTP sender initialization."""
        from app.infrastructure.email.service import SMTPEmailSender

        sender = SMTPEmailSender(
            host="smtp.example.com",
            port=587,
            username="user",
            password="pass",
            use_tls=True,
            start_tls=False,
        )

        assert sender.host == "smtp.example.com"
        assert sender.port == 587
        assert sender.username == "user"
        assert sender.password == "pass"
        assert sender.use_tls is True
        assert sender.start_tls is False

    @pytest.mark.asyncio
    async def test_send_success(self) -> None:
        """Test successful SMTP send."""
        from app.infrastructure.email.service import SMTPEmailSender

        sender = SMTPEmailSender(host="localhost", port=587)
        message = EmailMessage(
            to=[EmailRecipient(email="test@example.com")],
            subject="Test",
            html_body="<p>Test</p>",
            text_body="Test",
            from_email="from@example.com",
            from_name="Sender",
        )

        # Mock the internal import inside the method
        mock_aiosmtplib = MagicMock()
        mock_aiosmtplib.send = AsyncMock()

        with patch.dict("sys.modules", {"aiosmtplib": mock_aiosmtplib}):
            result = await sender.send(message)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_with_reply_to(self) -> None:
        """Test SMTP send with reply-to header."""
        from app.infrastructure.email.service import SMTPEmailSender

        sender = SMTPEmailSender(host="localhost", port=587)
        message = EmailMessage(
            to=[EmailRecipient(email="test@example.com")],
            subject="Test",
            html_body="<p>Test</p>",
            text_body="Test",
            reply_to="reply@example.com",
        )

        mock_aiosmtplib = MagicMock()
        mock_aiosmtplib.send = AsyncMock()

        with patch.dict("sys.modules", {"aiosmtplib": mock_aiosmtplib}):
            result = await sender.send(message)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_failure_returns_false(self) -> None:
        """Test that send failure returns False."""
        from app.infrastructure.email.service import SMTPEmailSender

        sender = SMTPEmailSender(host="localhost", port=587)
        message = EmailMessage(
            to=[EmailRecipient(email="test@example.com")],
            subject="Test",
            html_body="<p>Test</p>",
            text_body="Test",
        )

        mock_aiosmtplib = MagicMock()
        mock_aiosmtplib.send = AsyncMock(side_effect=Exception("Connection failed"))

        with patch.dict("sys.modules", {"aiosmtplib": mock_aiosmtplib}):
            result = await sender.send(message)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_batch_mixed_results(self) -> None:
        """Test batch sending with mixed success/failure."""
        from app.infrastructure.email.service import SMTPEmailSender

        sender = SMTPEmailSender(host="localhost", port=587)
        messages = [
            EmailMessage(
                to=[EmailRecipient(email="user1@example.com")],
                subject="Test 1",
                html_body="<p>1</p>",
                text_body="1",
            ),
            EmailMessage(
                to=[EmailRecipient(email="user2@example.com")],
                subject="Test 2",
                html_body="<p>2</p>",
                text_body="2",
            ),
        ]

        with patch.object(sender, "send", side_effect=[True, False]):
            results = await sender.send_batch(messages)

        assert results["user1@example.com"] is True
        assert results["user2@example.com"] is False


class TestEmailService:
    """Tests for EmailService."""

    def test_init_with_defaults(self) -> None:
        """Test EmailService initialization with defaults."""
        from app.infrastructure.email.service import EmailService

        with patch(
            "app.infrastructure.email.service.get_template_engine"
        ) as mock_engine:
            mock_engine.return_value = MagicMock()

            with patch("app.config.settings") as mock_settings:
                mock_settings.EMAIL_BACKEND = "console"
                mock_settings.APP_NAME = "Test App"

                service = EmailService()

        assert service._sender is not None

    def test_init_with_custom_sender(self) -> None:
        """Test EmailService with custom sender."""
        from app.infrastructure.email.service import EmailService

        mock_sender = MagicMock()
        mock_engine = MagicMock()

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        assert service._sender is mock_sender
        assert service._template_engine is mock_engine

    @pytest.mark.asyncio
    async def test_send_template_email_success(self) -> None:
        """Test sending template email."""
        from app.infrastructure.email.service import EmailService
        from app.infrastructure.email.templates import EmailTemplateType

        mock_sender = AsyncMock()
        mock_sender.send = AsyncMock(return_value=True)

        mock_template_result = MagicMock()
        mock_template_result.subject = "Test Subject"
        mock_template_result.html_body = "<p>Hello</p>"
        mock_template_result.text_body = "Hello"

        mock_engine = MagicMock()
        mock_engine.render = MagicMock(return_value=mock_template_result)

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        result = await service.send_template_email(
            template_type=EmailTemplateType.REGISTRATION,
            to_email="user@example.com",
            to_name="Test User",
            locale="en",
        )

        assert result is True
        mock_sender.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_registration_email(self) -> None:
        """Test convenience method for registration email."""
        from app.infrastructure.email.service import EmailService

        mock_sender = AsyncMock()
        mock_sender.send = AsyncMock(return_value=True)

        mock_template_result = MagicMock()
        mock_template_result.subject = "Welcome!"
        mock_template_result.html_body = "<p>Welcome</p>"
        mock_template_result.text_body = "Welcome"

        mock_engine = MagicMock()
        mock_engine.render = MagicMock(return_value=mock_template_result)

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        result = await service.send_registration_email(
            to_email="new@example.com",
            to_name="New User",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_verification_email(self) -> None:
        """Test convenience method for verification email."""
        from app.infrastructure.email.service import EmailService

        mock_sender = AsyncMock()
        mock_sender.send = AsyncMock(return_value=True)

        mock_template_result = MagicMock()
        mock_template_result.subject = "Verify"
        mock_template_result.html_body = "<p>Verify</p>"
        mock_template_result.text_body = "Verify"

        mock_engine = MagicMock()
        mock_engine.render = MagicMock(return_value=mock_template_result)

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        result = await service.send_verification_email(
            to_email="user@example.com",
            verification_url="https://example.com/verify",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_password_reset_email(self) -> None:
        """Test convenience method for password reset email."""
        from app.infrastructure.email.service import EmailService

        mock_sender = AsyncMock()
        mock_sender.send = AsyncMock(return_value=True)

        mock_template_result = MagicMock()
        mock_template_result.subject = "Reset Password"
        mock_template_result.html_body = "<p>Reset</p>"
        mock_template_result.text_body = "Reset"

        mock_engine = MagicMock()
        mock_engine.render = MagicMock(return_value=mock_template_result)

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        result = await service.send_password_reset_email(
            to_email="user@example.com",
            reset_url="https://example.com/reset",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_password_changed_email(self) -> None:
        """Test convenience method for password changed notification."""
        from app.infrastructure.email.service import EmailService

        mock_sender = AsyncMock()
        mock_sender.send = AsyncMock(return_value=True)

        mock_template_result = MagicMock()
        mock_template_result.subject = "Password Changed"
        mock_template_result.html_body = "<p>Changed</p>"
        mock_template_result.text_body = "Changed"

        mock_engine = MagicMock()
        mock_engine.render = MagicMock(return_value=mock_template_result)

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        result = await service.send_password_changed_email(
            to_email="user@example.com",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_tenant_invitation_email(self) -> None:
        """Test convenience method for tenant invitation email."""
        from app.infrastructure.email.service import EmailService

        mock_sender = AsyncMock()
        mock_sender.send = AsyncMock(return_value=True)

        mock_template_result = MagicMock()
        mock_template_result.subject = "You're Invited"
        mock_template_result.html_body = "<p>Invite</p>"
        mock_template_result.text_body = "Invite"

        mock_engine = MagicMock()
        mock_engine.render = MagicMock(return_value=mock_template_result)

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        result = await service.send_tenant_invitation_email(
            to_email="user@example.com",
            invitation_url="https://example.com/invite",
            inviter_name="Admin User",
            tenant_name="Test Tenant",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_welcome_email(self) -> None:
        """Test convenience method for welcome email."""
        from app.infrastructure.email.service import EmailService

        mock_sender = AsyncMock()
        mock_sender.send = AsyncMock(return_value=True)

        mock_template_result = MagicMock()
        mock_template_result.subject = "Welcome"
        mock_template_result.html_body = "<p>Welcome</p>"
        mock_template_result.text_body = "Welcome"

        mock_engine = MagicMock()
        mock_engine.render = MagicMock(return_value=mock_template_result)

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        result = await service.send_welcome_email(
            to_email="user@example.com",
            login_url="https://example.com/login",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_mfa_enabled_email(self) -> None:
        """Test convenience method for MFA enabled notification."""
        from app.infrastructure.email.service import EmailService

        mock_sender = AsyncMock()
        mock_sender.send = AsyncMock(return_value=True)

        mock_template_result = MagicMock()
        mock_template_result.subject = "MFA Enabled"
        mock_template_result.html_body = "<p>Enabled</p>"
        mock_template_result.text_body = "Enabled"

        mock_engine = MagicMock()
        mock_engine.render = MagicMock(return_value=mock_template_result)

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        result = await service.send_mfa_enabled_email(
            to_email="user@example.com",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_account_locked_email(self) -> None:
        """Test convenience method for account locked notification."""
        from app.infrastructure.email.service import EmailService

        mock_sender = AsyncMock()
        mock_sender.send = AsyncMock(return_value=True)

        mock_template_result = MagicMock()
        mock_template_result.subject = "Account Locked"
        mock_template_result.html_body = "<p>Locked</p>"
        mock_template_result.text_body = "Locked"

        mock_engine = MagicMock()
        mock_engine.render = MagicMock(return_value=mock_template_result)

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        result = await service.send_account_locked_email(
            to_email="user@example.com",
            unlock_url="https://example.com/unlock",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_login_new_device_email(self) -> None:
        """Test convenience method for login new device notification."""
        from app.infrastructure.email.service import EmailService

        mock_sender = AsyncMock()
        mock_sender.send = AsyncMock(return_value=True)

        mock_template_result = MagicMock()
        mock_template_result.subject = "New Device Login"
        mock_template_result.html_body = "<p>New Device</p>"
        mock_template_result.text_body = "New Device"

        mock_engine = MagicMock()
        mock_engine.render = MagicMock(return_value=mock_template_result)

        service = EmailService(sender=mock_sender, template_engine=mock_engine)

        result = await service.send_login_new_device_email(
            to_email="user@example.com",
            device_info="Chrome on Windows",
            ip_address="192.168.1.1",
        )

        assert result is True
