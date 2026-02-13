# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for auth endpoints - password reset flow."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestForgotPasswordEndpoint:
    """Tests for forgot-password endpoint."""

    @pytest.mark.asyncio
    async def test_forgot_password_user_exists(self) -> None:
        """Test forgot password with existing user."""
        from app.api.v1.endpoints.auth import forgot_password
        from app.api.v1.schemas.auth import ForgotPasswordRequest
        from app.domain.value_objects.email import Email

        request = ForgotPasswordRequest(email="user@example.com")
        mock_session = MagicMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = Email("user@example.com")
        mock_user.first_name = "John"
        mock_user.is_active = True

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
                mock_cache = AsyncMock()
                mock_cache.get.return_value = None  # No rate limit
                mock_get_cache.return_value = mock_cache

                with patch(
                    "app.infrastructure.email.get_email_service"
                ) as mock_email:
                    mock_service = MagicMock()
                    mock_service.send_password_reset_email = AsyncMock()
                    mock_email.return_value = mock_service

                    result = await forgot_password(request, mock_session)

                    assert result.success is True
                    # Token should be stored in cache
                    mock_cache.set.assert_called()

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

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await forgot_password(request, mock_session)

            # Should still return success to prevent enumeration
            assert result.success is True

    @pytest.mark.asyncio
    async def test_forgot_password_inactive_user(self) -> None:
        """Test forgot password with inactive user doesn't send email."""
        from app.api.v1.endpoints.auth import forgot_password
        from app.api.v1.schemas.auth import ForgotPasswordRequest

        request = ForgotPasswordRequest(email="inactive@example.com")
        mock_session = MagicMock()

        mock_user = MagicMock()
        mock_user.is_active = False

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await forgot_password(request, mock_session)

            assert result.success is True


class TestVerifyResetTokenEndpoint:
    """Tests for verify-reset-token endpoint."""

    @pytest.mark.asyncio
    async def test_verify_valid_token(self) -> None:
        """Test verifying a valid reset token."""
        from app.api.v1.endpoints.auth import verify_reset_token
        from app.api.v1.schemas.auth import VerifyResetTokenRequest

        request = VerifyResetTokenRequest(token="valid-test-token-123")

        with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = {"user_id": str(uuid4())}
            mock_get_cache.return_value = mock_cache

            result = await verify_reset_token(request)

        assert result.success is True
        assert "valid" in result.message.lower()

    @pytest.mark.asyncio
    async def test_verify_expired_token(self) -> None:
        """Test verifying an expired reset token (Redis TTL expired = not in cache)."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import verify_reset_token
        from app.api.v1.schemas.auth import VerifyResetTokenRequest

        request = VerifyResetTokenRequest(token="expired-test-token-456")

        with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None  # Expired = removed by Redis TTL
            mock_get_cache.return_value = mock_cache

            with pytest.raises(HTTPException) as exc_info:
                await verify_reset_token(request)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "INVALID_TOKEN"

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self) -> None:
        """Test verifying a non-existent token."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import verify_reset_token
        from app.api.v1.schemas.auth import VerifyResetTokenRequest

        request = VerifyResetTokenRequest(token="nonexistent-token")

        with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            with pytest.raises(HTTPException) as exc_info:
                await verify_reset_token(request)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "INVALID_TOKEN"


class TestResetPasswordEndpoint:
    """Tests for reset-password endpoint."""

    @pytest.mark.asyncio
    async def test_reset_password_success(self) -> None:
        """Test successful password reset."""
        from app.api.v1.endpoints.auth import reset_password
        from app.api.v1.schemas.auth import ResetPasswordRequest

        user_id = uuid4()
        request = ResetPasswordRequest(
            token="reset-success-token",
            new_password="NewPassword123!",
        )
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "user@example.com"
        mock_user.first_name = "John"

        with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get_and_delete.return_value = {"user_id": str(user_id)}
            mock_cache.delete = AsyncMock()
            mock_get_cache.return_value = mock_cache

            with patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_id = AsyncMock(return_value=mock_user)
                mock_repo.update = AsyncMock()
                mock_repo_class.return_value = mock_repo

                with (
                    patch(
                        "app.api.v1.endpoints.auth.hash_password",
                        return_value="new-hashed-password",
                    ),
                    patch(
                        "app.infrastructure.database.repositories.session_repository.SQLAlchemySessionRepository"
                    ) as mock_session_repo_cls,
                    patch(
                        "app.infrastructure.email.get_email_service"
                    ) as mock_email,
                ):
                    mock_session_repo = AsyncMock()
                    mock_session_repo_cls.return_value = mock_session_repo

                    mock_service = MagicMock()
                    mock_service.send_password_changed_email = AsyncMock()
                    mock_email.return_value = mock_service

                    result = await reset_password(request, mock_session)

                    assert result.success is True

    @pytest.mark.asyncio
    async def test_reset_password_weak_password(self) -> None:
        """Test reset password with weak new password."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import reset_password
        from app.api.v1.schemas.auth import ResetPasswordRequest

        # This password will pass Pydantic validation but fail domain validation
        request = ResetPasswordRequest(
            token="reset-weak-token",
            new_password="weakpas1",  # 8 chars but weak
        )
        mock_session = MagicMock()

        with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get_and_delete.return_value = {
                "user_id": str(uuid4()),
            }
            mock_get_cache.return_value = mock_cache

            with patch(
                "app.api.v1.endpoints.auth.Password",
                side_effect=ValueError("Weak password"),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await reset_password(request, mock_session)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "WEAK_PASSWORD"

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self) -> None:
        """Test reset password when user no longer exists."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import reset_password
        from app.api.v1.schemas.auth import ResetPasswordRequest

        user_id = uuid4()
        request = ResetPasswordRequest(
            token="reset-user-gone-token",
            new_password="NewPassword123!",
        )
        mock_session = MagicMock()

        with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get_and_delete.return_value = {
                "user_id": str(user_id),
            }
            mock_get_cache.return_value = mock_cache

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
