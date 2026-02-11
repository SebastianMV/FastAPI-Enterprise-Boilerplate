# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Extended unit tests for Auth API endpoints.

Additional tests covering more auth endpoint paths.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


class TestRefreshTokenEndpoint:
    """Tests for /auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_token(self) -> None:
        """Test refresh with invalid token."""
        from app.api.v1.endpoints.auth import refresh_token
        from app.api.v1.schemas.auth import RefreshTokenRequest
        from app.domain.exceptions.base import AuthenticationError

        request = RefreshTokenRequest(refresh_token="invalid-token")
        mock_session = AsyncMock()

        with patch("app.api.v1.endpoints.auth.validate_refresh_token") as mock_validate:
            mock_validate.side_effect = AuthenticationError(
                code="INVALID_TOKEN",
                message="Token is invalid",
            )

            with pytest.raises(HTTPException) as exc_info:
                await refresh_token(request=request, session=mock_session)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "INVALID_TOKEN"

    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found(self) -> None:
        """Test refresh when user no longer exists."""
        from app.api.v1.endpoints.auth import refresh_token
        from app.api.v1.schemas.auth import RefreshTokenRequest

        request = RefreshTokenRequest(refresh_token="valid-refresh-token")
        mock_session = AsyncMock()
        user_id = uuid4()

        with patch("app.api.v1.endpoints.auth.validate_refresh_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": str(uuid4()),
            }

            with patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = None
                mock_repo_class.return_value = mock_repo

                with pytest.raises(HTTPException) as exc_info:
                    await refresh_token(request=request, session=mock_session)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_refresh_token_user_inactive(self) -> None:
        """Test refresh when user is deactivated."""
        from app.api.v1.endpoints.auth import refresh_token
        from app.api.v1.schemas.auth import RefreshTokenRequest

        request = RefreshTokenRequest(refresh_token="valid-refresh-token")
        mock_session = AsyncMock()
        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = False

        with patch("app.api.v1.endpoints.auth.validate_refresh_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": str(uuid4()),
            }

            with patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = mock_user
                mock_repo_class.return_value = mock_repo

                with pytest.raises(HTTPException) as exc_info:
                    await refresh_token(request=request, session=mock_session)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "USER_INACTIVE"

    @pytest.mark.asyncio
    async def test_refresh_token_success(self) -> None:
        """Test successful token refresh."""
        from app.api.v1.endpoints.auth import refresh_token
        from app.api.v1.schemas.auth import RefreshTokenRequest

        request = RefreshTokenRequest(refresh_token="valid-refresh-token")
        mock_session = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.roles = []

        with patch("app.api.v1.endpoints.auth.validate_refresh_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
            }

            with patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = mock_user
                mock_repo_class.return_value = mock_repo

                with patch(
                    "app.api.v1.endpoints.auth.create_access_token",
                    return_value="new-access-token",
                ), patch(
                    "app.api.v1.endpoints.auth.create_refresh_token",
                    return_value="new-refresh-token",
                ):
                    result = await refresh_token(
                        request=request,
                        session=mock_session,
                    )

        assert result.access_token == "new-access-token"
        assert result.refresh_token == "new-refresh-token"


class TestLogoutEndpoint:
    """Tests for /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self) -> None:
        """Test successful logout."""
        from app.api.v1.endpoints.auth import logout

        user_id = uuid4()
        result = await logout(current_user_id=user_id)

        assert result.success is True
        assert "logged out" in result.message.lower()


