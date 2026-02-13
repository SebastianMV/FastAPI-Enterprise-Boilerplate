# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Auth API endpoints.

Tests for authentication endpoints - login, register, refresh, etc.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


class TestLoginEndpoint:
    """Tests for /auth/login endpoint."""

    def test_login_invalid_email_format_pydantic(self) -> None:
        """Test login with invalid email format fails at Pydantic validation."""
        from pydantic import ValidationError

        from app.api.v1.schemas.auth import LoginRequest

        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(
                email="not-an-email",
                password="password123",
            )

        assert "email" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_user_not_found(self) -> None:
        """Test login when user doesn't exist."""
        from app.api.v1.endpoints.auth import login
        from app.api.v1.schemas.auth import LoginRequest

        request = LoginRequest(
            email="test@example.com",
            password="Password123!",
        )
        mock_session = AsyncMock()
        mock_http_request = MagicMock()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = None
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await login(
                    request=request,
                    session=mock_session,
                    http_request=mock_http_request,
                )

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self) -> None:
        """Test login with incorrect password."""
        from app.api.v1.endpoints.auth import login
        from app.api.v1.schemas.auth import LoginRequest

        request = LoginRequest(
            email="test@example.com",
            password="WrongPassword123!",
        )
        mock_session = AsyncMock()
        mock_http_request = MagicMock()

        mock_user = MagicMock()
        mock_user.password_hash = "hashed_password"
        mock_user.is_active = True
        mock_user.is_locked.return_value = False  # Not locked
        mock_user.record_failed_login.return_value = (
            False  # Not locked after failed attempt
        )

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            with patch("app.application.use_cases.auth.login.verify_password", return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await login(
                        request=request,
                        session=mock_session,
                        http_request=mock_http_request,
                    )

                assert exc_info.value.status_code == 401
                assert exc_info.value.detail["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_inactive_user(self) -> None:
        """Test login with inactive user."""
        from app.api.v1.endpoints.auth import login
        from app.api.v1.schemas.auth import LoginRequest

        request = LoginRequest(
            email="test@example.com",
            password="Password123!",
        )
        mock_session = AsyncMock()
        mock_http_request = MagicMock()

        mock_user = MagicMock()
        mock_user.password_hash = "hashed_password"
        mock_user.is_active = False
        mock_user.is_locked.return_value = False  # Not locked

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            with patch("app.application.use_cases.auth.login.verify_password", return_value=True):
                with pytest.raises(HTTPException) as exc_info:
                    await login(
                        request=request,
                        session=mock_session,
                        http_request=mock_http_request,
                    )

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail["code"] == "USER_INACTIVE"

    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        """Test successful login."""
        from app.api.v1.endpoints.auth import login
        from app.api.v1.schemas.auth import LoginRequest

        request = LoginRequest(
            email="test@example.com",
            password="Password123!",
        )
        mock_session = AsyncMock()
        mock_http_request = MagicMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.tenant_id = uuid4()
        mock_user.password_hash = "hashed_password"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.is_locked.return_value = False  # Not locked
        mock_user.roles = []
        mock_user.last_login = None

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            with patch("app.application.use_cases.auth.login.verify_password", return_value=True):
                with patch(
                    "app.application.use_cases.auth.login.create_access_token",
                    return_value="access_token",
                ):
                    with patch(
                        "app.application.use_cases.auth.login.create_refresh_token",
                        return_value="refresh_token",
                    ):
                        with patch(
                            "app.application.use_cases.auth.login.decode_token",
                            return_value={"jti": "test-jti-123"},
                        ):
                            with patch(
                                "app.infrastructure.database.repositories.session_repository.SQLAlchemySessionRepository"
                            ) as mock_session_repo_cls:
                                mock_session_repo_cls.return_value = AsyncMock()

                                with patch(
                                    "app.application.services.mfa_config_service.get_mfa_config",
                                    new_callable=AsyncMock,
                                    return_value=None,
                                ):
                                    result = await login(
                                        request=request,
                                        session=mock_session,
                                        http_request=mock_http_request,
                                    )

        assert result.access_token == "access_token"
        assert result.refresh_token == "refresh_token"
        assert result.token_type == "bearer"


class TestRegisterEndpoint:
    """Tests for /auth/register endpoint."""

    def test_register_invalid_email_pydantic(self) -> None:
        """Test register with invalid email fails at Pydantic validation."""
        from pydantic import ValidationError

        from app.api.v1.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="invalid-email",
                password="Password123!",
                first_name="Test",
                last_name="User",
            )

        assert "email" in str(exc_info.value)

    def test_register_weak_password_pydantic(self) -> None:
        """Test register with weak password fails at Pydantic validation."""
        from pydantic import ValidationError

        from app.api.v1.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="test@example.com",
                password="weak",
                first_name="Test",
                last_name="User",
            )

        assert "password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_email_exists(self) -> None:
        """Test register when email already exists."""
        from app.api.v1.endpoints.auth import register
        from app.api.v1.schemas.auth import RegisterRequest

        request = RegisterRequest(
            email="existing@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
        )
        mock_session = AsyncMock()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = MagicMock()  # User exists
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await register(request=request, session=mock_session)

            assert exc_info.value.status_code == 409
            assert exc_info.value.detail["code"] == "EMAIL_EXISTS"


