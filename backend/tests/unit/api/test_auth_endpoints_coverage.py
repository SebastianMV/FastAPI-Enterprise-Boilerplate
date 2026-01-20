# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for auth endpoints to improve coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.api.v1.endpoints.auth import (
    login,
    register,
    refresh_token,
    change_password,
)
from app.api.v1.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
)
from app.domain.entities.user import User
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
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = None
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await login(request=request, session=mock_session, http_request=mock_http_request)
            
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
        mock_user.record_failed_login.return_value = False  # Not locked after failed attempt
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            with patch("app.api.v1.endpoints.auth.verify_password") as mock_verify:
                mock_verify.return_value = False
                
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc:
                    await login(request=request, session=mock_session, http_request=mock_http_request)
                
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
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            with patch("app.api.v1.endpoints.auth.verify_password") as mock_verify:
                mock_verify.return_value = True
                
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc:
                    await login(request=request, session=mock_session, http_request=mock_http_request)
                
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
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.last_login = None
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo.update.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            with patch("app.api.v1.endpoints.auth.verify_password") as mock_verify:
                mock_verify.return_value = True
                
                with patch("app.api.v1.endpoints.auth.create_access_token") as mock_access:
                    with patch("app.api.v1.endpoints.auth.create_refresh_token") as mock_refresh:
                        with patch("app.infrastructure.auth.jwt_handler.decode_token") as mock_decode:
                            mock_access.return_value = "access_token"
                            mock_refresh.return_value = "refresh_token"
                            mock_decode.return_value = {"jti": "test-jti-456"}
                        
                            result = await login(request=request, session=mock_session, http_request=mock_http_request)
                        
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
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user  # User exists
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await register(request=request, session=mock_session)
            
            assert exc.value.status_code == 409
            assert "EMAIL_EXISTS" in str(exc.value.detail)


class TestRefreshTokenEndpoint:
    """Tests for refresh_token endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, mock_session: MagicMock) -> None:
        """Test refresh with invalid token."""
        request = RefreshTokenRequest(refresh_token="invalid_token")
        
        with patch("app.api.v1.endpoints.auth.validate_refresh_token") as mock_validate:
            from app.infrastructure.auth.jwt_handler import AuthenticationError
            mock_validate.side_effect = AuthenticationError(
                code="INVALID_TOKEN",
                message="Invalid refresh token"
            )
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await refresh_token(request=request, session=mock_session)
            
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found(self, mock_session: MagicMock) -> None:
        """Test refresh when user no longer exists."""
        request = RefreshTokenRequest(refresh_token="valid_token")
        
        user_id = uuid4()
        
        with patch("app.api.v1.endpoints.auth.validate_refresh_token") as mock_validate:
            mock_validate.return_value = {"sub": str(user_id), "tenant_id": str(uuid4())}
            
            with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = None  # User deleted
                mock_repo_cls.return_value = mock_repo
                
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc:
                    await refresh_token(request=request, session=mock_session)
                
                assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, mock_session: MagicMock) -> None:
        """Test successful token refresh."""
        request = RefreshTokenRequest(refresh_token="valid_token")
        
        user_id = uuid4()
        tenant_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id
        mock_user.is_active = True
        
        with patch("app.api.v1.endpoints.auth.validate_refresh_token") as mock_validate:
            mock_validate.return_value = {"sub": str(user_id), "tenant_id": str(tenant_id)}
            
            with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = mock_user
                mock_repo_cls.return_value = mock_repo
                
                with patch("app.api.v1.endpoints.auth.create_access_token") as mock_access:
                    with patch("app.api.v1.endpoints.auth.create_refresh_token") as mock_refresh:
                        mock_access.return_value = "new_access_token"
                        mock_refresh.return_value = "new_refresh_token"
                        
                        result = await refresh_token(request=request, session=mock_session)
                        
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
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            with patch("app.api.v1.endpoints.auth.verify_password") as mock_verify:
                mock_verify.return_value = False  # Wrong password
                
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc:
                    await change_password(
                        request=request,
                        current_user_id=user_id,
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
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            with patch("app.api.v1.endpoints.auth.verify_password") as mock_verify:
                mock_verify.return_value = True
                
                with patch("app.api.v1.endpoints.auth.hash_password") as mock_hash:
                    mock_hash.return_value = "new_hashed"
                    
                    result = await change_password(
                        request=request,
                        current_user_id=user_id,
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
