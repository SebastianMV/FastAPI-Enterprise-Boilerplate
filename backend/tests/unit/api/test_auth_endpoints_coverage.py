# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for auth endpoints to improve coverage.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.v1.endpoints.auth import (
    change_password,
    login,
    refresh_token,
    register,
    send_verification_email,
    verify_email,
)
from app.api.v1.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    VerifyEmailTokenRequest,
)
from app.domain.value_objects.email import Email


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


class TestLoginEndpoint:
    """Tests for login endpoint."""

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, mock_session: MagicMock) -> None:
        """Test login with non-existent user."""
        request = LoginRequest(
            email="notfound@example.com",
            password="Password123!",
        )
        mock_http_request = MagicMock()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = None
            mock_repo_cls.return_value = mock_repo

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc:
                await login(
                    request=request,
                    session=mock_session,
                    http_request=mock_http_request,
                )

            assert exc.value.status_code == 401
            assert "INVALID_CREDENTIALS" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, mock_session: MagicMock) -> None:
        """Test login with wrong password."""
        request = LoginRequest(
            email="test@example.com",
            password="WrongPassword123!",
        )
        mock_http_request = MagicMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.password_hash = "hashed_correct_password"
        mock_user.is_active = True
        mock_user.is_locked.return_value = False
        mock_user.record_failed_login.return_value = (
            False  # Not locked after failed attempt
        )

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_cls.return_value = mock_repo

            with patch("app.api.v1.endpoints.auth.verify_password") as mock_verify:
                mock_verify.return_value = False

                from fastapi import HTTPException

                with pytest.raises(HTTPException) as exc:
                    await login(
                        request=request,
                        session=mock_session,
                        http_request=mock_http_request,
                    )

                assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, mock_session: MagicMock) -> None:
        """Test login with inactive user."""
        request = LoginRequest(
            email="inactive@example.com",
            password="Password123!",
        )
        mock_http_request = MagicMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.password_hash = "hashed"
        mock_user.is_active = False
        mock_user.is_locked.return_value = False

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_cls.return_value = mock_repo

            with patch("app.application.use_cases.auth.login.verify_password") as mock_verify:
                mock_verify.return_value = True

                from fastapi import HTTPException

                with pytest.raises(HTTPException) as exc:
                    await login(
                        request=request,
                        session=mock_session,
                        http_request=mock_http_request,
                    )

                assert exc.value.status_code == 403
                assert "USER_INACTIVE" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_login_success(self, mock_session: MagicMock) -> None:
        """Test successful login."""
        request = LoginRequest(
            email="test@example.com",
            password="Password123!",
        )
        mock_http_request = MagicMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.tenant_id = uuid4()
        mock_user.email = Email("test@example.com")
        mock_user.password_hash = "hashed"
        mock_user.is_active = True
        mock_user.is_locked.return_value = False
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.is_superuser = False
        mock_user.roles = []
        mock_user.created_at = datetime.now(UTC)
        mock_user.last_login = None

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo.update.return_value = mock_user
            mock_repo_cls.return_value = mock_repo

            with patch("app.application.use_cases.auth.login.verify_password") as mock_verify:
                mock_verify.return_value = True

                with (
                    patch(
                        "app.application.use_cases.auth.login.create_access_token"
                    ) as mock_access,
                    patch(
                        "app.application.use_cases.auth.login.create_refresh_token"
                    ) as mock_refresh,
                    patch(
                        "app.application.use_cases.auth.login.decode_token"
                    ) as mock_decode,
                    patch(
                        "app.application.services.mfa_config_service.get_mfa_config",
                        new_callable=AsyncMock,
                        return_value=None,
                    ),
                    patch(
                        "app.infrastructure.database.repositories.session_repository.SQLAlchemySessionRepository"
                    ) as mock_session_repo_cls,
                ):
                    mock_access.return_value = "access_token"
                    mock_refresh.return_value = "refresh_token"
                    mock_decode.return_value = {"jti": "test-jti-456"}
                    mock_session_repo_cls.return_value = AsyncMock()

                    result = await login(
                        request=request,
                        session=mock_session,
                        http_request=mock_http_request,
                    )

                    # login returns TokenResponse directly, not AuthResponse
                    assert result.access_token == "access_token"
                    assert result.refresh_token == "refresh_token"


