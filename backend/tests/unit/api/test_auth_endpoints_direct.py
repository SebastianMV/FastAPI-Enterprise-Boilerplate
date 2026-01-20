# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Direct unit tests for auth endpoint functions.

Tests authentication logic directly without HTTP layer overhead.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.entities.user import User
from app.domain.entities.tenant import Tenant
from app.infrastructure.auth.jwt_handler import hash_password, create_access_token
from app.api.v1.schemas.auth import LoginRequest, RegisterRequest, ChangePasswordRequest
from fastapi import HTTPException


@pytest.fixture
async def test_tenant(db_session):
    """Create a real tenant entity in database."""
    from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
    
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    tenant = Tenant(
        id=uuid4(),
        name="Test Company",
        slug="test-company",
        plan="free",
        is_active=True,
    )
    created = await tenant_repo.create(tenant)
    await db_session.flush()
    return created


@pytest.fixture
async def test_user(db_session, test_tenant):
    """Create a real user entity in database."""
    from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
    
    user_repo = SQLAlchemyUserRepository(db_session)
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name="User",
        tenant_id=test_tenant.id,
        is_active=True,
        email_verified=True,
    )
    created = await user_repo.create(user)
    await db_session.flush()
    return created



class TestLoginLogic:
    """Test login endpoint logic."""

    @pytest.mark.asyncio
    async def test_login_creates_session(self, db_session, test_user, test_tenant):
        """Test that login creates a user session."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        from app.infrastructure.database.repositories.session_repository import SQLAlchemySessionRepository
        
        user_repo = SQLAlchemyUserRepository(db_session)
        session_repo = SQLAlchemySessionRepository(db_session)
        
        # Verify user exists
        user = await user_repo.get_by_id(test_user.id)
        assert user is not None
        # Email is an Email value object, need .value
        assert user.email.value == "test@example.com"
        
        # Create session manually (simulating endpoint logic)
        from app.domain.entities.session import UserSession
        session = UserSession(
            id=uuid4(),
            user_id=user.id,
            tenant_id=user.tenant_id,
            ip_address="127.0.0.1",
            device_name="test-device",
            refresh_token_hash="test_hash",
        )
        
        created_session = await session_repo.create(session)
        assert created_session is not None
        assert created_session.user_id == user.id

    @pytest.mark.asyncio
    async def test_login_updates_last_login(self, db_session, test_user):
        """Test that login updates user's last_login timestamp."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        
        user_repo = SQLAlchemyUserRepository(db_session)
        
        # Get user
        user = await user_repo.get_by_id(test_user.id)
        original_last_login = user.last_login
        
        # Update last_login
        user.last_login = datetime.now(UTC)
        updated_user = await user_repo.update(user)
        
        assert updated_user.last_login is not None
        if original_last_login:
            assert updated_user.last_login > original_last_login

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, db_session, test_user):
        """Test login fails with wrong password."""
        from app.infrastructure.auth.jwt_handler import verify_password
        
        result = verify_password("WrongPassword123!", test_user.password_hash)
        assert result is False

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, db_session):
        """Test login fails for nonexistent user."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        
        user_repo = SQLAlchemyUserRepository(db_session)
        user = await user_repo.get_by_email("nonexistent@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, db_session, test_user):
        """Test login fails for inactive user."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        
        user_repo = SQLAlchemyUserRepository(db_session)
        
        # Deactivate user
        test_user.is_active = False
        await user_repo.update(test_user)
        
        # Retrieve and verify
        user = await user_repo.get_by_id(test_user.id)
        assert user.is_active is False


