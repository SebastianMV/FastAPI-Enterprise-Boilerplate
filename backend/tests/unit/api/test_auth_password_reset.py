# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for auth endpoints - password reset flow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestForgotPasswordEndpoint:
    """Tests for forgot-password endpoint."""

    @pytest.mark.asyncio
    async def test_forgot_password_user_exists(self) -> None:
        """Test forgot password with existing user."""
        from app.api.v1.endpoints.auth import _password_reset_tokens, forgot_password
        from app.api.v1.schemas.auth import ForgotPasswordRequest
        from app.domain.value_objects.email import Email

        request = ForgotPasswordRequest(email="user@example.com")
        mock_session = MagicMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = Email("user@example.com")
        mock_user.first_name = "John"
        mock_user.is_active = True

        # Clear existing tokens
        _password_reset_tokens.clear()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            with patch("app.infrastructure.email.get_email_service") as mock_email:
                mock_service = MagicMock()
                mock_service.send_password_reset_email = AsyncMock()
                mock_email.return_value = mock_service

                result = await forgot_password(request, mock_session)

                assert result.success is True
                # Token should be created
                assert len(_password_reset_tokens) == 1

    @pytest.mark.asyncio
    async def test_forgot_password_user_not_found(self) -> None:
        """Test forgot password returns success even if user not found."""
        from app.api.v1.endpoints.auth import forgot_password
        from app.api.v1.schemas.auth import ForgotPasswordRequest

        request = ForgotPasswordRequest(email="notfound@example.com")
        mock_session = MagicMock()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_email = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            result = await forgot_password(request, mock_session)

            # Should still return success to prevent enumeration
            assert result.success is True

    @pytest.mark.asyncio
    async def test_forgot_password_inactive_user(self) -> None:
        """Test forgot password with inactive user doesn't send email."""
        from app.api.v1.endpoints.auth import _password_reset_tokens, forgot_password
        from app.api.v1.schemas.auth import ForgotPasswordRequest

        request = ForgotPasswordRequest(email="inactive@example.com")
        mock_session = MagicMock()

        mock_user = MagicMock()
        mock_user.is_active = False

        initial_token_count = len(_password_reset_tokens)

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            result = await forgot_password(request, mock_session)

            assert result.success is True
            # No new token should be created for inactive user
            assert len(_password_reset_tokens) == initial_token_count


class TestVerifyResetTokenEndpoint:
    """Tests for verify-reset-token endpoint."""

    @pytest.mark.asyncio
    async def test_verify_valid_token(self) -> None:
        """Test verifying a valid reset token."""
        from app.api.v1.endpoints.auth import _password_reset_tokens, verify_reset_token
        from app.api.v1.schemas.auth import VerifyResetTokenRequest

        # Create a valid token
        token = "valid-test-token-123"
        _password_reset_tokens[token] = {
            "user_id": uuid4(),
            "email": "user@example.com",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
        }

        request = VerifyResetTokenRequest(token=token)
        result = await verify_reset_token(request)

        assert result.success is True
        assert "valid" in result.message.lower()

        # Cleanup
        del _password_reset_tokens[token]

    @pytest.mark.asyncio
    async def test_verify_expired_token(self) -> None:
        """Test verifying an expired reset token."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import _password_reset_tokens, verify_reset_token
        from app.api.v1.schemas.auth import VerifyResetTokenRequest

        # Create an expired token
        token = "expired-test-token-456"
        _password_reset_tokens[token] = {
            "user_id": uuid4(),
            "email": "user@example.com",
            "expires_at": datetime.now(UTC) - timedelta(hours=1),
        }

        request = VerifyResetTokenRequest(token=token)

        with pytest.raises(HTTPException) as exc_info:
            await verify_reset_token(request)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "TOKEN_EXPIRED"

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self) -> None:
        """Test verifying a non-existent token."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import verify_reset_token
        from app.api.v1.schemas.auth import VerifyResetTokenRequest

        request = VerifyResetTokenRequest(token="nonexistent-token")

        with pytest.raises(HTTPException) as exc_info:
            await verify_reset_token(request)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "INVALID_TOKEN"


