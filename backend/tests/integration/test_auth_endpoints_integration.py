# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Integration tests for authentication endpoints.

Tests complete authentication flows with real database and mocked external services.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status

from app.domain.entities.user import User
from app.domain.entities.tenant import Tenant
from app.infrastructure.auth.jwt_handler import create_refresh_token, hash_password


@pytest.fixture
async def test_tenant(db_session):
    """Create a test tenant with unique slug."""
    from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
    
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    # Use UUID to ensure uniqueness across tests
    unique_id = str(uuid4())[:8]
    tenant = Tenant(
        id=uuid4(),
        name=f"Test Organization {unique_id}",
        slug=f"test-org-{unique_id}",
        plan="free",
        is_active=True,
    )
    tenant = await tenant_repo.create(tenant)
    await db_session.flush()  # Flush instead of commit
    return tenant


@pytest.fixture
async def test_user(db_session, test_tenant):
    """Create a test user with fixed email for integration tests."""
    from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
    from app.domain.value_objects.email import Email
    
    user_repo = SQLAlchemyUserRepository(db_session)
    # Use fixed email for predictable tests
    user = User(
        id=uuid4(),
        email=Email("testuser@example.com"),
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name="User",
        tenant_id=test_tenant.id,
        is_active=True,
        email_verified=True,
    )
    user = await user_repo.create(user)
    await db_session.flush()  # Flush instead of commit
    return user


@pytest.fixture
def mock_email_service():
    """Mock get_email_service to avoid sending real emails."""
    with patch("app.infrastructure.email.get_email_service") as mock:
        mock_instance = AsyncMock()
        mock_instance.send_email = AsyncMock(return_value=True)
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_cache():
    """Mock get_cache to avoid Redis connection."""
    class MockCache:
        def __init__(self):
            self._store = {}
        
        async def get(self, key: str):
            return self._store.get(key)
        
        async def set(self, key: str, value: str, ex: int = None):
            self._store[key] = value
        
        async def delete(self, key: str):
            self._store.pop(key, None)
    
    with patch("app.infrastructure.cache.get_cache") as mock:
        mock.return_value = MockCache()
        yield mock.return_value


@pytest.fixture
async def auth_client(db_session, mock_cache):
    """HTTP auth_client with DB session and cache override."""
    from httpx import AsyncClient, ASGITransport
    from app.infrastructure.database.connection import get_db_session
    from app.main import app
    
    # Override get_db_session dependency
    async def override_get_db_session():
        yield db_session
    
    app.dependency_overrides[get_db_session] = override_get_db_session
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()


# ============================================================================
# LOGIN ENDPOINT TESTS
# ============================================================================

class TestLoginEndpoint:
    """Tests for POST /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, auth_client, test_user, db_session):
        """Test successful login with valid credentials."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, auth_client):
        """Test login with invalid email format."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "invalid-email",
                "password": "TestPassword123!",
            },
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, auth_client, test_user):
        """Test login with incorrect password."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "WrongPassword123!",
            },
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, auth_client):
        """Test login with non-existent email."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "TestPassword123!",
            },
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, auth_client, test_user, db_session):
        """Test login with inactive account."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        
        # Deactivate user
        user_repo = SQLAlchemyUserRepository(db_session)
        test_user.is_active = False
        await user_repo.update(test_user)
        await db_session.commit()
        
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"]["code"] == "USER_INACTIVE"

    @pytest.mark.asyncio
    async def test_login_creates_session(self, auth_client, test_user, db_session):
        """Test that login creates a session record in database."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify session was created
        from app.infrastructure.database.repositories.session_repository import SQLAlchemySessionRepository
        session_repo = SQLAlchemySessionRepository(db_session)
        sessions = await session_repo.get_active_sessions_by_user(test_user.id)
        
        assert len(sessions) > 0
        assert sessions[0].user_id == test_user.id

    @pytest.mark.asyncio
    async def test_login_updates_last_login(self, auth_client, test_user, db_session):
        """Test that login updates last_login timestamp."""
        old_last_login = test_user.last_login
        
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Refresh user from DB
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        user_repo = SQLAlchemyUserRepository(db_session)
        updated_user = await user_repo.get_by_id(test_user.id)
        
        assert updated_user.last_login > (old_last_login or datetime.now(UTC) - timedelta(minutes=1))


# ============================================================================
# REGISTER ENDPOINT TESTS
# ============================================================================

class TestRegisterEndpoint:
    """Tests for POST /auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, auth_client, db_session, mock_email_service):
        """Test successful user registration."""
        response = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecureP@ss123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["first_name"] == "New"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_creates_tenant(self, auth_client, db_session, mock_email_service):
        """Test that registration creates a default tenant."""
        response = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser2@example.com",
                "password": "SecureP@ss123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        # Verify tenant was created
        from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
        tenant_repo = SQLAlchemyTenantRepository(db_session)
        tenant = await tenant_repo.get_by_id(data["tenant_id"])
        
        assert tenant is not None
        assert tenant.plan == "free"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_client, test_user, mock_email_service):
        """Test registration with already existing email."""
        response = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": "testuser@example.com",  # Already exists
                "password": "SecureP@ss123",
                "first_name": "Duplicate",
                "last_name": "User",
            },
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_register_weak_password(self, auth_client, mock_email_service):
        """Test registration with weak password."""
        response = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser3@example.com",
                "password": "weak",  # Too weak
                "first_name": "New",
                "last_name": "User",
            },
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_sends_verification_email(self, auth_client, db_session, mock_email_service):
        """Test that registration sends verification email."""
        with patch("app.config.settings.EMAIL_VERIFICATION_REQUIRED", True):
            response = await auth_client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser4@example.com",
                    "password": "SecureP@ss123",
                    "first_name": "New",
                    "last_name": "User",
                },
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            # Verify email service was called
            assert mock_email_service.send_email.called


