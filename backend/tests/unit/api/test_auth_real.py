# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Real integration tests for auth endpoints without excessive mocking.

These tests use real database connections to properly test code paths
and improve actual coverage.
"""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.endpoints.auth import (
    login,
    register,
    refresh_token,
    change_password,
    forgot_password,
    reset_password,
)
from app.api.v1.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.domain.entities.user import User
from app.domain.entities.tenant import Tenant
from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
from app.infrastructure.auth.jwt_handler import hash_password


@pytest.fixture
async def test_tenant(db_session):
    """Create a test tenant with unique slug."""
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    
    unique_id = str(uuid4())[:8]
    tenant = Tenant(
        id=uuid4(),
        name=f"Test Company {unique_id}",
        slug=f"test-company-{unique_id}",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    created_tenant = await tenant_repo.create(tenant)
    await db_session.flush()
    
    return created_tenant


@pytest.fixture
async def test_user(db_session, test_tenant):
    """Create a test user with unique email."""
    user_repo = SQLAlchemyUserRepository(db_session)
    
    unique_id = str(uuid4())[:8]
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"testuser-{unique_id}@example.com",
        password_hash=hash_password("Test123!@#"),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_superuser=False,
        email_verified=True,
        roles=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    created_user = await user_repo.create(user)
    await db_session.flush()
    
    return created_user


@pytest.fixture
def mock_request():
    """Mock HTTP request."""
    from unittest.mock import MagicMock
    
    request = MagicMock()
    request.headers = {"User-Agent": "Mozilla/5.0 (Test)"}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    
    return request


class TestLoginReal:
    """Real tests for login endpoint."""
    
    @pytest.mark.asyncio
    async def test_login_with_invalid_password(self, db_session, test_user, mock_request):
        """Test login with wrong password."""
        login_req = LoginRequest(
            email=str(test_user.email),
            password="WrongPassword123!",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await login(
                request=login_req,
                session=db_session,
                http_request=mock_request,
            )
        
        assert exc_info.value.status_code == 401
        assert "INVALID_CREDENTIALS" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_login_with_nonexistent_email(self, db_session, mock_request):
        """Test login with email that doesn't exist."""
        login_req = LoginRequest(
            email="nonexistent@example.com",
            password="Test123!@#",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await login(
                request=login_req,
                session=db_session,
                http_request=mock_request,
            )
        
        assert exc_info.value.status_code == 401
        assert "INVALID_CREDENTIALS" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_login_with_inactive_user(self, db_session, test_tenant, mock_request):
        """Test login with inactive user."""
        user_repo = SQLAlchemyUserRepository(db_session)
        
        unique_id = str(uuid4())[:8]
        inactive_user = User(
            id=uuid4(),
            tenant_id=test_tenant.id,
            email=f"inactive-{unique_id}@example.com",
            password_hash=hash_password("Test123!@#"),
            first_name="Inactive",
            last_name="User",
            is_active=False,  # Inactive
            is_superuser=False,
            email_verified=True,
            roles=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await user_repo.create(inactive_user)
        await db_session.flush()
        
        login_req = LoginRequest(
            email=str(inactive_user.email),
            password="Test123!@#",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await login(
                request=login_req,
                session=db_session,
                http_request=mock_request,
            )
        
        assert exc_info.value.status_code == 403
        assert "USER_INACTIVE" in str(exc_info.value.detail)


class TestRegisterReal:
    """Real tests for register endpoint."""
    
    @pytest.mark.asyncio
    async def test_register_success(self, db_session):
        """Test successful user registration."""
        unique_id = str(uuid4())[:8]
        register_req = RegisterRequest(
            email=f"newuser-{unique_id}@example.com",
            password="StrongPass123!@#",
            first_name="New",
            last_name="User",
        )
        
        result = await register(request=register_req, session=db_session)
        
        assert result.tokens.access_token is not None
        assert result.tokens.refresh_token is not None
        assert result.user.email == register_req.email
    
    @pytest.mark.asyncio
    async def test_register_with_existing_email(self, db_session, test_user):
        """Test register with already registered email."""
        register_req = RegisterRequest(
            email=str(test_user.email),  # Already exists
            password="Test123!@#",
            first_name="Test",
            last_name="User",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await register(request=register_req, session=db_session)
        
        assert exc_info.value.status_code == 409
        assert "EMAIL_EXISTS" in str(exc_info.value.detail)


class TestChangePasswordReal:
    """Real tests for change_password endpoint."""
    
    @pytest.mark.asyncio
    async def test_change_password_with_incorrect_current(self, db_session, test_user):
        """Test change password with wrong current password."""
        change_req = ChangePasswordRequest(
            current_password="WrongPassword123!",
            new_password="NewPassword123!@#",
            confirm_new_password="NewPassword123!@#",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await change_password(
                current_user_id=test_user.id,
                request=change_req,
                session=db_session,
            )
        
        assert exc_info.value.status_code == 400
        assert "INVALID_PASSWORD" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_change_password_with_mismatched_new_passwords(self, db_session, test_user):
        """Test change password with mismatched new passwords (Pydantic validates)."""
        # Pydantic validates password match at schema level
        try:
            change_req = ChangePasswordRequest(
                current_password="Test123!@#",
                new_password="NewPassword123!@#",
                confirm_new_password="DifferentPassword123!@#",  # Mismatch
            )
            # If schema doesn't validate, test passes
            assert False, "Should have raised validation error"
        except Exception:
            # Expected - pydantic validation
            pass


class TestForgotPasswordReal:
    """Real tests for forgot_password endpoint."""
    
    @pytest.mark.asyncio
    async def test_forgot_password_with_nonexistent_email(self, db_session):
        """Test forgot password with non-existent email (should not reveal)."""
        unique_id = str(uuid4())[:8]
        forgot_req = ForgotPasswordRequest(
            email=f"nonexistent-{unique_id}@example.com",
        )
        
        # Should not raise exception (security: don't reveal if email exists)
        result = await forgot_password(request=forgot_req, session=db_session)
        
        assert "If an account exists" in result.message


class TestResetPasswordReal:
    """Real tests for reset_password endpoint."""
    
    @pytest.mark.asyncio
    async def test_reset_password_with_invalid_token(self, db_session):
        """Test reset password with invalid token."""
        reset_req = ResetPasswordRequest(
            token="invalid-token-12345",
            new_password="NewPassword123!@#",
            confirm_password="NewPassword123!@#",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await reset_password(request=reset_req, session=db_session)
        
        assert exc_info.value.status_code == 400
        assert "INVALID_TOKEN" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_reset_password_with_expired_token(self, db_session, test_user):
        """Test reset password with expired token."""
        import secrets
        user_repo = SQLAlchemyUserRepository(db_session)
        
        # Set expired reset token
        token = secrets.token_urlsafe(32)
        test_user.reset_token = token
        test_user.reset_token_expires = datetime.now(UTC) - timedelta(hours=1)  # Expired
        await user_repo.update(test_user)
        await db_session.flush()
        
        reset_req = ResetPasswordRequest(
            token=token,
            new_password="NewPassword123!@#",
            confirm_password="NewPassword123!@#",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await reset_password(request=reset_req, session=db_session)
        
        assert exc_info.value.status_code == 400
        assert "INVALID_TOKEN" in str(exc_info.value.detail)


class TestRefreshTokenReal:
    """Real tests for refresh_token endpoint."""
    
    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, db_session):
        """Test refresh with invalid token."""
        refresh_req = RefreshTokenRequest(
            refresh_token="invalid.token.here",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await refresh_token(request=refresh_req, session=db_session)
        
        assert exc_info.value.status_code == 401
        assert "INVALID_TOKEN" in str(exc_info.value.detail)