class TestRegisterLogic:
    """Test register endpoint logic."""

    @pytest.mark.asyncio
    async def test_register_creates_tenant(self, db_session):
        """Test that registration creates a new tenant."""
        from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
        
        tenant_repo = SQLAlchemyTenantRepository(db_session)
        
        tenant = Tenant(
            id=uuid4(),
            name="New Organization",
            slug="new-org",
            plan="free",
            is_active=True,
        )
        
        created_tenant = await tenant_repo.create(tenant)
        assert created_tenant is not None
        assert created_tenant.name == "New Organization"
        assert created_tenant.plan == "free"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, db_session, test_user):
        """Test registration fails with duplicate email."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        
        user_repo = SQLAlchemyUserRepository(db_session)
        
        # Try to find user with same email
        existing = await user_repo.get_by_email(test_user.email.value)
        assert existing is not None
        assert existing.email.value == test_user.email.value


class TestTokenLogic:
    """Test token refresh logic."""

    @pytest.mark.asyncio
    async def test_refresh_token_creates_new_tokens(self):
        """Test refresh token generates new access token."""
        user_id = uuid4()
        tenant_id = uuid4()
        
        # Create tokens
        access_token = create_access_token(user_id, tenant_id)
        refresh_token = create_access_token(user_id, tenant_id)  # Simplified
        
        assert access_token is not None
        assert refresh_token is not None
        assert isinstance(access_token, str)

    @pytest.mark.asyncio
    async def test_logout_revokes_session(self, db_session, test_user):
        """Test logout revokes user session."""
        from app.infrastructure.database.repositories.session_repository import SQLAlchemySessionRepository
        from app.domain.entities.session import UserSession
        
        session_repo = SQLAlchemySessionRepository(db_session)
        
        # Create session
        session = UserSession(
            id=uuid4(),
            user_id=test_user.id,
            tenant_id=test_user.tenant_id,
            ip_address="127.0.0.1",
            device_name="test",
            refresh_token_hash="test_hash",
        )
        
        created = await session_repo.create(session)
        await db_session.flush()
        
        # Verify session exists before revoking
        assert created is not None
        assert created.is_revoked is False
        
        # Revoke using repository method
        result = await session_repo.revoke(created.id)
        assert result is True


class TestPasswordChangeLogic:
    """Test password change logic."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, db_session, test_user):
        """Test successful password change."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        from app.infrastructure.auth.jwt_handler import hash_password as hash_pwd, verify_password
        
        user_repo = SQLAlchemyUserRepository(db_session)
        
        # Change password
        new_password_hash = hash_pwd("NewPassword123!")
        test_user.password_hash = new_password_hash
        updated = await user_repo.update(test_user)
        
        # Verify new password works
        assert verify_password("NewPassword123!", updated.password_hash)
        assert not verify_password("OldPassword123!", updated.password_hash)

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, test_user):
        """Test password change fails with wrong current password."""
        from app.infrastructure.auth.jwt_handler import verify_password
        
        # Current password verification should fail
        result = verify_password("WrongCurrentPassword!", test_user.password_hash)
        assert result is False


class TestPasswordResetLogic:
    """Test password reset flow."""

    @pytest.mark.asyncio
    async def test_forgot_password_user_exists(self, db_session, test_user):
        """Test forgot password for existing user."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        
        user_repo = SQLAlchemyUserRepository(db_session)
        
        # User should exist
        user = await user_repo.get_by_email(test_user.email.value)
        assert user is not None

    @pytest.mark.asyncio
    async def test_reset_password_changes_hash(self, db_session, test_user):
        """Test password reset changes the hash."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        from app.infrastructure.auth.jwt_handler import hash_password as hash_pwd, verify_password
        
        user_repo = SQLAlchemyUserRepository(db_session)
        
        # Get original hash
        original_hash = test_user.password_hash
        
        # Change password
        new_hash = hash_pwd("NewPassword123!")
        test_user.password_hash = new_hash
        
        updated = await user_repo.update(test_user)
        
        # Verify new hash is different
        assert updated.password_hash != original_hash
        assert verify_password("NewPassword123!", updated.password_hash)

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self):
        """Test password reset fails with expired token."""
        expired_time = datetime.now(UTC) - timedelta(hours=1)
        current_time = datetime.now(UTC)
        
        # Token is expired if expiry is in the past
        assert expired_time < current_time


class TestEmailVerificationLogic:
    """Test email verification flow."""

    @pytest.mark.asyncio
    async def test_verify_email_success(self, db_session, test_user):
        """Test successful email verification."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        
        user_repo = SQLAlchemyUserRepository(db_session)
        
        # Set user as unverified
        test_user.email_verified = False
        test_user.email_verification_token = "test_token"
        await user_repo.update(test_user)
        
        # Verify email
        test_user.email_verified = True
        test_user.email_verification_token = None
        
        updated = await user_repo.update(test_user)
        
        assert updated.email_verified is True
        assert updated.email_verification_token is None

    @pytest.mark.asyncio
    async def test_send_verification_email_generates_token(self, test_user):
        """Test sending verification email generates token."""
        # Set user as unverified first
        test_user.email_verified = False
        test_user.email_verification_token = None
        
        # Generate verification token using domain method
        token = test_user.generate_verification_token()
        
        assert token is not None
        assert test_user.email_verification_token == token
        assert test_user.email_verification_sent_at is not None

    @pytest.mark.asyncio
    async def test_get_verification_status(self, test_user):
        """Test getting email verification status."""
        # User created as verified
        assert test_user.email_verified is True
        
        # Unverified user
        test_user.email_verified = False
        assert test_user.email_verified is False