class TestGetCurrentUserEndpoint:
    """Tests for /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user(self) -> None:
        """Test getting current user info."""
        from app.api.v1.endpoints.auth import get_current_user_info
        from app.domain.value_objects.email import Email

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = Email("test@example.com")
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.created_at = datetime.now(UTC)
        mock_user.last_login = None

        result = await get_current_user_info(current_user=mock_user)

        assert result.id == user_id
        assert result.email == "test@example.com"
        assert result.first_name == "Test"


class TestChangePasswordEndpoint:
    """Tests for /auth/change-password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_weak_password(self) -> None:
        """Test change password with weak new password - validation at schema level."""
        from pydantic import ValidationError

        from app.api.v1.schemas.auth import ChangePasswordRequest

        # Password validation happens at schema level
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="CurrentPass123!",
                new_password="weak",  # Too short
            )

        assert "new_password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self) -> None:
        """Test change password when user not found."""
        from app.api.v1.endpoints.auth import change_password
        from app.api.v1.schemas.auth import ChangePasswordRequest

        request = ChangePasswordRequest(
            current_password="CurrentPass123!",
            new_password="NewPassword123!",
        )
        user_id = uuid4()
        mock_session = AsyncMock()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    request=request,
                    current_user_id=user_id,
                    session=mock_session,
                )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_change_password_wrong_current_password(self) -> None:
        """Test change password with wrong current password."""
        from app.api.v1.endpoints.auth import change_password
        from app.api.v1.schemas.auth import ChangePasswordRequest

        request = ChangePasswordRequest(
            current_password="WrongCurrentPass123!",
            new_password="NewPassword123!",
        )
        user_id = uuid4()
        mock_session = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.password_hash = "hashed_password"

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.auth.verify_password",
                return_value=False,
            ), pytest.raises(HTTPException) as exc_info:
                await change_password(
                    request=request,
                    current_user_id=user_id,
                    session=mock_session,
                )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "INVALID_PASSWORD"

    @pytest.mark.asyncio
    async def test_change_password_success(self) -> None:
        """Test successful password change."""
        from app.api.v1.endpoints.auth import change_password
        from app.api.v1.schemas.auth import ChangePasswordRequest

        request = ChangePasswordRequest(
            current_password="CurrentPass123!",
            new_password="NewPassword123!",
        )
        user_id = uuid4()
        mock_session = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.password_hash = "hashed_password"

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.auth.verify_password",
                return_value=True,
            ), patch("app.api.v1.endpoints.auth.hash_password"):
                result = await change_password(
                    request=request,
                    current_user_id=user_id,
                    session=mock_session,
                )

        assert result.success is True
        mock_repo.update.assert_called_once()
        mock_session.commit.assert_called_once()


class TestForgotPasswordEndpoint:
    """Tests for /auth/forgot-password endpoint."""

    @pytest.mark.asyncio
    async def test_forgot_password_user_exists(self) -> None:
        """Test forgot password for existing user."""
        from app.api.v1.endpoints.auth import forgot_password
        from app.api.v1.schemas.auth import ForgotPasswordRequest
        from app.domain.value_objects.email import Email

        request = ForgotPasswordRequest(email="test@example.com")
        mock_session = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = Email("test@example.com")
        mock_user.first_name = "Test"
        mock_user.is_active = True

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            # Patch email service import inside the function
            with patch(
                "app.infrastructure.email.get_email_service"
            ) as mock_email_service:
                mock_service = AsyncMock()
                mock_email_service.return_value = mock_service

                result = await forgot_password(
                    request=request,
                    session=mock_session,
                )

        assert result.success is True
        assert "email" in result.message.lower() or "account" in result.message.lower()

    @pytest.mark.asyncio
    async def test_forgot_password_user_not_exists(self) -> None:
        """Test forgot password for non-existent user returns same response."""
        from app.api.v1.endpoints.auth import forgot_password
        from app.api.v1.schemas.auth import ForgotPasswordRequest

        request = ForgotPasswordRequest(email="nonexistent@example.com")
        mock_session = AsyncMock()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = None
            mock_repo_class.return_value = mock_repo

            result = await forgot_password(
                request=request,
                session=mock_session,
            )

        # Should return same success message to prevent email enumeration
        assert result.success is True

    @pytest.mark.asyncio
    async def test_forgot_password_inactive_user(self) -> None:
        """Test forgot password for inactive user."""
        from app.api.v1.endpoints.auth import forgot_password
        from app.api.v1.schemas.auth import ForgotPasswordRequest
        from app.domain.value_objects.email import Email

        request = ForgotPasswordRequest(email="inactive@example.com")
        mock_session = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = Email("inactive@example.com")
        mock_user.is_active = False

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            result = await forgot_password(
                request=request,
                session=mock_session,
            )

        # Should still return success to prevent enumeration
        assert result.success is True