class TestRegisterEndpoint:
    """Tests for register endpoint."""

    @pytest.mark.asyncio
    async def test_register_email_exists(self, mock_session: MagicMock) -> None:
        """Test register with existing email."""
        request = RegisterRequest(
            email="existing@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
        )

        mock_user = MagicMock()
        mock_user.id = uuid4()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user  # User exists
            mock_repo_cls.return_value = mock_repo

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc:
                await register(request=request, session=mock_session)

            assert exc.value.status_code == 409
            assert "EMAIL_EXISTS" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_register_creates_default_tenant_when_none_exists(
        self, mock_session: MagicMock
    ) -> None:
        """Test register creates default tenant when none exists."""
        request = RegisterRequest(
            email="new@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
        )

        user_id = uuid4()
        tenant_id = uuid4()

        # Mock created user
        mock_created_user = MagicMock()
        mock_created_user.id = user_id
        mock_created_user.tenant_id = tenant_id
        mock_created_user.email = "new@example.com"
        mock_created_user.first_name = "Test"
        mock_created_user.last_name = "User"
        mock_created_user.is_active = True
        mock_created_user.is_superuser = False
        mock_created_user.roles = []
        mock_created_user.email_verified = False
        mock_created_user.avatar_url = None

        # Mock created tenant
        mock_created_tenant = MagicMock()
        mock_created_tenant.id = tenant_id
        mock_created_tenant.name = "Default"
        mock_created_tenant.slug = "default"

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_user_repo_cls:
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_email.return_value = None  # User doesn't exist
            mock_user_repo.create.return_value = mock_created_user
            mock_user_repo_cls.return_value = mock_user_repo

            with patch(
                "app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository"
            ) as mock_tenant_repo_cls:
                mock_tenant_repo = AsyncMock()
                mock_tenant_repo.get_default_tenant.return_value = (
                    None  # No default tenant
                )
                mock_tenant_repo.create.return_value = mock_created_tenant
                mock_tenant_repo_cls.return_value = mock_tenant_repo

                with (
                    patch(
                        "app.application.use_cases.auth.register.hash_password",
                        return_value="hashed_password",
                    ),
                    patch(
                        "app.application.use_cases.auth.register.create_access_token",
                        return_value="access_token",
                    ),
                    patch(
                        "app.application.use_cases.auth.register.create_refresh_token",
                        return_value="refresh_token",
                    ),
                    patch("app.application.use_cases.auth.register.settings") as mock_settings,
                ):
                    mock_settings.EMAIL_VERIFICATION_REQUIRED = False

                    result = await register(request=request, session=mock_session)

                    # Verify tenant was created
                    mock_tenant_repo.create.assert_called_once()
                    assert result is not None

    @pytest.mark.asyncio
    async def test_register_with_email_verification_enabled(
        self, mock_session: MagicMock
    ) -> None:
        """Test register sends verification email when enabled."""
        request = RegisterRequest(
            email="verify@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
        )

        user_id = uuid4()
        tenant_id = uuid4()

        mock_created_user = MagicMock()
        mock_created_user.id = user_id
        mock_created_user.tenant_id = tenant_id
        mock_created_user.email = "verify@example.com"
        mock_created_user.first_name = "Test"
        mock_created_user.last_name = "User"
        mock_created_user.is_active = True
        mock_created_user.is_superuser = False
        mock_created_user.roles = []
        mock_created_user.email_verified = False
        mock_created_user.avatar_url = None
        mock_created_user.generate_verification_token.return_value = "verify_token_123"

        mock_default_tenant = MagicMock()
        mock_default_tenant.id = tenant_id

        mock_email_service = AsyncMock()
        mock_email_service.send_verification_email = AsyncMock()

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_user_repo_cls:
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_email.return_value = None
            mock_user_repo.create.return_value = mock_created_user
            mock_user_repo_cls.return_value = mock_user_repo

            with patch(
                "app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository"
            ) as mock_tenant_repo_cls:
                mock_tenant_repo = AsyncMock()
                mock_tenant_repo.get_default_tenant.return_value = mock_default_tenant
                mock_tenant_repo_cls.return_value = mock_tenant_repo

                with patch(
                    "app.application.use_cases.auth.register.hash_password",
                    return_value="hashed_password",
                ):
                    with patch(
                        "app.application.use_cases.auth.register.create_access_token",
                        return_value="access_token",
                    ):
                        with patch(
                            "app.application.use_cases.auth.register.create_refresh_token",
                            return_value="refresh_token",
                        ):
                            with patch(
                                "app.application.use_cases.auth.register.settings"
                            ) as mock_settings:
                                mock_settings.EMAIL_VERIFICATION_REQUIRED = True
                                mock_settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24
                                mock_settings.CORS_ORIGINS = ["http://localhost:3000"]

                                with patch(
                                    "app.infrastructure.email.get_email_service",
                                    return_value=mock_email_service,
                                ):
                                    result = await register(
                                        request=request, session=mock_session
                                    )

                                    # Verify email service was called
                                    mock_email_service.send_verification_email.assert_called_once()
                                    assert result is not None


