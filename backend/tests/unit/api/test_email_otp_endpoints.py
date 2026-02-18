# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Email OTP API endpoints.

Tests for Email-based One-Time Password endpoints in MFA router.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


class TestRequestEmailOTPEndpoint:
    """Tests for /mfa/email-otp/request endpoint."""

    @pytest.mark.asyncio
    async def test_request_email_otp_success(self) -> None:
        """Test successful email OTP request."""
        from app.api.v1.endpoints.mfa import request_email_otp

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"

        mock_otp_handler = MagicMock()
        mock_otp_handler.can_generate_otp = AsyncMock(return_value=(True, 0))
        mock_otp_handler.generate_otp = AsyncMock(return_value="123456")
        mock_otp_handler.OTP_EXPIRY_MINUTES = 10

        mock_email_service = AsyncMock()

        with (
            patch(
                "app.api.v1.endpoints.mfa.get_email_otp_handler",
                return_value=mock_otp_handler,
            ),
            patch(
                "app.api.v1.endpoints.mfa.get_email_service",
                return_value=mock_email_service,
            ),
        ):
            result = await request_email_otp(current_user=mock_user)

        assert result.success is True
        assert result.expires_in_minutes == 10
        assert "sent" in result.message.lower()

        # Verify email was sent
        mock_email_service.send_template_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_email_otp_cooldown(self) -> None:
        """Test email OTP request blocked by cooldown."""
        from app.api.v1.endpoints.mfa import request_email_otp

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_otp_handler = MagicMock()
        mock_otp_handler.can_generate_otp = AsyncMock(return_value=(False, 30))

        with (
            patch(
                "app.api.v1.endpoints.mfa.get_email_otp_handler",
                return_value=mock_otp_handler,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await request_email_otp(current_user=mock_user)

        assert exc_info.value.status_code == 429
        assert "OTP_COOLDOWN" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_request_email_otp_generation_failed(self) -> None:
        """Test email OTP request when generation fails."""
        from app.api.v1.endpoints.mfa import request_email_otp

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_otp_handler = MagicMock()
        mock_otp_handler.can_generate_otp = AsyncMock(return_value=(True, 0))
        mock_otp_handler.generate_otp = AsyncMock(
            return_value=None
        )  # Generation failed

        with (
            patch(
                "app.api.v1.endpoints.mfa.get_email_otp_handler",
                return_value=mock_otp_handler,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await request_email_otp(current_user=mock_user)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_request_email_otp_uses_full_name(self) -> None:
        """Test email OTP uses full_name when available."""
        from app.api.v1.endpoints.mfa import request_email_otp

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "john@example.com"
        mock_user.full_name = "John Doe"

        mock_otp_handler = MagicMock()
        mock_otp_handler.can_generate_otp = AsyncMock(return_value=(True, 0))
        mock_otp_handler.generate_otp = AsyncMock(return_value="123456")
        mock_otp_handler.OTP_EXPIRY_MINUTES = 10

        mock_email_service = AsyncMock()

        with (
            patch(
                "app.api.v1.endpoints.mfa.get_email_otp_handler",
                return_value=mock_otp_handler,
            ),
            patch(
                "app.api.v1.endpoints.mfa.get_email_service",
                return_value=mock_email_service,
            ),
        ):
            await request_email_otp(current_user=mock_user)

        call_kwargs = mock_email_service.send_template_email.call_args[1]
        assert call_kwargs["to_name"] == "John Doe"
        assert call_kwargs["context"]["recipient_name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_request_email_otp_fallback_to_email_prefix(self) -> None:
        """Test email OTP falls back to email prefix when no name."""
        from app.api.v1.endpoints.mfa import request_email_otp

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "testuser@example.com"
        mock_user.full_name = None  # No full name

        mock_otp_handler = MagicMock()
        mock_otp_handler.can_generate_otp = AsyncMock(return_value=(True, 0))
        mock_otp_handler.generate_otp = AsyncMock(return_value="123456")
        mock_otp_handler.OTP_EXPIRY_MINUTES = 10

        mock_email_service = AsyncMock()

        with (
            patch(
                "app.api.v1.endpoints.mfa.get_email_otp_handler",
                return_value=mock_otp_handler,
            ),
            patch(
                "app.api.v1.endpoints.mfa.get_email_service",
                return_value=mock_email_service,
            ),
        ):
            await request_email_otp(current_user=mock_user)

        call_kwargs = mock_email_service.send_template_email.call_args[1]
        assert call_kwargs["to_name"] == "testuser"


class TestVerifyEmailOTPEndpoint:
    """Tests for /mfa/email-otp/verify endpoint."""

    @pytest.mark.asyncio
    async def test_verify_email_otp_success(self) -> None:
        """Test successful email OTP verification."""
        from app.api.v1.endpoints.mfa import verify_email_otp
        from app.api.v1.schemas.mfa import EmailOTPVerifyRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_otp_handler = MagicMock()
        mock_otp_handler.get_remaining_attempts = AsyncMock(return_value=3)
        mock_otp_handler.verify_otp = AsyncMock(return_value=True)

        request = EmailOTPVerifyRequest(code="123456")

        with patch(
            "app.api.v1.endpoints.mfa.get_email_otp_handler",
            return_value=mock_otp_handler,
        ):
            result = await verify_email_otp(request=request, current_user=mock_user)

        assert result.success is True
        assert "successful" in result.message.lower()

    @pytest.mark.asyncio
    async def test_verify_email_otp_no_pending(self) -> None:
        """Test verification fails when no pending OTP."""
        from app.api.v1.endpoints.mfa import verify_email_otp
        from app.api.v1.schemas.mfa import EmailOTPVerifyRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_otp_handler = MagicMock()
        mock_otp_handler.get_remaining_attempts = AsyncMock(
            return_value=0
        )  # No pending OTP

        request = EmailOTPVerifyRequest(code="123456")

        with (
            patch(
                "app.api.v1.endpoints.mfa.get_email_otp_handler",
                return_value=mock_otp_handler,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await verify_email_otp(request=request, current_user=mock_user)

        assert exc_info.value.status_code == 400
        assert "NO_PENDING_OTP" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_email_otp_invalid_code(self) -> None:
        """Test verification fails for invalid code."""
        from app.api.v1.endpoints.mfa import verify_email_otp
        from app.api.v1.schemas.mfa import EmailOTPVerifyRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_otp_handler = MagicMock()
        mock_otp_handler.get_remaining_attempts = AsyncMock(return_value=3)
        mock_otp_handler.verify_otp = AsyncMock(return_value=False)

        request = EmailOTPVerifyRequest(code="000000")

        with (
            patch(
                "app.api.v1.endpoints.mfa.get_email_otp_handler",
                return_value=mock_otp_handler,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await verify_email_otp(request=request, current_user=mock_user)

        assert exc_info.value.status_code == 400
        assert "INVALID_CODE" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_email_otp_shows_remaining_attempts(self) -> None:
        """Test verification error shows remaining attempts."""
        from app.api.v1.endpoints.mfa import verify_email_otp
        from app.api.v1.schemas.mfa import EmailOTPVerifyRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_otp_handler = MagicMock()
        mock_otp_handler.get_remaining_attempts = AsyncMock(return_value=2)
        mock_otp_handler.verify_otp = AsyncMock(return_value=False)

        request = EmailOTPVerifyRequest(code="111111")

        with (
            patch(
                "app.api.v1.endpoints.mfa.get_email_otp_handler",
                return_value=mock_otp_handler,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await verify_email_otp(request=request, current_user=mock_user)

        assert exc_info.value.status_code == 400
        assert "INVALID_CODE" in str(exc_info.value.detail)


class TestEmailOTPSchemas:
    """Tests for Email OTP request/response schemas."""

    def test_email_otp_request_response_schema(self) -> None:
        """Test EmailOTPRequestResponse schema."""
        from app.api.v1.schemas.mfa import EmailOTPRequestResponse

        response = EmailOTPRequestResponse(
            success=True,
            message="Code sent",
            expires_in_minutes=10,
        )

        assert response.success is True
        assert response.message == "Code sent"
        assert response.expires_in_minutes == 10

    def test_email_otp_verify_request_schema(self) -> None:
        """Test EmailOTPVerifyRequest schema."""
        from app.api.v1.schemas.mfa import EmailOTPVerifyRequest

        request = EmailOTPVerifyRequest(code="123456")
        assert request.code == "123456"

    def test_email_otp_verify_request_validation(self) -> None:
        """Test EmailOTPVerifyRequest validates code length."""
        from pydantic import ValidationError

        from app.api.v1.schemas.mfa import EmailOTPVerifyRequest

        # Valid code
        request = EmailOTPVerifyRequest(code="123456")
        assert request.code == "123456"

        # Code too long should fail validation
        with pytest.raises(ValidationError):
            EmailOTPVerifyRequest(code="1234567")

        # Code too short should fail validation
        with pytest.raises(ValidationError):
            EmailOTPVerifyRequest(code="12345")

    def test_email_otp_verify_response_schema(self) -> None:
        """Test EmailOTPVerifyResponse schema."""
        from app.api.v1.schemas.mfa import EmailOTPVerifyResponse

        response = EmailOTPVerifyResponse(
            success=True,
            message="Verified",
        )

        assert response.success is True
        assert response.message == "Verified"


class TestEmailOTPIntegration:
    """Integration-style tests for Email OTP flow."""

    @pytest.mark.asyncio
    async def test_full_email_otp_flow(self) -> None:
        """Test complete email OTP request → verify flow."""
        from app.api.v1.endpoints.mfa import request_email_otp, verify_email_otp
        from app.api.v1.schemas.mfa import EmailOTPVerifyRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"

        generated_code = "987654"

        mock_otp_handler = MagicMock()
        mock_otp_handler.can_generate_otp = AsyncMock(return_value=(True, 0))
        mock_otp_handler.generate_otp = AsyncMock(return_value=generated_code)
        mock_otp_handler.OTP_EXPIRY_MINUTES = 10
        mock_otp_handler.get_remaining_attempts = AsyncMock(return_value=3)
        mock_otp_handler.verify_otp = AsyncMock(return_value=True)

        mock_email_service = AsyncMock()

        with (
            patch(
                "app.api.v1.endpoints.mfa.get_email_otp_handler",
                return_value=mock_otp_handler,
            ),
            patch(
                "app.api.v1.endpoints.mfa.get_email_service",
                return_value=mock_email_service,
            ),
        ):
            # Step 1: Request OTP
            request_result = await request_email_otp(current_user=mock_user)
            assert request_result.success is True

            # Verify email was sent with the code
            email_context = mock_email_service.send_template_email.call_args[1][
                "context"
            ]
            assert email_context["otp_code"] == generated_code

            # Step 2: Verify OTP
            verify_request = EmailOTPVerifyRequest(code=generated_code)
            verify_result = await verify_email_otp(
                request=verify_request, current_user=mock_user
            )
            assert verify_result.success is True

    @pytest.mark.asyncio
    async def test_email_otp_retry_after_failure(self) -> None:
        """Test email OTP allows retry after failed attempt."""
        from app.api.v1.endpoints.mfa import verify_email_otp
        from app.api.v1.schemas.mfa import EmailOTPVerifyRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_otp_handler = MagicMock()
        mock_otp_handler.get_remaining_attempts = AsyncMock(side_effect=[3, 2, 2])
        mock_otp_handler.verify_otp = AsyncMock(side_effect=[False, True])

        with patch(
            "app.api.v1.endpoints.mfa.get_email_otp_handler",
            return_value=mock_otp_handler,
        ):
            # First attempt - wrong code
            try:
                await verify_email_otp(
                    request=EmailOTPVerifyRequest(code="000000"),
                    current_user=mock_user,
                )
            except HTTPException:
                pass  # Expected

            # Second attempt - correct code
            result = await verify_email_otp(
                request=EmailOTPVerifyRequest(code="123456"),
                current_user=mock_user,
            )
            assert result.success is True