class TestRefreshTokenEndpoint:
    """Tests for /auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self) -> None:
        """Test refresh with invalid token."""
        from app.api.v1.endpoints.auth import refresh_token
        from app.api.v1.schemas.auth import RefreshTokenRequest
        from app.domain.exceptions.base import AuthenticationError

        request = RefreshTokenRequest(
            refresh_token="invalid-token",
        )
        mock_session = AsyncMock()
        mock_http_request = MagicMock()
        mock_http_request.cookies = {}

        with patch(
            "app.application.use_cases.auth.refresh.validate_refresh_token",
            side_effect=AuthenticationError(
                message="Invalid token",
                code="INVALID_TOKEN",
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await refresh_token(request=request, session=mock_session, http_request=mock_http_request)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail["code"] == "INVALID_TOKEN"

    @pytest.mark.asyncio
    async def test_refresh_user_not_found(self) -> None:
        """Test refresh when user doesn't exist."""
        from app.api.v1.endpoints.auth import refresh_token
        from app.api.v1.schemas.auth import RefreshTokenRequest

        user_id = uuid4()
        request = RefreshTokenRequest(
            refresh_token="valid-token",
        )
        mock_session = AsyncMock()
        mock_http_request = MagicMock()
        mock_http_request.cookies = {}

        with (
            patch(
                "app.application.use_cases.auth.refresh.validate_refresh_token",
                return_value={"sub": str(user_id), "tenant_id": str(uuid4())},
            ),
            patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_class,
        ):
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await refresh_token(request=request, session=mock_session, http_request=mock_http_request)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail["code"] == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_refresh_inactive_user(self) -> None:
        """Test refresh with inactive user."""
        from app.api.v1.endpoints.auth import refresh_token
        from app.api.v1.schemas.auth import RefreshTokenRequest

        user_id = uuid4()
        request = RefreshTokenRequest(
            refresh_token="valid-token",
        )
        mock_session = AsyncMock()
        mock_http_request = MagicMock()
        mock_http_request.cookies = {}

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = False

        with (
            patch(
                "app.application.use_cases.auth.refresh.validate_refresh_token",
                return_value={"sub": str(user_id), "tenant_id": str(uuid4())},
            ),
            patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_class,
        ):
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await refresh_token(request=request, session=mock_session, http_request=mock_http_request)

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["code"] == "USER_INACTIVE"

    @pytest.mark.asyncio
    async def test_refresh_success(self) -> None:
        """Test successful token refresh."""
        from app.api.v1.endpoints.auth import refresh_token
        from app.api.v1.schemas.auth import RefreshTokenRequest

        user_id = uuid4()
        tenant_id = uuid4()
        request = RefreshTokenRequest(
            refresh_token="valid-token",
        )
        mock_session = AsyncMock()
        mock_http_request = MagicMock()
        mock_http_request.cookies = {}

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.roles = []

        with (
            patch(
                "app.application.use_cases.auth.refresh.validate_refresh_token",
                return_value={"sub": str(user_id), "tenant_id": str(tenant_id)},
            ),
            patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_class,
        ):
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            with (
                patch(
                    "app.application.use_cases.auth.refresh.create_access_token",
                    return_value="new_access_token",
                ),
                patch(
                    "app.application.use_cases.auth.refresh.create_refresh_token",
                    return_value="new_refresh_token",
                ),
            ):
                result = await refresh_token(request=request, session=mock_session, http_request=mock_http_request)

        assert result.access_token == "new_access_token"
        assert result.refresh_token == "new_refresh_token"