class TestRefreshTokenEndpoint:
    """Tests for refresh_token endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, mock_session: MagicMock) -> None:
        """Test refresh with invalid token."""
        request = RefreshTokenRequest(refresh_token="invalid_token")
        mock_request = MagicMock()
        mock_request.cookies = {}

        with patch("app.application.use_cases.auth.refresh.validate_refresh_token") as mock_validate:
            from app.infrastructure.auth.jwt_handler import AuthenticationError

            mock_validate.side_effect = AuthenticationError(
                code="INVALID_TOKEN", message="Invalid refresh token"
            )

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc:
                await refresh_token(request=request, session=mock_session, http_request=mock_request)

            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found(self, mock_session: MagicMock) -> None:
        """Test refresh when user no longer exists."""
        request = RefreshTokenRequest(refresh_token="valid_token")
        mock_request = MagicMock()
        mock_request.cookies = {}

        user_id = uuid4()

        with patch("app.application.use_cases.auth.refresh.validate_refresh_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": str(uuid4()),
            }

            with patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = None  # User deleted
                mock_repo_cls.return_value = mock_repo

                from fastapi import HTTPException

                with pytest.raises(HTTPException) as exc:
                    await refresh_token(request=request, session=mock_session, http_request=mock_request)

                assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, mock_session: MagicMock) -> None:
        """Test successful token refresh."""
        request = RefreshTokenRequest(refresh_token="valid_token")
        mock_request = MagicMock()
        mock_request.cookies = {}

        user_id = uuid4()
        tenant_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id
        mock_user.is_active = True

        with patch("app.application.use_cases.auth.refresh.validate_refresh_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
            }

            with patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = mock_user
                mock_repo_cls.return_value = mock_repo

                with (
                    patch(
                        "app.application.use_cases.auth.refresh.create_access_token"
                    ) as mock_access,
                    patch(
                        "app.application.use_cases.auth.refresh.create_refresh_token"
                    ) as mock_refresh,
                ):
                    mock_access.return_value = "new_access_token"
                    mock_refresh.return_value = "new_refresh_token"

                    result = await refresh_token(request=request, session=mock_session, http_request=mock_request)

                    assert result.access_token == "new_access_token"
                    assert result.refresh_token == "new_refresh_token"


class TestChangePasswordEndpoint:
    """Tests for change_password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, mock_session: MagicMock) -> None:
        """Test change password with wrong current password."""
        user_id = uuid4()
        request = ChangePasswordRequest(
            current_password="WrongPassword123!",
            new_password="NewPassword123!",
        )

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.password_hash = "hashed"

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_cls.return_value = mock_repo

            with patch("app.api.v1.endpoints.auth.verify_password") as mock_verify:
                mock_verify.return_value = False  # Wrong password

                from fastapi import HTTPException

                with pytest.raises(HTTPException) as exc:
                    await change_password(
                        request=request,
                        current_user=mock_user,
                        session=mock_session,
                    )

                assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_change_password_success(self, mock_session: MagicMock) -> None:
        """Test successful password change."""
        user_id = uuid4()
        request = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword123!",
        )

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.password_hash = "old_hashed"

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.return_value = mock_user
            mock_repo_cls.return_value = mock_repo

            with patch("app.api.v1.endpoints.auth.verify_password") as mock_verify:
                mock_verify.return_value = True

                with (
                    patch("app.api.v1.endpoints.auth.hash_password") as mock_hash,
                    patch(
                        "app.infrastructure.database.repositories.session_repository.SQLAlchemySessionRepository"
                    ) as mock_session_repo_cls,
                ):
                    mock_hash.return_value = "new_hashed"
                    mock_session_repo = AsyncMock()
                    mock_session_repo_cls.return_value = mock_session_repo

                    result = await change_password(
                        request=request,
                        current_user=mock_user,
                        session=mock_session,
                    )

                    assert result.message is not None
                    assert result.success is True