class TestResetPasswordEndpoint:
    """Tests for reset-password endpoint."""

    @pytest.mark.asyncio
    async def test_reset_password_success(self) -> None:
        """Test successful password reset."""
        from app.api.v1.endpoints.auth import _password_reset_tokens, reset_password
        from app.api.v1.schemas.auth import ResetPasswordRequest

        user_id = uuid4()
        token = "reset-success-token"
        _password_reset_tokens[token] = {
            "user_id": user_id,
            "email": "user@example.com",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
        }

        request = ResetPasswordRequest(
            token=token,
            new_password="NewPassword123!",
        )
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        mock_user = MagicMock()
        mock_user.email = "user@example.com"
        mock_user.first_name = "John"

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo.update = AsyncMock()
            mock_repo_class.return_value = mock_repo

            with patch("app.api.v1.endpoints.auth.hash_password") as mock_hash:
                mock_hash.return_value = "new-hashed-password"

                # Email service is imported inside the function
                with patch.object(
                    __import__(
                        "app.infrastructure.email", fromlist=["get_email_service"]
                    ),
                    "get_email_service",
                ) as mock_email:
                    mock_service = MagicMock()
                    mock_service.send_password_changed_email = AsyncMock()
                    mock_email.return_value = mock_service

                    result = await reset_password(request, mock_session)

                    assert result.success is True
                    # Token should be removed after use
                    assert token not in _password_reset_tokens

    @pytest.mark.asyncio
    async def test_reset_password_weak_password(self) -> None:
        """Test reset password with weak new password."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import _password_reset_tokens, reset_password
        from app.api.v1.schemas.auth import ResetPasswordRequest

        token = "reset-weak-token"
        _password_reset_tokens[token] = {
            "user_id": uuid4(),
            "email": "user@example.com",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
        }

        # This password will pass Pydantic validation but fail domain validation
        request = ResetPasswordRequest(
            token=token,
            new_password="weakpas1",  # 8 chars but weak
        )
        mock_session = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await reset_password(request, mock_session)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "WEAK_PASSWORD"

        # Cleanup
        if token in _password_reset_tokens:
            del _password_reset_tokens[token]

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self) -> None:
        """Test reset password when user no longer exists."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import _password_reset_tokens, reset_password
        from app.api.v1.schemas.auth import ResetPasswordRequest

        user_id = uuid4()
        token = "reset-user-gone-token"
        _password_reset_tokens[token] = {
            "user_id": user_id,
            "email": "user@example.com",
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
        }

        request = ResetPasswordRequest(
            token=token,
            new_password="NewPassword123!",
        )
        mock_session = MagicMock()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await reset_password(request, mock_session)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail["code"] == "USER_NOT_FOUND"

        # Cleanup
        if token in _password_reset_tokens:
            del _password_reset_tokens[token]


class TestAuthSchemas:
    """Extended tests for auth schemas."""

    def test_forgot_password_request(self) -> None:
        """Test ForgotPasswordRequest schema."""
        from app.api.v1.schemas.auth import ForgotPasswordRequest

        request = ForgotPasswordRequest(email="test@example.com")
        assert request.email == "test@example.com"

    def test_verify_reset_token_request(self) -> None:
        """Test VerifyResetTokenRequest schema."""
        from app.api.v1.schemas.auth import VerifyResetTokenRequest

        request = VerifyResetTokenRequest(token="test-token")
        assert request.token == "test-token"

    def test_reset_password_request(self) -> None:
        """Test ResetPasswordRequest schema."""
        from app.api.v1.schemas.auth import ResetPasswordRequest

        request = ResetPasswordRequest(
            token="token123",
            new_password="NewPassword123!",
        )
        assert request.token == "token123"
        assert request.new_password == "NewPassword123!"

    def test_refresh_token_request(self) -> None:
        """Test RefreshTokenRequest schema."""
        from app.api.v1.schemas.auth import RefreshTokenRequest

        request = RefreshTokenRequest(refresh_token="refresh-token-123")
        assert request.refresh_token == "refresh-token-123"

    def test_auth_response(self) -> None:
        """Test AuthResponse schema."""
        from app.api.v1.schemas.auth import AuthResponse, TokenResponse, UserResponse

        tokens = TokenResponse(
            access_token="access",
            refresh_token="refresh",
            token_type="bearer",
            expires_in=900,
        )
        user = UserResponse(
            id=uuid4(),
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=datetime.now(UTC),
            last_login=None,
        )

        response = AuthResponse(tokens=tokens, user=user)
        assert response.tokens.access_token == "access"
        assert response.user.email == "test@example.com"

    def test_change_password_request(self) -> None:
        """Test ChangePasswordRequest schema."""
        from app.api.v1.schemas.auth import ChangePasswordRequest

        request = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword456!",
        )
        assert request.current_password == "OldPassword123!"
        assert request.new_password == "NewPassword456!"
