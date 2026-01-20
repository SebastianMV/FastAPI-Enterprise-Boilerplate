# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for auth endpoints to improve coverage.

Focuses on edge cases, error paths, and integration scenarios.
"""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import (
    login,
    register,
    refresh_token,
    logout,
    change_password,
    forgot_password,
    verify_reset_token,
    reset_password,
    send_verification_email,
    verify_email,
)
from app.api.v1.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    VerifyResetTokenRequest,
    ResetPasswordRequest,
)
from app.domain.entities.user import User


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_request():
    """Mock HTTP Request."""
    request = MagicMock()
    request.headers = {"User-Agent": "Mozilla/5.0"}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def sample_user():
    """Sample user entity."""
    user = User(
        id=uuid4(),
        tenant_id=uuid4(),
        email="test@example.com",
        password_hash="$2b$12$hashed_password",
        is_active=True,
        is_superuser=False,
        email_verified=True,
        roles=[],
    )
    user.last_login = None
    user.failed_login_attempts = 0
    user.locked_until = None
    return user


class TestLoginEndpoint:
    """Tests for /login endpoint."""
    
    @pytest.mark.asyncio
    async def test_login_with_locked_account(self, mock_session, mock_request):
        """Test login with locked account."""
        # Create locked user
        locked_user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email="locked@example.com",
            password_hash="$2b$12$hashed",
            is_active=True,
            is_superuser=False,
            email_verified=True,
            roles=[],
        )
        locked_user.locked_until = datetime.now(UTC) + timedelta(minutes=10)
        locked_user.failed_login_attempts = 5
        
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=locked_user)
        
        request = LoginRequest(email="locked@example.com", password="password123")
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.config.settings.ACCOUNT_LOCKOUT_ENABLED', True):
            
            with pytest.raises(HTTPException) as exc_info:
                await login(request, mock_session, mock_request)
            
            assert exc_info.value.status_code == status.HTTP_423_LOCKED
            assert "ACCOUNT_LOCKED" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_login_triggers_lockout_on_failed_attempt(self, mock_session, mock_request, sample_user):
        """Test that failed login triggers account lockout."""
        sample_user.failed_login_attempts = 4  # One before lockout
        
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=sample_user)
        mock_repo.update = AsyncMock()
        
        request = LoginRequest(email="test@example.com", password="wrong_password")
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.verify_password', return_value=False), \
             patch('app.config.settings.ACCOUNT_LOCKOUT_ENABLED', True), \
             patch('app.config.settings.ACCOUNT_LOCKOUT_THRESHOLD', 5), \
             patch('app.config.settings.ACCOUNT_LOCKOUT_DURATION_MINUTES', 30):
            
            # Mock user.record_failed_login to return True (locked)
            with patch.object(sample_user, 'record_failed_login', return_value=True):
                with pytest.raises(HTTPException) as exc_info:
                    await login(request, mock_session, mock_request)
                
                assert exc_info.value.status_code == status.HTTP_423_LOCKED
                assert "ACCOUNT_LOCKED" in str(exc_info.value.detail)
                mock_repo.update.assert_called_once()
                mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_login_with_inactive_user(self, mock_session, mock_request, sample_user):
        """Test login with inactive user account."""
        sample_user.is_active = False
        
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=sample_user)
        
        request = LoginRequest(email="test@example.com", password="password123")
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.verify_password', return_value=True):
            
            with pytest.raises(HTTPException) as exc_info:
                await login(request, mock_session, mock_request)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "USER_INACTIVE" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_login_with_mfa_enabled_no_code(self, mock_session, mock_request, sample_user):
        """Test login with MFA enabled but no code provided."""
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=sample_user)
        
        mock_mfa_config = MagicMock()
        mock_mfa_config.is_enabled = True
        
        request = LoginRequest(email="test@example.com", password="password123")
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.verify_password', return_value=True), \
             patch('app.api.v1.endpoints.auth.get_mfa_config', return_value=mock_mfa_config):
            
            with pytest.raises(HTTPException) as exc_info:
                await login(request, mock_session, mock_request)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "MFA_REQUIRED" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_login_with_mfa_invalid_code(self, mock_session, mock_request, sample_user):
        """Test login with MFA enabled but invalid code."""
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=sample_user)
        
        mock_mfa_config = MagicMock()
        mock_mfa_config.is_enabled = True
        
        mock_mfa_service = MagicMock()
        mock_mfa_service.verify_code = MagicMock(return_value=(False, False))
        
        request = LoginRequest(
            email="test@example.com",
            password="password123",
            mfa_code="000000"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.verify_password', return_value=True), \
             patch('app.api.v1.endpoints.auth.get_mfa_config', return_value=mock_mfa_config), \
             patch('app.api.v1.endpoints.auth.get_mfa_service', return_value=mock_mfa_service):
            
            with pytest.raises(HTTPException) as exc_info:
                await login(request, mock_session, mock_request)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "INVALID_MFA_CODE" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_login_success_with_mfa_valid_code(self, mock_session, mock_request, sample_user):
        """Test successful login with valid MFA code."""
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=sample_user)
        mock_repo.update = AsyncMock()
        
        mock_mfa_config = MagicMock()
        mock_mfa_config.is_enabled = True
        
        mock_mfa_service = MagicMock()
        mock_mfa_service.verify_code = MagicMock(return_value=(True, False))
        
        mock_session_repo = AsyncMock()
        mock_session_repo.create = AsyncMock()
        
        request = LoginRequest(
            email="test@example.com",
            password="password123",
            mfa_code="123456"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.verify_password', return_value=True), \
             patch('app.api.v1.endpoints.auth.get_mfa_config', return_value=mock_mfa_config), \
             patch('app.api.v1.endpoints.auth.get_mfa_service', return_value=mock_mfa_service), \
             patch('app.api.v1.endpoints.auth.save_mfa_config'), \
             patch('app.api.v1.endpoints.auth.create_access_token', return_value="access_token"), \
             patch('app.api.v1.endpoints.auth.create_refresh_token', return_value="refresh_token"), \
             patch('app.api.v1.endpoints.auth.decode_token', return_value={"jti": "session_id"}), \
             patch('app.api.v1.endpoints.auth.SQLAlchemySessionRepository', return_value=mock_session_repo):
            
            result = await login(request, mock_session, mock_request)
            
            assert result.access_token == "access_token"
            assert result.refresh_token == "refresh_token"
            mock_repo.update.assert_called_once()
            mock_session_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_login_success_with_mfa_backup_code(self, mock_session, mock_request, sample_user):
        """Test successful login using MFA backup code."""
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=sample_user)
        mock_repo.update = AsyncMock()
        
        mock_mfa_config = MagicMock()
        mock_mfa_config.is_enabled = True
        
        # Simulate backup code usage
        mock_mfa_service = MagicMock()
        mock_mfa_service.verify_code = MagicMock(return_value=(True, True))  # was_backup=True
        
        mock_session_repo = AsyncMock()
        mock_session_repo.create = AsyncMock()
        
        request = LoginRequest(
            email="test@example.com",
            password="password123",
            mfa_code="backup-12345"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.verify_password', return_value=True), \
             patch('app.api.v1.endpoints.auth.get_mfa_config', return_value=mock_mfa_config), \
             patch('app.api.v1.endpoints.auth.get_mfa_service', return_value=mock_mfa_service), \
             patch('app.api.v1.endpoints.auth.save_mfa_config') as mock_save, \
             patch('app.api.v1.endpoints.auth.create_access_token', return_value="access_token"), \
             patch('app.api.v1.endpoints.auth.create_refresh_token', return_value="refresh_token"), \
             patch('app.api.v1.endpoints.auth.decode_token', return_value={"jti": "session_id"}), \
             patch('app.api.v1.endpoints.auth.SQLAlchemySessionRepository', return_value=mock_session_repo):
            
            result = await login(request, mock_session, mock_request)
            
            assert result.access_token == "access_token"
            # Verify backup code caused config to be saved
            mock_save.assert_called_once_with(mock_mfa_config)


class TestRegisterEndpoint:
    """Tests for /register endpoint."""
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, mock_session):
        """Test registration with duplicate email."""
        existing_user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email="existing@example.com",
            password_hash="$2b$12$hash",
            is_active=True,
            is_superuser=False,
            email_verified=False,
            roles=[],
        )
        
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=existing_user)
        
        request = RegisterRequest(
            email="existing@example.com",
            password="Password123!",
            confirm_password="Password123!",
            full_name="Test User"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await register(request, mock_session)
            
            assert exc_info.value.status_code == status.HTTP_409_CONFLICT
            assert "EMAIL_ALREADY_REGISTERED" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_register_password_mismatch(self, mock_session):
        """Test registration with mismatched passwords."""
        request = RegisterRequest(
            email="new@example.com",
            password="Password123!",
            confirm_password="DifferentPassword123!",
            full_name="Test User"
        )
        
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=None)
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await register(request, mock_session)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "PASSWORDS_DO_NOT_MATCH" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_register_success_creates_user_and_tenant(self, mock_session):
        """Test successful registration creates user and tenant."""
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email = AsyncMock(return_value=None)
        mock_user_repo.create = AsyncMock()
        
        mock_tenant_repo = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant_repo.create = AsyncMock(return_value=mock_tenant)
        
        request = RegisterRequest(
            email="new@example.com",
            password="Password123!",
            confirm_password="Password123!",
            full_name="Test User"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_user_repo), \
             patch('app.api.v1.endpoints.auth.SQLAlchemyTenantRepository', return_value=mock_tenant_repo), \
             patch('app.api.v1.endpoints.auth.hash_password', return_value="hashed_password"):
            
            result = await register(request, mock_session)
            
            assert result.message == "User registered successfully"
            mock_tenant_repo.create.assert_called_once()
            mock_user_repo.create.assert_called_once()
            mock_session.commit.assert_called()


class TestRefreshTokenEndpoint:
    """Tests for /refresh endpoint."""
    
    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, mock_session):
        """Test refresh with invalid token."""
        request = RefreshTokenRequest(refresh_token="invalid_token")
        
        with patch('app.api.v1.endpoints.auth.validate_refresh_token', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await refresh_token(request, mock_session)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "INVALID_REFRESH_TOKEN" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_refresh_with_deleted_session(self, mock_session, sample_user):
        """Test refresh with deleted/revoked session."""
        payload = {
            "sub": str(sample_user.id),
            "tenant_id": str(sample_user.tenant_id),
            "jti": "session_id",
        }
        
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_jti = AsyncMock(return_value=None)  # Session not found
        
        request = RefreshTokenRequest(refresh_token="valid_token")
        
        with patch('app.api.v1.endpoints.auth.validate_refresh_token', return_value=payload), \
             patch('app.api.v1.endpoints.auth.SQLAlchemySessionRepository', return_value=mock_session_repo):
            
            with pytest.raises(HTTPException) as exc_info:
                await refresh_token(request, mock_session)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "SESSION_NOT_FOUND" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_refresh_success(self, mock_session, sample_user):
        """Test successful token refresh."""
        payload = {
            "sub": str(sample_user.id),
            "tenant_id": str(sample_user.tenant_id),
            "jti": "session_id",
        }
        
        mock_user_session = MagicMock()
        mock_user_session.is_revoked = False
        mock_user_session.is_active = True
        
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_jti = AsyncMock(return_value=mock_user_session)
        mock_session_repo.update = AsyncMock()
        
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=sample_user)
        
        request = RefreshTokenRequest(refresh_token="valid_token")
        
        with patch('app.api.v1.endpoints.auth.validate_refresh_token', return_value=payload), \
             patch('app.api.v1.endpoints.auth.SQLAlchemySessionRepository', return_value=mock_session_repo), \
             patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_user_repo), \
             patch('app.api.v1.endpoints.auth.create_access_token', return_value="new_access_token"):
            
            result = await refresh_token(request, mock_session)
            
            assert result.access_token == "new_access_token"
            assert result.token_type == "bearer"
            mock_session_repo.update.assert_called_once()


class TestLogoutEndpoint:
    """Tests for /logout endpoint."""
    
    @pytest.mark.asyncio
    async def test_logout_revokes_session(self, mock_session):
        """Test logout revokes user session."""
        user_id = uuid4()
        
        mock_user_session = MagicMock()
        mock_user_session.is_revoked = False
        mock_user_session.revoke = MagicMock()
        
        mock_session_repo = AsyncMock()
        mock_session_repo.get_active_by_user_id = AsyncMock(return_value=[mock_user_session])
        mock_session_repo.update = AsyncMock()
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemySessionRepository', return_value=mock_session_repo):
            result = await logout(user_id, mock_session)
            
            assert result.message == "Logged out successfully"
            mock_user_session.revoke.assert_called_once()
            mock_session_repo.update.assert_called_once()
            mock_session.commit.assert_called_once()


class TestChangePasswordEndpoint:
    """Tests for /change-password endpoint."""
    
    @pytest.mark.asyncio
    async def test_change_password_incorrect_current(self, mock_session, sample_user):
        """Test change password with incorrect current password."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=sample_user)
        
        request = ChangePasswordRequest(
            current_password="wrong_password",
            new_password="NewPassword123!",
            confirm_password="NewPassword123!"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.verify_password', return_value=False):
            
            with pytest.raises(HTTPException) as exc_info:
                await change_password(sample_user.id, request, mock_session)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "INCORRECT_PASSWORD" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, mock_session, sample_user):
        """Test change password with mismatched new passwords."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=sample_user)
        
        request = ChangePasswordRequest(
            current_password="current_password",
            new_password="NewPassword123!",
            confirm_password="DifferentPassword123!"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.verify_password', return_value=True):
            
            with pytest.raises(HTTPException) as exc_info:
                await change_password(sample_user.id, request, mock_session)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "PASSWORDS_DO_NOT_MATCH" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, mock_session, sample_user):
        """Test successful password change."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=sample_user)
        mock_repo.update = AsyncMock()
        
        request = ChangePasswordRequest(
            current_password="current_password",
            new_password="NewPassword123!",
            confirm_password="NewPassword123!"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.verify_password', return_value=True), \
             patch('app.api.v1.endpoints.auth.hash_password', return_value="new_hash"):
            
            result = await change_password(sample_user.id, request, mock_session)
            
            assert result.message == "Password changed successfully"
            mock_repo.update.assert_called_once()
            mock_session.commit.assert_called_once()


class TestForgotPasswordEndpoint:
    """Tests for /forgot-password endpoint."""
    
    @pytest.mark.asyncio
    async def test_forgot_password_user_not_found(self, mock_session):
        """Test forgot password for non-existent user."""
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=None)
        
        request = ForgotPasswordRequest(email="nonexistent@example.com")
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo):
            # Should not raise error for security reasons
            result = await forgot_password(request, mock_session)
            
            assert result.message == "If the email exists, a reset link has been sent"
    
    @pytest.mark.asyncio
    async def test_forgot_password_success(self, mock_session, sample_user):
        """Test successful forgot password request."""
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=sample_user)
        mock_repo.update = AsyncMock()
        
        mock_email_service = AsyncMock()
        mock_email_service.send_password_reset_email = AsyncMock()
        
        request = ForgotPasswordRequest(email="test@example.com")
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.get_email_service', return_value=mock_email_service), \
             patch('app.api.v1.endpoints.auth.secrets.token_urlsafe', return_value="reset_token"):
            
            result = await forgot_password(request, mock_session)
            
            assert result.message == "If the email exists, a reset link has been sent"
            mock_repo.update.assert_called_once()
            mock_email_service.send_password_reset_email.assert_called_once()