# ============================================================================
# REFRESH TOKEN TESTS
# ============================================================================

class TestRefreshTokenEndpoint:
    """Tests for POST /auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, auth_client, test_user, db_session):
        """Test successful token refresh."""
        # Create a valid refresh token
        refresh_token = create_refresh_token(
            user_id=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        
        response = await auth_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, auth_client):
        """Test refresh with invalid token."""
        response = await auth_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token_here"},
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_revokes_old_token(self, auth_client, test_user, db_session):
        """Test that refresh revokes the old session."""
        refresh_token = create_refresh_token(
            user_id=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        
        # First refresh - should succeed
        response1 = await auth_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response1.status_code == status.HTTP_200_OK
        
        # Second refresh with same token - should fail
        response2 = await auth_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response2.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# LOGOUT TESTS
# ============================================================================

class TestLogoutEndpoint:
    """Tests for POST /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, auth_client, test_user, db_session):
        """Test successful logout."""
        # Login first
        login_response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Logout
        response = await auth_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Successfully logged out"

    @pytest.mark.asyncio
    async def test_logout_revokes_session(self, auth_client, test_user, db_session):
        """Test that logout revokes the session in database."""
        # Login
        login_response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Verify session exists
        from app.infrastructure.database.repositories.session_repository import SQLAlchemySessionRepository
        session_repo = SQLAlchemySessionRepository(db_session)
        sessions_before = await session_repo.get_active_sessions_by_user(test_user.id)
        assert len(sessions_before) > 0
        
        # Logout
        await auth_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        # Verify session was revoked
        sessions_after = await session_repo.get_active_sessions_by_user(test_user.id)
        assert len(sessions_after) == 0


# ============================================================================
# CHANGE PASSWORD TESTS
# ============================================================================

class TestChangePasswordEndpoint:
    """Tests for POST /auth/change-password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_client, test_user, db_session):
        """Test successful password change."""
        # Login first
        login_response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Change password
        response = await auth_client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewPassword456!",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, auth_client, test_user):
        """Test password change with incorrect current password."""
        # Login first
        login_response = await auth_client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Try to change with wrong current password
        response = await auth_client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewPassword456!",
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# FORGOT/RESET PASSWORD TESTS
# ============================================================================

class TestForgotPasswordEndpoint:
    """Tests for POST /auth/forgot-password endpoint."""

    @pytest.mark.asyncio
    async def test_forgot_password_sends_email(self, auth_client, test_user, mock_email_service):
        """Test that forgot password sends reset email."""
        response = await auth_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "testuser@example.com"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "reset link" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(self, auth_client, mock_email_service):
        """Test forgot password with non-existent email (returns generic message)."""
        response = await auth_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        
        # Should return success to prevent email enumeration
        assert response.status_code == status.HTTP_200_OK


class TestResetPasswordEndpoint:
    """Tests for POST /auth/reset-password endpoint."""

    @pytest.mark.asyncio
    async def test_reset_password_success(self, auth_client, test_user, db_session):
        """Test successful password reset with valid token."""
        # Manually set reset token for test user
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        import secrets
        
        user_repo = SQLAlchemyUserRepository(db_session)
        reset_token = secrets.token_urlsafe(32)
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)
        await user_repo.update(test_user)
        await db_session.commit()
        
        # Reset password
        response = await auth_client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "NewResetPassword123!",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, auth_client):
        """Test password reset with invalid token."""
        response = await auth_client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid_token",
                "new_password": "NewPassword123!",
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self, auth_client, test_user, db_session):
        """Test password reset with expired token."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        import secrets
        
        user_repo = SQLAlchemyUserRepository(db_session)
        reset_token = secrets.token_urlsafe(32)
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = datetime.now(UTC) - timedelta(hours=1)  # Expired
        await user_repo.update(test_user)
        await db_session.commit()
        
        response = await auth_client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "NewPassword123!",
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# EMAIL VERIFICATION TESTS
# ============================================================================

class TestVerifyEmailEndpoint:
    """Tests for POST /auth/verify-email endpoint."""

    @pytest.mark.asyncio
    async def test_verify_email_success(self, auth_client, test_user, db_session):
        """Test successful email verification."""
        from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
        import secrets
        
        # Set verification token
        user_repo = SQLAlchemyUserRepository(db_session)
        verification_token = secrets.token_urlsafe(32)
        test_user.email_verification_token = verification_token
        test_user.is_verified = False
        await user_repo.update(test_user)
        await db_session.commit()
        
        # Verify email
        response = await auth_client.post(
            f"/api/v1/auth/verify-email/{verification_token}",
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check user is verified
        updated_user = await user_repo.get_by_id(test_user.id)
        assert updated_user.is_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, auth_client):
        """Test email verification with invalid token."""
        response = await auth_client.post(
            "/api/v1/auth/verify-email/invalid_token_here",
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