class TestLogoutEndpoint:
    """Tests for /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self) -> None:
        """Test successful logout."""
        from app.api.v1.endpoints.auth import logout

        user_id = uuid4()
        mock_request = MagicMock()
        mock_request.cookies = {}
        mock_response = MagicMock()

        with patch("app.application.use_cases.auth.logout.LogoutUseCase") as mock_uc_cls:
            mock_uc = AsyncMock()
            mock_uc_cls.return_value = mock_uc

            result = await logout(
                current_user_id=user_id,
                request=mock_request,
                response=mock_response,
                authorization="",
            )

        assert result.message == "Successfully logged out"
        assert result.success is True


class TestGetCurrentUserEndpoint:
    """Tests for /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user(self) -> None:
        """Test getting current user info."""
        from app.api.v1.endpoints.auth import get_current_user_info

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.created_at = datetime.now(UTC)
        mock_user.last_login = datetime.now(UTC)

        result = await get_current_user_info(current_user=mock_user)

        assert result.email == "test@example.com"
        assert result.first_name == "Test"
        assert result.last_name == "User"


class TestChangePasswordEndpoint:
    """Tests for /auth/change-password endpoint."""

    def test_change_password_weak_password_pydantic(self) -> None:
        """Test change password with weak new password fails at Pydantic validation."""
        from pydantic import ValidationError

        from app.api.v1.schemas.auth import ChangePasswordRequest

        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="OldPassword123!",
                new_password="weak",
            )

        assert "password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self) -> None:
        """Test change password when user not found."""
        from app.api.v1.endpoints.auth import change_password
        from app.api.v1.schemas.auth import ChangePasswordRequest

        request = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword123!",
        )
        mock_session = AsyncMock()
        mock_current_user = MagicMock()
        mock_current_user.id = uuid4()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    request=request,
                    current_user=mock_current_user,
                    session=mock_session,
                )

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail["code"] == "USER_NOT_FOUND"


class TestAuthSchemas:
    """Tests for auth request/response schemas."""

    def test_login_request_valid(self) -> None:
        """Test valid LoginRequest."""
        from app.api.v1.schemas.auth import LoginRequest

        request = LoginRequest(
            email="test@example.com",
            password="password123",
        )

        assert request.email == "test@example.com"
        assert request.password == "password123"

    def test_token_response_valid(self) -> None:
        """Test valid TokenResponse."""
        from app.api.v1.schemas.auth import TokenResponse

        response = TokenResponse(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=900,
        )

        assert response.access_token == "access-token"
        assert response.token_type == "bearer"
        assert response.expires_in == 900

    def test_message_response(self) -> None:
        """Test MessageResponse."""
        from app.api.v1.schemas.common import MessageResponse

        response = MessageResponse(
            message="Success",
            success=True,
        )

        assert response.message == "Success"
        assert response.success is True