class TestResetPasswordEndpoint:
    """Tests for /reset-password endpoint."""
    
    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, mock_session):
        """Test reset password with invalid token."""
        mock_repo = AsyncMock()
        mock_repo.get_by_reset_token = AsyncMock(return_value=None)
        
        request = ResetPasswordRequest(
            token="invalid_token",
            new_password="NewPassword123!",
            confirm_password="NewPassword123!"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await reset_password(request, mock_session)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "INVALID_RESET_TOKEN" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self, mock_session, sample_user):
        """Test reset password with expired token."""
        sample_user.reset_token = "valid_token"
        sample_user.reset_token_expires = datetime.now(UTC) - timedelta(hours=1)  # Expired
        
        mock_repo = AsyncMock()
        mock_repo.get_by_reset_token = AsyncMock(return_value=sample_user)
        
        request = ResetPasswordRequest(
            token="valid_token",
            new_password="NewPassword123!",
            confirm_password="NewPassword123!"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await reset_password(request, mock_session)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "RESET_TOKEN_EXPIRED" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_reset_password_success(self, mock_session, sample_user):
        """Test successful password reset."""
        sample_user.reset_token = "valid_token"
        sample_user.reset_token_expires = datetime.now(UTC) + timedelta(hours=1)  # Valid
        
        mock_repo = AsyncMock()
        mock_repo.get_by_reset_token = AsyncMock(return_value=sample_user)
        mock_repo.update = AsyncMock()
        
        request = ResetPasswordRequest(
            token="valid_token",
            new_password="NewPassword123!",
            confirm_password="NewPassword123!"
        )
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo), \
             patch('app.api.v1.endpoints.auth.hash_password', return_value="new_hash"):
            
            result = await reset_password(request, mock_session)
            
            assert result.message == "Password reset successfully"
            assert sample_user.reset_token is None
            assert sample_user.reset_token_expires is None
            mock_repo.update.assert_called_once()


class TestVerifyEmailEndpoint:
    """Tests for /verify-email endpoint."""
    
    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, mock_session):
        """Test email verification with invalid token."""
        mock_repo = AsyncMock()
        mock_repo.get_by_verification_token = AsyncMock(return_value=None)
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await verify_email("invalid_token", mock_session)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "INVALID_VERIFICATION_TOKEN" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_verify_email_success(self, mock_session, sample_user):
        """Test successful email verification."""
        sample_user.email_verified = False
        sample_user.verification_token = "valid_token"
        
        mock_repo = AsyncMock()
        mock_repo.get_by_verification_token = AsyncMock(return_value=sample_user)
        mock_repo.update = AsyncMock()
        
        with patch('app.api.v1.endpoints.auth.SQLAlchemyUserRepository', return_value=mock_repo):
            result = await verify_email("valid_token", mock_session)
            
            assert result.message == "Email verified successfully"
            assert sample_user.email_verified is True
            assert sample_user.verification_token is None
            mock_repo.update.assert_called_once()