class TestAuthSchemas:
    """Tests for auth schema validation."""

    def test_login_request(self) -> None:
        """Test LoginRequest schema."""
        request = LoginRequest(
            email="test@example.com",
            password="Password123!",
        )

        assert request.email == "test@example.com"

    def test_register_request(self) -> None:
        """Test RegisterRequest schema."""
        request = RegisterRequest(
            email="new@example.com",
            password="Password123!",
            first_name="John",
            last_name="Doe",
        )

        assert request.first_name == "John"
        assert request.last_name == "Doe"

    def test_refresh_token_request(self) -> None:
        """Test RefreshTokenRequest schema."""
        request = RefreshTokenRequest(
            refresh_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        )

        assert request.refresh_token.startswith("eyJ")

    def test_change_password_request(self) -> None:
        """Test ChangePasswordRequest schema."""
        request = ChangePasswordRequest(
            current_password="OldPass123!",
            new_password="NewPass456!",
        )

        assert request.current_password != request.new_password


class TestLoginMFAFlow:
    """Tests for MFA flow in login endpoint."""

    @pytest.mark.asyncio
    async def test_login_mfa_required_without_code(
        self, mock_session: MagicMock
    ) -> None:
        """Test login fails when MFA is required but no code provided."""
        request = LoginRequest(
            email="mfa@example.com",
            password="Password123!",
            mfa_code=None,
        )
        mock_http_request = MagicMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.password_hash = "hashed"
        mock_user.is_active = True
        mock_user.is_locked.return_value = False
        mock_user.tenant_id = uuid4()

        mock_mfa_config = MagicMock()
        mock_mfa_config.is_enabled = True

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_cls.return_value = mock_repo

            with patch("app.application.use_cases.auth.login.verify_password", return_value=True):
                with patch(
                    "app.application.services.mfa_config_service.get_mfa_config",
                    new_callable=AsyncMock,
                    return_value=mock_mfa_config,
                ):
                    from fastapi import HTTPException

                    with pytest.raises(HTTPException) as exc:
                        await login(
                            request=request,
                            session=mock_session,
                            http_request=mock_http_request,
                        )

                    assert exc.value.status_code == 403
                    assert "MFA_REQUIRED" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_login_mfa_invalid_code(self, mock_session: MagicMock) -> None:
        """Test login fails with invalid MFA code."""
        request = LoginRequest(
            email="mfa@example.com",
            password="Password123!",
            mfa_code="000000",
        )
        mock_http_request = MagicMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.password_hash = "hashed"
        mock_user.is_active = True
        mock_user.is_locked.return_value = False
        mock_user.tenant_id = uuid4()

        mock_mfa_config = MagicMock()
        mock_mfa_config.is_enabled = True

        mock_mfa_service = MagicMock()
        mock_mfa_service.verify_code.return_value = (False, False)

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_cls.return_value = mock_repo

            with patch("app.application.use_cases.auth.login.verify_password", return_value=True):
                with patch(
                    "app.application.services.mfa_config_service.get_mfa_config",
                    new_callable=AsyncMock,
                    return_value=mock_mfa_config,
                ):
                    with patch(
                        "app.application.services.mfa_service.get_mfa_service",
                        return_value=mock_mfa_service,
                    ):
                        from fastapi import HTTPException

                        with pytest.raises(HTTPException) as exc:
                            await login(
                                request=request,
                                session=mock_session,
                                http_request=mock_http_request,
                            )

                        assert exc.value.status_code == 403
                        assert "INVALID_MFA_CODE" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_login_mfa_valid_code_success(self, mock_session: MagicMock) -> None:
        """Test login succeeds with valid MFA code."""
        request = LoginRequest(
            email="mfa@example.com",
            password="Password123!",
            mfa_code="123456",
        )
        mock_http_request = MagicMock()
        mock_http_request.headers.get.return_value = "Mozilla/5.0"
        mock_http_request.client.host = "127.0.0.1"

        user_id = uuid4()
        tenant_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.password_hash = "hashed"
        mock_user.is_active = True
        mock_user.is_locked.return_value = False
        mock_user.tenant_id = tenant_id
        mock_user.email = "mfa@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.is_superuser = False
        mock_user.roles = []
        mock_user.email_verified = True
        mock_user.avatar_url = None
        mock_user.reset_failed_attempts = MagicMock()

        mock_mfa_config = MagicMock()
        mock_mfa_config.is_enabled = True

        mock_mfa_service = MagicMock()
        mock_mfa_service.verify_code.return_value = (True, False)

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo.update = AsyncMock(return_value=mock_user)
            mock_repo_cls.return_value = mock_repo

            with patch("app.application.use_cases.auth.login.verify_password", return_value=True):
                with patch(
                    "app.application.services.mfa_config_service.get_mfa_config",
                    new_callable=AsyncMock,
                    return_value=mock_mfa_config,
                ):
                    with patch(
                        "app.application.services.mfa_service.get_mfa_service",
                        return_value=mock_mfa_service,
                    ):
                        with patch(
                            "app.application.services.mfa_config_service.save_mfa_config",
                            new_callable=AsyncMock,
                        ):
                            with patch(
                                "app.application.use_cases.auth.login.create_access_token",
                                return_value="access_token",
                            ):
                                with patch(
                                    "app.application.use_cases.auth.login.create_refresh_token",
                                    return_value="refresh_token",
                                ):
                                    # Mock decode_token in the login use case module
                                    with patch(
                                        "app.application.use_cases.auth.login.decode_token",
                                        return_value={"jti": "test_jti"},
                                    ):
                                        # Mock session repository
                                        with patch(
                                            "app.infrastructure.database.repositories.session_repository.SQLAlchemySessionRepository"
                                        ) as mock_sess_repo_cls:
                                            mock_sess_repo = AsyncMock()
                                            mock_sess_repo.create = AsyncMock()
                                            mock_sess_repo_cls.return_value = (
                                                mock_sess_repo
                                            )

                                            with patch(
                                                "app.infrastructure.auth.jwt_handler.hash_password",
                                                return_value="hashed_jti",
                                            ):
                                                result = await login(
                                                    request=request,
                                                    session=mock_session,
                                                    http_request=mock_http_request,
                                                )

                                                # Result is AuthResponse which has tokens attribute
                                                assert hasattr(
                                                    result, "tokens"
                                                ) or hasattr(result, "access_token")
                                                if hasattr(result, "tokens"):
                                                    assert (
                                                        result.tokens.access_token
                                                        == "access_token"
                                                    )
                                                else:
                                                    assert (
                                                        result.access_token
                                                        == "access_token"
                                                    )