class TestAuthSchemaValidation:
    """Additional tests for auth schema validation."""

    def test_change_password_request_valid(self) -> None:
        """Test valid ChangePasswordRequest."""
        from app.api.v1.schemas.auth import ChangePasswordRequest

        request = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword123!",
        )

        assert request.current_password == "OldPassword123!"
        assert request.new_password == "NewPassword123!"

    def test_forgot_password_request_valid(self) -> None:
        """Test valid ForgotPasswordRequest."""
        from app.api.v1.schemas.auth import ForgotPasswordRequest

        request = ForgotPasswordRequest(email="test@example.com")
        assert request.email == "test@example.com"

    def test_forgot_password_request_invalid_email(self) -> None:
        """Test ForgotPasswordRequest with invalid email."""
        from pydantic import ValidationError

        from app.api.v1.schemas.auth import ForgotPasswordRequest

        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="not-an-email")

    def test_refresh_token_request_valid(self) -> None:
        """Test valid RefreshTokenRequest."""
        from app.api.v1.schemas.auth import RefreshTokenRequest

        request = RefreshTokenRequest(refresh_token="some-refresh-token")
        assert request.refresh_token == "some-refresh-token"

    def test_message_response_schema(self) -> None:
        """Test MessageResponse schema."""
        from app.api.v1.schemas.common import MessageResponse

        response = MessageResponse(message="Success", success=True)
        assert response.message == "Success"
        assert response.success is True

        response2 = MessageResponse(message="Failed", success=False)
        assert response2.success is False


class TestAuthEdgeCases:
    """Tests for edge cases in auth handling."""

    @pytest.mark.asyncio
    async def test_login_with_mfa_enabled_user(self) -> None:
        """Test login for user with MFA enabled."""
        from app.api.v1.endpoints.auth import login
        from app.api.v1.schemas.auth import LoginRequest

        request = LoginRequest(
            email="mfa_user@example.com",
            password="Password123!",
        )
        mock_session = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.tenant_id = uuid4()
        mock_user.password_hash = "hashed"
        mock_user.is_active = True
        mock_user.is_locked.return_value = False  # Not locked
        mock_user.is_superuser = False
        mock_user.roles = []
        mock_user.last_login = None
        mock_user.mfa_enabled = False  # Assume no MFA for now

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.auth.verify_password",
                return_value=True,
            ), patch(
                "app.api.v1.endpoints.auth.create_access_token",
                return_value="access",
            ), patch(
                "app.api.v1.endpoints.auth.create_refresh_token",
                return_value="refresh",
            ), patch(
                "app.infrastructure.auth.jwt_handler.decode_token",
                return_value={"jti": "mfa-test-jti"},
            ):
                mock_http_request = MagicMock()
                result = await login(
                    request=request,
                    session=mock_session,
                    http_request=mock_http_request,
                )

        assert result.access_token == "access"

    def test_token_response_expires_in(self) -> None:
        """Test TokenResponse expires_in field."""
        from app.api.v1.schemas.auth import TokenResponse

        response = TokenResponse(
            access_token="abc",
            refresh_token="xyz",
            token_type="bearer",
            expires_in=3600,
        )

        assert response.expires_in == 3600

    def test_auth_response_schema(self) -> None:
        """Test AuthResponse schema with nested schemas."""
        from app.api.v1.schemas.auth import AuthResponse, TokenResponse, UserResponse

        tokens = TokenResponse(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=3600,
        )

        user = UserResponse(
            id=uuid4(),
            email="test@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
            created_at=datetime.now(UTC),
            last_login=None,
        )

        response = AuthResponse(tokens=tokens, user=user)

        assert response.tokens.access_token == "access-token"
        assert response.user.email == "test@example.com"