class TestEmailVerificationEndpoints:
    """Tests for email verification endpoints."""

    @pytest.mark.asyncio
    async def test_send_verification_email_user_not_found(
        self, mock_session: MagicMock
    ) -> None:
        """Test send verification email fails when user not found."""
        user_id = uuid4()
        mock_current_user = MagicMock()
        mock_current_user.id = user_id

        with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            with patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = None  # User not found
                mock_repo_cls.return_value = mock_repo

                from fastapi import HTTPException

                with pytest.raises(HTTPException) as exc:
                    await send_verification_email(current_user=mock_current_user, session=mock_session)

                assert exc.value.status_code == 404
                assert "USER_NOT_FOUND" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_send_verification_email_already_verified(
        self, mock_session: MagicMock
    ) -> None:
        """Test send verification email returns early when already verified."""
        user_id = uuid4()
        mock_current_user = MagicMock()
        mock_current_user.id = user_id

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email_verified = True  # Already verified

        with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            with patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = mock_user
                mock_repo_cls.return_value = mock_repo

                result = await send_verification_email(
                    current_user=mock_current_user, session=mock_session
                )

                assert result.success is True
                assert "already verified" in result.message.lower()

    @pytest.mark.asyncio
    async def test_send_verification_email_success(
        self, mock_session: MagicMock
    ) -> None:
        """Test send verification email succeeds."""
        user_id = uuid4()
        mock_current_user = MagicMock()
        mock_current_user.id = user_id

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.email_verified = False
        mock_user.generate_verification_token.return_value = "token123"

        mock_email_service = AsyncMock()
        mock_email_service.send_verification_email = AsyncMock()

        with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            with patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = mock_user
                mock_repo.update = AsyncMock(return_value=mock_user)
                mock_repo_cls.return_value = mock_repo

                with (
                    patch(
                        "app.infrastructure.email.get_email_service",
                        return_value=mock_email_service,
                    ),
                    patch("app.api.v1.endpoints.auth.settings") as mock_settings,
                ):
                    mock_settings.FRONTEND_URL = "http://localhost:3000"
                    mock_settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24

                    result = await send_verification_email(
                        current_user=mock_current_user, session=mock_session
                    )

                    assert result.success is True
                    mock_email_service.send_verification_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, mock_session: MagicMock) -> None:
        """Test verify email fails with invalid token."""
        token = "invalid_token"

        # Mock the session execute for finding user by token
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None  # No user found
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await verify_email(request=VerifyEmailTokenRequest(token=token), session=mock_session)

        assert exc.value.status_code == 400
        assert "INVALID_TOKEN" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_verify_email_success(self, mock_session: MagicMock) -> None:
        """Test verify email succeeds with valid token."""
        token = "valid_token"
        user_id = uuid4()

        mock_user_model = MagicMock()
        mock_user_model.id = user_id

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email_verified = False
        mock_user.verify_email.return_value = True

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update = AsyncMock(return_value=mock_user)
            mock_repo_cls.return_value = mock_repo

            # Mock the session execute for finding user by token
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.first.return_value = mock_user_model
            mock_result.scalars.return_value = mock_scalars
            mock_session.execute.return_value = mock_result

            with patch("app.api.v1.endpoints.auth.settings") as mock_settings:
                mock_settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24

                result = await verify_email(request=VerifyEmailTokenRequest(token=token), session=mock_session)

                assert result.success is True
                mock_user.verify_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_email_token_expired(self, mock_session: MagicMock) -> None:
        """Test verify email fails with expired token."""
        token = "expired_token"
        user_id = uuid4()

        mock_user_model = MagicMock()
        mock_user_model.id = user_id

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email_verified = False
        mock_user.verify_email.return_value = False  # Token expired

        with patch(
            "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_cls.return_value = mock_repo

            # Mock the session execute for finding user by token
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.first.return_value = mock_user_model
            mock_result.scalars.return_value = mock_scalars
            mock_session.execute.return_value = mock_result

            with patch("app.api.v1.endpoints.auth.settings") as mock_settings:
                mock_settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24

                from fastapi import HTTPException

                with pytest.raises(HTTPException) as exc:
                    await verify_email(request=VerifyEmailTokenRequest(token=token), session=mock_session)

                assert exc.value.status_code == 400
                assert "TOKEN_EXPIRED" in str(exc.value.detail)


class TestAuthAdditionalCoverage:
    """Additional tests for auth endpoint coverage."""

    @pytest.mark.asyncio
    async def test_login_invalid_email_format(self, mock_session: MagicMock) -> None:
        """Test login with invalid email format (lines 71-72)."""
        from app.api.v1.endpoints.auth import login
        from app.api.v1.schemas.auth import LoginRequest

        request = LoginRequest(
            email="test@example.com",  # Valid for pydantic but we mock Email to fail
            password="Password123!",
        )
        mock_http_request = MagicMock()

        with patch("app.application.use_cases.auth.login.Email") as mock_email:
            mock_email.side_effect = ValueError("Invalid email format")

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc:
                await login(
                    request=request,
                    session=mock_session,
                    http_request=mock_http_request,
                )

            assert exc.value.status_code == 401
            assert "INVALID_CREDENTIALS" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_login_account_locked(self, mock_session: MagicMock) -> None:
        """Test login with locked account (lines 89-91)."""
        from datetime import timedelta

        from app.api.v1.endpoints.auth import login
        from app.api.v1.schemas.auth import LoginRequest

        request = LoginRequest(
            email="locked@example.com",
            password="Password123!",
        )
        mock_http_request = MagicMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.is_locked.return_value = True
        mock_user.locked_until = datetime.now(UTC) + timedelta(minutes=10)

        with (
            patch("app.application.use_cases.auth.login.Email") as mock_email,
            patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_cls,
            patch("app.application.use_cases.auth.login.settings") as mock_settings,
        ):
            mock_email.return_value = MagicMock()
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            mock_settings.ACCOUNT_LOCKOUT_ENABLED = True

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc:
                await login(
                    request=request,
                    session=mock_session,
                    http_request=mock_http_request,
                )

            assert exc.value.status_code == 423
            assert "ACCOUNT_LOCKED" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_login_wrong_password_triggers_lockout(
        self, mock_session: MagicMock
    ) -> None:
        """Test login with wrong password that triggers lockout (lines 111)."""
        from app.api.v1.endpoints.auth import login
        from app.api.v1.schemas.auth import LoginRequest

        request = LoginRequest(
            email="test@example.com",
            password="WrongPassword123!",
        )
        mock_http_request = MagicMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.password_hash = "hashed"
        mock_user.is_locked.return_value = False
        mock_user.record_failed_login.return_value = (
            True  # Now locked after this attempt
        )

        with (
            patch("app.application.use_cases.auth.login.Email") as mock_email,
            patch(
                "app.api.v1.endpoints.auth.SQLAlchemyUserRepository"
            ) as mock_repo_cls,
            patch("app.application.use_cases.auth.login.verify_password") as mock_verify,
            patch("app.application.use_cases.auth.login.settings") as mock_settings,
        ):
            mock_email.return_value = MagicMock()
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            mock_verify.return_value = False
            mock_settings.ACCOUNT_LOCKOUT_ENABLED = True
            mock_settings.ACCOUNT_LOCKOUT_THRESHOLD = 5
            mock_settings.ACCOUNT_LOCKOUT_DURATION_MINUTES = 15

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc:
                await login(
                    request=request,
                    session=mock_session,
                    http_request=mock_http_request,
                )

            assert exc.value.status_code == 423
            assert "ACCOUNT_LOCKED" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_register_invalid_email_format(self, mock_session: MagicMock) -> None:
        """Test register with invalid email format (lines 250-251)."""
        from app.api.v1.endpoints.auth import register
        from app.api.v1.schemas.auth import RegisterRequest

        request = RegisterRequest(
            email="test@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
        )

        with patch("app.application.use_cases.auth.register.Email") as mock_email:
            mock_email.side_effect = ValueError("Invalid email format")

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc:
                await register(request=request, session=mock_session)

            assert exc.value.status_code == 400
            assert "INVALID_EMAIL" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_register_weak_password(self, mock_session: MagicMock) -> None:
        """Test register with weak password (lines 259-260)."""
        from app.api.v1.endpoints.auth import register
        from app.api.v1.schemas.auth import RegisterRequest

        request = RegisterRequest(
            email="test@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
        )

        with (
            patch("app.application.use_cases.auth.register.Email") as mock_email,
            patch("app.application.use_cases.auth.register.Password") as mock_password,
        ):
            mock_email.return_value = MagicMock()
            mock_password.side_effect = ValueError("Password too weak")

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc:
                await register(request=request, session=mock_session)

            assert exc.value.status_code == 400
            assert "WEAK_PASSWORD" in str(exc.value.detail)
