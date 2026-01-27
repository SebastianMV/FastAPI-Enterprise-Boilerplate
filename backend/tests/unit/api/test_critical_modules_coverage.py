# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Critical modules coverage tests.
Targets: auth.py, users.py, roles.py, tenants.py, mfa.py - 100% coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone, timedelta


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


# =============================================================================
# AUTH.PY COVERAGE TESTS (lines 739, 746-747 - password reset tokens)
# =============================================================================

class TestAuthPasswordReset:
    """Tests for password reset endpoints."""

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, mock_session):
        """Test reset_password with invalid token (lines 739)."""
        from app.api.v1.endpoints.auth import reset_password
        from app.api.v1.schemas.auth import ResetPasswordRequest
        
        request = ResetPasswordRequest(
            token="invalid_token_12345",
            new_password="NewPassword123!",
        )
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await reset_password(request=request, session=mock_session)
        
        assert exc.value.status_code == 400
        assert "INVALID_TOKEN" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self, mock_session):
        """Test reset_password with expired token (lines 746-747)."""
        from app.api.v1.endpoints.auth import reset_password
        from app.api.v1.schemas.auth import ResetPasswordRequest
        import app.api.v1.endpoints.auth as auth_module
        
        # Add an expired token
        expired_time = datetime.now(timezone.utc) - timedelta(hours=2)
        auth_module._password_reset_tokens["expired_reset_123"] = {
            "user_id": uuid4(),
            "email": "test@example.com",
            "expires_at": expired_time,
        }
        
        request = ResetPasswordRequest(
            token="expired_reset_123",
            new_password="NewPassword123!",
        )
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await reset_password(request=request, session=mock_session)
        
        assert exc.value.status_code == 400
        assert "TOKEN_EXPIRED" in str(exc.value.detail)


# =============================================================================
# USERS.PY COVERAGE TESTS (lines 165, 297, 399-407, 450-452)
# =============================================================================

class TestUsersDeleteAndAvatar:
    """Tests for users delete and avatar endpoints."""

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, mock_session):
        """Test delete_user with non-existent user (line 297)."""
        from app.api.v1.endpoints.users import delete_user
        from app.domain.exceptions.base import EntityNotFoundError
        
        user_id = uuid4()
        superuser_id = uuid4()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.delete.side_effect = EntityNotFoundError(
                code="USER_NOT_FOUND",
                message="User not found"
            )
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await delete_user(
                    user_id=user_id,
                    superuser_id=superuser_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_avatar_storage_error(self, mock_session):
        """Test delete_avatar handles storage errors gracefully (lines 450-452)."""
        from app.api.v1.endpoints.users import delete_avatar
        
        current_user_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = current_user_id
        mock_user.avatar_url = "/storage/avatars/test.png"
        mock_user.mark_updated = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.users.get_storage") as mock_get_storage:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update = AsyncMock()
            mock_repo_cls.return_value = mock_repo
            
            mock_storage = AsyncMock()
            mock_storage.delete.side_effect = Exception("Storage error")
            mock_get_storage.return_value = mock_storage
            
            # Should succeed even if storage delete fails
            result = await delete_avatar(
                current_user_id=current_user_id,
                session=mock_session,
            )
            
            assert result.message == "Avatar deleted successfully"

    @pytest.mark.asyncio
    async def test_delete_avatar_no_avatar(self, mock_session):
        """Test delete_avatar when user has no avatar (lines 438-441)."""
        from app.api.v1.endpoints.users import delete_avatar
        
        current_user_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = current_user_id
        mock_user.avatar_url = None  # No avatar
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await delete_avatar(
                    current_user_id=current_user_id,
                    session=mock_session,
                )
            
            # It returns 400, not 404
            assert exc.value.status_code == 400
            assert "NO_AVATAR" in str(exc.value.detail)


# =============================================================================
# ROLES.PY COVERAGE TESTS (lines 168, 203, 215, 221, 288-297)
# =============================================================================

class TestRolesUpdateAndPermissions:
    """Tests for roles update and permissions endpoints."""

    @pytest.mark.asyncio
    async def test_update_role_entity_not_found_error(self, mock_session):
        """Test update_role handles EntityNotFoundError (lines 221)."""
        from app.api.v1.endpoints.roles import update_role
        from app.api.v1.schemas.roles import RoleUpdate
        from app.domain.exceptions.base import EntityNotFoundError
        
        role_id = uuid4()
        superuser_id = uuid4()
        request = RoleUpdate(name="new_name")
        
        mock_role = MagicMock()
        mock_role.id = role_id
        mock_role.name = "old_name"
        mock_role.description = "desc"
        mock_role.permissions = []
        mock_role.mark_updated = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_role
            mock_repo.update.side_effect = EntityNotFoundError(
                code="ROLE_NOT_FOUND",
                message="Role not found during update"
            )
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_role(
                    role_id=role_id,
                    request=request,
                    superuser_id=superuser_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_permissions_user_not_found(self, mock_session):
        """Test get_user_permissions with non-existent user (lines 288-290)."""
        from app.api.v1.endpoints.roles import get_user_permissions
        
        user_id = uuid4()
        current_user_id = uuid4()  # Changed from superuser_id to current_user_id
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyUserRepository") as mock_user_repo_cls, \
             patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_role_repo_cls:
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_id.return_value = None  # User not found
            mock_user_repo_cls.return_value = mock_user_repo
            
            mock_role_repo = AsyncMock()
            mock_role_repo_cls.return_value = mock_role_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await get_user_permissions(
                    user_id=user_id,
                    current_user_id=current_user_id,  # Fixed parameter name
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404
            assert "USER_NOT_FOUND" in str(exc.value.detail)


# =============================================================================
# TENANTS.PY COVERAGE TESTS (lines 110, 216, 225, 235, 237, 239, 303)
# =============================================================================

class TestTenantsCreateAndActivate:
    """Tests for tenants create and activate endpoints."""

    @pytest.mark.asyncio
    async def test_create_tenant_domain_conflict(self):
        """Test create_tenant with conflicting domain (line 110)."""
        from app.api.v1.endpoints.tenants import create_tenant
        from app.api.v1.schemas.tenants import TenantCreate
        
        data = TenantCreate(
            name="Test Tenant",
            slug="test-tenant",
            domain="existing.com",
        )
        
        mock_repo = AsyncMock()
        mock_repo.slug_exists.return_value = False
        mock_repo.domain_exists.return_value = True  # Domain exists
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await create_tenant(
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )
        
        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_tenant_all_fields(self):
        """Test update_tenant updates all fields (lines 225-239)."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        
        tenant_id = uuid4()
        data = TenantUpdate(
            name="New Name",
            email="new@example.com",
            phone="+1234567890",
            timezone="America/New_York",
            locale="en-US",
            plan="professional",  # Valid plan value
        )
        
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "current"
        mock_tenant.domain = None
        mock_tenant.name = "Old Name"
        mock_tenant.email = None
        mock_tenant.phone = None
        mock_tenant.timezone = "UTC"
        mock_tenant.locale = "en"
        mock_tenant.plan = "free"
        mock_tenant.settings = MagicMock(
            enable_2fa=True,
            enable_api_keys=True,
            enable_webhooks=False,
            max_users=10,
            max_api_keys_per_user=5,
            max_storage_mb=1024,
            primary_color="#000000",
            logo_url=None,
            password_min_length=8,
            session_timeout_minutes=60,
            require_email_verification=True,
        )
        mock_tenant.mark_updated = MagicMock()
        mock_tenant.is_active = True
        mock_tenant.is_verified = True
        mock_tenant.created_at = datetime.now(timezone.utc)
        mock_tenant.updated_at = datetime.now(timezone.utc)
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.update.return_value = mock_tenant
        
        result = await update_tenant(
            tenant_id=tenant_id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )
        
        # Verify fields were updated
        assert mock_tenant.name == "New Name"
        assert mock_tenant.email == "new@example.com"

    @pytest.mark.asyncio
    async def test_set_tenant_active_not_found(self):
        """Test set_tenant_active with non-existent tenant (line 303)."""
        from app.api.v1.endpoints.tenants import set_tenant_active
        from app.api.v1.schemas.tenants import TenantActivateRequest
        
        tenant_id = uuid4()
        data = TenantActivateRequest(is_active=True)
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await set_tenant_active(
                tenant_id=tenant_id,
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )
        
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_set_tenant_active_activate(self):
        """Test set_tenant_active activates tenant."""
        from app.api.v1.endpoints.tenants import set_tenant_active
        from app.api.v1.schemas.tenants import TenantActivateRequest
        
        tenant_id = uuid4()
        data = TenantActivateRequest(is_active=True)
        
        mock_settings = MagicMock(
            enable_2fa=True,
            enable_api_keys=True,
            enable_webhooks=False,
            max_users=10,
            max_api_keys_per_user=5,
            max_storage_mb=1024,
            primary_color="#000000",
            logo_url=None,
            password_min_length=8,
            session_timeout_minutes=60,
            require_email_verification=True,
        )
        
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.is_active = False
        mock_tenant.activate = MagicMock()
        mock_tenant.deactivate = MagicMock()
        mock_tenant.mark_updated = MagicMock()
        mock_tenant.name = "Test"
        mock_tenant.slug = "test"
        mock_tenant.domain = None
        mock_tenant.plan = "free"
        mock_tenant.email = None
        mock_tenant.phone = None
        mock_tenant.timezone = "UTC"
        mock_tenant.locale = "en"
        mock_tenant.settings = mock_settings
        mock_tenant.is_verified = True
        mock_tenant.created_at = datetime.now(timezone.utc)
        mock_tenant.updated_at = datetime.now(timezone.utc)
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.update.return_value = mock_tenant
        
        await set_tenant_active(
            tenant_id=tenant_id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )
        
        mock_tenant.activate.assert_called_once()
        mock_tenant.deactivate.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_tenant_active_deactivate(self):
        """Test set_tenant_active deactivates tenant."""
        from app.api.v1.endpoints.tenants import set_tenant_active
        from app.api.v1.schemas.tenants import TenantActivateRequest
        
        tenant_id = uuid4()
        data = TenantActivateRequest(is_active=False)
        
        mock_settings = MagicMock(
            enable_2fa=True,
            enable_api_keys=True,
            enable_webhooks=False,
            max_users=10,
            max_api_keys_per_user=5,
            max_storage_mb=1024,
            primary_color="#000000",
            logo_url=None,
            password_min_length=8,
            session_timeout_minutes=60,
            require_email_verification=True,
        )
        
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.is_active = True
        mock_tenant.activate = MagicMock()
        mock_tenant.deactivate = MagicMock()
        mock_tenant.mark_updated = MagicMock()
        mock_tenant.name = "Test"
        mock_tenant.slug = "test"
        mock_tenant.domain = None
        mock_tenant.plan = "free"
        mock_tenant.email = None
        mock_tenant.phone = None
        mock_tenant.timezone = "UTC"
        mock_tenant.locale = "en"
        mock_tenant.settings = mock_settings
        mock_tenant.is_verified = True
        mock_tenant.created_at = datetime.now(timezone.utc)
        mock_tenant.updated_at = datetime.now(timezone.utc)
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.update.return_value = mock_tenant
        
        await set_tenant_active(
            tenant_id=tenant_id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )
        
        mock_tenant.deactivate.assert_called_once()
        mock_tenant.activate.assert_not_called()


# =============================================================================
# MFA.PY COVERAGE TESTS (line 233)
# =============================================================================

class TestMFADisable:
    """Tests for MFA disable endpoint."""

    @pytest.mark.asyncio
    async def test_disable_mfa_password_verification_branch(self, mock_session):
        """Test disable_mfa goes through password verification (line 233 is pass stmt)."""
        from app.api.v1.endpoints.mfa import disable_mfa, get_mfa_config, get_mfa_service
        from app.api.v1.schemas.mfa import MFADisableRequest
        
        # Request with valid 6-digit code and password
        request = MFADisableRequest(
            code="123456",
            password="ValidPassword123!",
        )
        
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.mfa_enabled = True
        # verify_password returns False to trigger the pass branch (line 233)
        mock_user.verify_password = MagicMock(return_value=False)
        
        mock_config = MagicMock()
        mock_config.is_enabled = True
        
        mock_mfa_service = MagicMock()
        mock_mfa_service.disable_mfa.return_value = True
        
        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config, \
             patch("app.api.v1.endpoints.mfa.save_mfa_config") as mock_save_config:
            
            mock_get_config.return_value = mock_config
            
            result = await disable_mfa(
                request=request,
                current_user=mock_user,
                mfa_service=mock_mfa_service,
            )
            
            # Should succeed because the pass statement allows flow to continue
            assert result.success is True
            mock_user.verify_password.assert_called_once()


# =============================================================================
# ADDITIONAL COVERAGE TESTS
# =============================================================================

class TestTenantsAdditionalCoverage:
    """Additional tests for tenants coverage."""

    @pytest.mark.asyncio
    async def test_create_tenant_with_custom_settings(self):
        """Test create_tenant with custom settings (line 110+)."""
        from app.api.v1.endpoints.tenants import create_tenant
        from app.api.v1.schemas.tenants import TenantCreate, TenantSettingsSchema
        
        data = TenantCreate(
            name="Test Tenant",
            slug="test-tenant-custom",
            settings=TenantSettingsSchema(
                enable_2fa=True,
                enable_api_keys=True,
                enable_webhooks=True,
                max_users=50,
                max_api_keys_per_user=10,
                max_storage_mb=5000,
                primary_color="#000000",
            ),
        )
        
        mock_repo = AsyncMock()
        mock_repo.slug_exists.return_value = False
        mock_repo.domain_exists.return_value = False
        
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.name = "Test Tenant"
        mock_tenant.slug = "test-tenant-custom"
        mock_tenant.domain = None
        mock_tenant.plan = "free"
        mock_tenant.email = None
        mock_tenant.phone = None
        mock_tenant.timezone = "UTC"
        mock_tenant.locale = "en"
        mock_tenant.is_active = True
        mock_tenant.is_verified = False
        mock_tenant.plan_expires_at = None
        mock_tenant.settings = MagicMock(
            enable_2fa=True,
            enable_api_keys=True,
            enable_webhooks=True,
            max_users=50,
            max_api_keys_per_user=10,
            max_storage_mb=5000,
            primary_color="#000000",  # Required non-null
            logo_url=None,
            password_min_length=8,
            session_timeout_minutes=60,
            require_email_verification=False,
        )
        mock_tenant.created_at = datetime.now(timezone.utc)
        mock_tenant.updated_at = datetime.now(timezone.utc)
        mock_repo.create.return_value = mock_tenant
        
        result = await create_tenant(
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )
        
        assert result.name == "Test Tenant"

    @pytest.mark.asyncio
    async def test_update_tenant_slug_conflict(self):
        """Test update_tenant with conflicting slug (line 216)."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        
        tenant_id = uuid4()
        data = TenantUpdate(slug="existing-slug")
        
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "old-slug"
        mock_tenant.domain = None
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.slug_exists.return_value = True  # Slug exists
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=tenant_id,
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )
        
        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_tenant_domain_conflict(self):
        """Test update_tenant with conflicting domain (line 225)."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        
        tenant_id = uuid4()
        data = TenantUpdate(domain="existing.com")
        
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "test"
        mock_tenant.domain = "old.com"
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.domain_exists.return_value = True  # Domain exists
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=tenant_id,
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )
        
        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)


class TestUsersAdditionalCoverage:
    """Additional tests for users coverage."""

    @pytest.mark.asyncio
    async def test_create_user_conflict_error(self, mock_session):
        """Test create_user with ConflictError (line 165)."""
        from app.api.v1.endpoints.users import create_user
        from app.api.v1.schemas.users import UserCreate
        from app.domain.exceptions.base import ConflictError
        
        request = UserCreate(
            email="existing@example.com",
            first_name="Test",
            last_name="User",
            password="Password123!",
        )
        tenant_id = uuid4()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.users.hash_password") as mock_hash:
            
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = None
            mock_repo.create.side_effect = ConflictError(
                code="EMAIL_EXISTS",
                message="Email already exists"
            )
            mock_repo_cls.return_value = mock_repo
            mock_hash.return_value = "hashed"
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_user(
                    request=request,
                    superuser_id=uuid4(),
                    tenant_id=tenant_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 409
            assert "EMAIL_EXISTS" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_self_user_not_found(self, mock_session):
        """Test update_self with user not found (lines 199-208)."""
        from app.api.v1.endpoints.users import update_self
        from app.api.v1.schemas.users import UserUpdateSelf
        
        request = UserUpdateSelf(first_name="New Name")
        current_user_id = uuid4()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_self(
                    request=request,
                    current_user_id=current_user_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404
            assert "USER_NOT_FOUND" in str(exc.value.detail)


class TestRolesAdditionalCoverage:
    """Additional tests for roles coverage."""

    @pytest.mark.asyncio
    async def test_create_role_conflict_error(self, mock_session):
        """Test create_role with ConflictError (line 168)."""
        from app.api.v1.endpoints.roles import create_role
        from app.api.v1.schemas.roles import RoleCreate
        from app.domain.exceptions.base import ConflictError
        
        request = RoleCreate(name="existing_role", description="Test")
        tenant_id = uuid4()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_name.return_value = None
            mock_repo.create.side_effect = ConflictError(
                code="ROLE_EXISTS",
                message="Role already exists"
            )
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_role(
                    request=request,
                    superuser_id=uuid4(),
                    tenant_id=tenant_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_role_with_permissions_validation(self, mock_session):
        """Test update_role with permissions validation (lines 203, 215, 221)."""
        from app.api.v1.endpoints.roles import update_role
        from app.api.v1.schemas.roles import RoleUpdate
        
        role_id = uuid4()
        request = RoleUpdate(
            name="new_name",
            permissions=["read:users", "write:users"],
        )
        
        mock_role = MagicMock()
        mock_role.id = role_id
        mock_role.name = "old_name"
        mock_role.description = "desc"
        mock_role.permissions = []
        mock_role.mark_updated = MagicMock()
        mock_role.is_system = False
        mock_role.created_at = datetime.now(timezone.utc)
        mock_role.updated_at = datetime.now(timezone.utc)
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_role
            mock_repo.get_by_name.return_value = None
            mock_repo.update.return_value = mock_role
            mock_repo_cls.return_value = mock_repo
            
            result = await update_role(
                role_id=role_id,
                request=request,
                superuser_id=uuid4(),
                session=mock_session,
            )
            
            # Verify permissions were updated
            assert mock_role.permissions == ["read:users", "write:users"]


# =============================================================================
# AUTH.PY ADDITIONAL COVERAGE (lines 321-322, 342-343, 444-470, 578-579, etc)
# =============================================================================

class TestAuthRegisterFlow:
    """Tests for register flow coverage."""

    @pytest.mark.asyncio
    async def test_register_conflict_error_on_create(self, mock_session):
        """Test register ConflictError during user creation (lines 321-322)."""
        from app.api.v1.endpoints.auth import register
        from app.api.v1.schemas.auth import RegisterRequest
        from app.domain.exceptions.base import ConflictError
        
        request = RegisterRequest(
            email="conflict@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
        )
        
        # Tenant repo is imported inside function, patch at source
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_user_repo, \
             patch("app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository") as mock_tenant_repo, \
             patch("app.api.v1.endpoints.auth.Email") as mock_email, \
             patch("app.api.v1.endpoints.auth.hash_password") as mock_hash:
            
            mock_email.return_value = MagicMock()
            mock_hash.return_value = "hashed_password"
            
            # Mock tenant repo  
            mock_tenant = MagicMock()
            mock_tenant.id = uuid4()
            mock_tenant_repo_instance = AsyncMock()
            mock_tenant_repo_instance.get_default_tenant.return_value = mock_tenant
            mock_tenant_repo.return_value = mock_tenant_repo_instance
            
            # Mock user repo to throw ConflictError on create
            mock_user_repo_instance = AsyncMock()
            mock_user_repo_instance.get_by_email.return_value = None
            mock_user_repo_instance.create.side_effect = ConflictError(
                code="EMAIL_EXISTS",
                message="Email already exists"
            )
            mock_user_repo.return_value = mock_user_repo_instance
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await register(request=request, session=mock_session)
            
            assert exc.value.status_code == 409


class TestAuthTokenRotation:
    """Tests for token rotation coverage."""

    @pytest.mark.asyncio
    async def test_refresh_token_rotation_with_session(self, mock_session):
        """Test refresh token rotates session (lines 444-470)."""
        from app.api.v1.endpoints.auth import refresh_token
        from app.api.v1.schemas.auth import RefreshTokenRequest
        
        request = RefreshTokenRequest(refresh_token="valid_refresh_token")
        
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.tenant_id = uuid4()
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.roles = []
        
        mock_old_session = MagicMock()
        mock_old_session.id = uuid4()
        mock_old_session.device_name = "Chrome"
        mock_old_session.device_type = "desktop"
        mock_old_session.browser = "Chrome"
        mock_old_session.os = "Windows"
        mock_old_session.ip_address = "127.0.0.1"
        mock_old_session.location = "Local"
        
        mock_session_repo_instance = AsyncMock()
        mock_session_repo_instance.get_by_token_hash.return_value = mock_old_session
        mock_session_repo_instance.revoke = AsyncMock()
        mock_session_repo_instance.create = AsyncMock()
        
        with patch("app.api.v1.endpoints.auth.validate_refresh_token") as mock_validate, \
             patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_user_repo, \
             patch("app.infrastructure.database.repositories.session_repository.SQLAlchemySessionRepository") as mock_session_repo, \
             patch("app.api.v1.endpoints.auth.create_access_token") as mock_access, \
             patch("app.api.v1.endpoints.auth.create_refresh_token") as mock_refresh, \
             patch("app.api.v1.endpoints.auth.hash_password") as mock_hash, \
             patch("app.infrastructure.auth.jwt_handler.decode_token") as mock_decode, \
             patch("app.api.v1.endpoints.auth.settings") as mock_settings:
            
            # Setup mocks
            mock_validate.return_value = {
                "sub": str(mock_user.id),
                "tenant_id": str(mock_user.tenant_id),
                "jti": "old_jti_123",
            }
            
            mock_user_repo_instance = AsyncMock()
            mock_user_repo_instance.get_by_id.return_value = mock_user
            mock_user_repo.return_value = mock_user_repo_instance
            
            mock_session_repo.return_value = mock_session_repo_instance
            
            mock_access.return_value = "new_access_token"
            mock_refresh.return_value = "new_refresh_token"
            mock_hash.return_value = "hashed_jti"
            mock_decode.return_value = {"jti": "new_jti_456"}
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
            
            result = await refresh_token(request=request, session=mock_session)
            
            assert result.access_token == "new_access_token"
            assert result.refresh_token == "new_refresh_token"
            mock_session_repo_instance.revoke.assert_called_once()


class TestAuthChangePasswordFlow:
    """Tests for change password flow coverage."""

    @pytest.mark.asyncio
    async def test_change_password_weak_password_validation(self, mock_session):
        """Test change_password with weak password (lines 578-579)."""
        from app.api.v1.endpoints.auth import change_password
        from app.api.v1.schemas.auth import ChangePasswordRequest
        
        # Create request with valid format but will fail on Password validation
        request = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="weakpass1",  # min 8 chars but weak
        )
        
        with patch("app.api.v1.endpoints.auth.Password") as mock_password:
            mock_password.side_effect = ValueError("Password must contain uppercase")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await change_password(
                    request=request,
                    current_user_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 400
            assert "WEAK_PASSWORD" in str(exc.value.detail)


class TestAuthForgotPasswordFlow:
    """Tests for forgot password flow coverage."""

    @pytest.mark.asyncio
    async def test_forgot_password_sends_email(self, mock_session):
        """Test forgot_password sends reset email (lines 663, 672)."""
        from app.api.v1.endpoints.auth import forgot_password
        from app.api.v1.schemas.auth import ForgotPasswordRequest
        
        request = ForgotPasswordRequest(email="test@example.com")
        
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.auth.settings") as mock_settings, \
             patch("app.infrastructure.email.get_email_service") as mock_get_email:
            
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            
            mock_email_service = AsyncMock()
            mock_get_email.return_value = mock_email_service
            
            result = await forgot_password(request=request, session=mock_session)
            
            assert result.success is True


class TestAuthResendVerification:
    """Tests for resend verification coverage."""

    @pytest.mark.asyncio
    async def test_send_verification_email_flow(self, mock_session):
        """Test send verification email (lines 853-855)."""
        from app.api.v1.endpoints.auth import send_verification_email
        
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.email_verified = False
        mock_user.generate_verification_token.return_value = "new_token"
        
        mock_email_service = AsyncMock()
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.auth.settings") as mock_settings, \
             patch("app.infrastructure.email.get_email_service") as mock_get_email:
            
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update = AsyncMock()
            mock_repo_cls.return_value = mock_repo
            
            mock_settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24
            mock_settings.CORS_ORIGINS = ["http://localhost:3000"]
            
            mock_get_email.return_value = mock_email_service
            
            result = await send_verification_email(
                user_id=mock_user.id,
                session=mock_session,
            )
            
            assert result.success is True


# =============================================================================
# USERS.PY ADDITIONAL COVERAGE (lines 165, 199-208, 297, 399-407)
# =============================================================================

class TestUsersAvatarUpload:
    """Tests for avatar upload coverage."""

    @pytest.mark.asyncio
    async def test_upload_avatar_replaces_old(self, mock_session):
        """Test upload_avatar deletes old avatar (lines 399-407)."""
        from app.api.v1.endpoints.users import upload_avatar
        from fastapi import UploadFile
        from io import BytesIO
        
        # Create mock file
        file_content = b"fake image content"
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "avatar.png"
        mock_file.content_type = "image/png"
        mock_file.read = AsyncMock(return_value=file_content)
        
        current_user_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = current_user_id
        mock_user.avatar_url = "/storage/avatars/old.png"  # Has old avatar
        mock_user.mark_updated = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.email_verified = True
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        
        mock_storage_file = MagicMock()
        mock_storage_file.url = "/storage/avatars/new.png"
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.users.get_storage") as mock_get_storage:
            
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            mock_storage = AsyncMock()
            mock_storage.upload.return_value = mock_storage_file
            mock_storage.delete = AsyncMock()  # Should be called for old avatar
            mock_get_storage.return_value = mock_storage
            
            result = await upload_avatar(
                file=mock_file,
                current_user_id=current_user_id,
                session=mock_session,
            )
            
            # Verify old avatar was deleted
            mock_storage.delete.assert_called_once()

    @pytest.mark.asyncio  
    async def test_upload_avatar_delete_old_fails_gracefully(self, mock_session):
        """Test upload_avatar continues if old avatar delete fails (lines 405-407)."""
        from app.api.v1.endpoints.users import upload_avatar
        from fastapi import UploadFile
        
        # Create mock file
        file_content = b"fake image content"
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "avatar.png"
        mock_file.content_type = "image/png"
        mock_file.read = AsyncMock(return_value=file_content)
        
        current_user_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = current_user_id
        mock_user.avatar_url = "/storage/avatars/old.png"
        mock_user.mark_updated = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.email_verified = True
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        
        mock_storage_file = MagicMock()
        mock_storage_file.url = "/storage/avatars/new.png"
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.users.get_storage") as mock_get_storage:
            
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            mock_storage = AsyncMock()
            mock_storage.upload.return_value = mock_storage_file
            mock_storage.delete.side_effect = Exception("Delete failed")  # Fails but should continue
            mock_get_storage.return_value = mock_storage
            
            result = await upload_avatar(
                file=mock_file,
                current_user_id=current_user_id,
                session=mock_session,
            )
            
            # Should succeed despite delete failure
            assert result is not None


class TestUsersDeleteFlow:
    """Tests for user delete flow coverage."""

    @pytest.mark.asyncio
    async def test_delete_user_self_deletion_blocked(self, mock_session):
        """Test delete_user blocks self-deletion (line 297)."""
        from app.api.v1.endpoints.users import delete_user
        
        user_id = uuid4()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await delete_user(
                user_id=user_id,
                superuser_id=user_id,  # Same as user_id = self-deletion
                session=mock_session,
            )
        
        assert exc.value.status_code == 400
        assert "CANNOT_DELETE_SELF" in str(exc.value.detail)


# =============================================================================
# ROLES.PY ADDITIONAL COVERAGE (lines 168, 203, 288-297)
# =============================================================================

class TestRolesAdditionalFlows:
    """Additional tests for roles coverage."""

    @pytest.mark.asyncio
    async def test_create_role_success(self, mock_session):
        """Test create_role successful path (line 168)."""
        from app.api.v1.endpoints.roles import create_role
        from app.api.v1.schemas.roles import RoleCreate
        
        request = RoleCreate(name="new_role", description="A new role")
        tenant_id = uuid4()
        
        mock_role = MagicMock()
        mock_role.id = uuid4()
        mock_role.name = "new_role"
        mock_role.description = "A new role"
        mock_role.permissions = []
        mock_role.is_system = False
        mock_role.created_at = datetime.now(timezone.utc)
        mock_role.updated_at = datetime.now(timezone.utc)
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_name.return_value = None
            mock_repo.create.return_value = mock_role
            mock_repo_cls.return_value = mock_repo
            
            result = await create_role(
                request=request,
                superuser_id=uuid4(),
                tenant_id=tenant_id,
                session=mock_session,
            )
            
            assert result.name == "new_role"

    @pytest.mark.asyncio
    async def test_update_role_with_invalid_permission(self, mock_session):
        """Test update_role with invalid permission format (line 203)."""
        from app.api.v1.endpoints.roles import update_role
        from app.api.v1.schemas.roles import RoleUpdate
        
        role_id = uuid4()
        request = RoleUpdate(permissions=["invalid-permission-format"])
        
        mock_role = MagicMock()
        mock_role.id = role_id
        mock_role.name = "test_role"
        mock_role.description = "Test"
        mock_role.permissions = []
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.roles.Permission") as mock_permission:
            
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_role
            mock_repo_cls.return_value = mock_repo
            
            # Make Permission.from_string raise ValueError
            mock_permission.from_string.side_effect = ValueError("Invalid permission format")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_role(
                    role_id=role_id,
                    request=request,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 400
            assert "INVALID_PERMISSION" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_get_user_permissions_success(self, mock_session):
        """Test get_user_permissions successful path (lines 288-297)."""
        from app.api.v1.endpoints.roles import get_user_permissions
        
        user_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_superuser = False
        
        mock_role = MagicMock()
        mock_role.id = uuid4()
        mock_role.name = "user"
        mock_role.description = "User role"
        mock_role.permissions = ["read:users"]
        mock_role.is_system = False
        mock_role.created_at = datetime.now(timezone.utc)
        mock_role.updated_at = datetime.now(timezone.utc)
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyUserRepository") as mock_user_repo_cls, \
             patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_role_repo_cls, \
             patch("app.api.v1.endpoints.roles.ACLService") as mock_acl_cls:
            
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_id.return_value = mock_user
            mock_user_repo_cls.return_value = mock_user_repo
            
            mock_role_repo = AsyncMock()
            mock_role_repo.get_user_roles.return_value = [mock_role]
            mock_role_repo_cls.return_value = mock_role_repo
            
            mock_acl = AsyncMock()
            mock_acl.get_user_permissions.return_value = ["read:users"]
            mock_acl_cls.return_value = mock_acl
            
            result = await get_user_permissions(
                user_id=user_id,
                current_user_id=uuid4(),
                session=mock_session,
            )
            
            assert result.user_id == user_id
            assert "read:users" in result.permissions


# =============================================================================
# TENANTS.PY FINAL COVERAGE (lines 216, 225 - slug/domain exists checks)
# =============================================================================

class TestTenantsSlugDomainExistsCheck:
    """Tests for tenant slug/domain exists checks in update."""

    @pytest.mark.asyncio
    async def test_update_tenant_slug_exists_check(self, mock_session):
        """Test update_tenant when slug already exists (line 216)."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        
        tenant_id = uuid4()
        
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "old-slug"
        mock_tenant.domain = "old.example.com"
        
        request = TenantUpdate(slug="new-slug")  # Trying to change slug
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.slug_exists.return_value = True  # Slug already exists!
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=tenant_id,
                data=request,
                current_user_id=uuid4(),
                repo=mock_repo,
            )
        
        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_tenant_domain_exists_check(self, mock_session):
        """Test update_tenant when domain already exists (line 225)."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        
        tenant_id = uuid4()
        
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "current-slug"
        mock_tenant.domain = "old.example.com"
        
        request = TenantUpdate(domain="new.example.com")  # Trying to change domain
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.domain_exists.return_value = True  # Domain already exists!
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=tenant_id,
                data=request,
                current_user_id=uuid4(),
                repo=mock_repo,
            )
        
        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)


# =============================================================================
# USERS.PY FINAL COVERAGE (lines 165, 199-208)
# =============================================================================

class TestUsersCreateSuccess:
    """Tests for user creation success path."""

    @pytest.mark.asyncio
    async def test_create_user_success_path(self, mock_session):
        """Test create_user success path (line 165)."""
        from app.api.v1.endpoints.users import create_user
        from app.api.v1.schemas.users import UserCreate
        
        tenant_id = uuid4()
        superuser_id = uuid4()
        
        request = UserCreate(
            email="newuser@example.com",
            password="SecurePass123!",
            first_name="New",
            last_name="User",
            is_active=True,
            is_superuser=False,
            roles=[],
        )
        
        mock_created_user = MagicMock()
        mock_created_user.id = uuid4()
        mock_created_user.tenant_id = tenant_id
        mock_created_user.email = "newuser@example.com"
        mock_created_user.first_name = "New"
        mock_created_user.last_name = "User"
        mock_created_user.avatar_url = None
        mock_created_user.is_active = True
        mock_created_user.is_superuser = False
        mock_created_user.email_verified = False
        mock_created_user.roles = []
        mock_created_user.created_at = datetime.now(timezone.utc)
        mock_created_user.updated_at = datetime.now(timezone.utc)
        mock_created_user.last_login = None
        mock_created_user.created_by = superuser_id
        mock_created_user.updated_by = None
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.users.hash_password") as mock_hash, \
             patch("app.api.v1.endpoints.users.Email") as mock_email:
            
            mock_repo = AsyncMock()
            mock_repo.exists_by_email.return_value = False  # Email does not exist
            mock_repo.create.return_value = mock_created_user
            mock_repo_cls.return_value = mock_repo
            
            mock_hash.return_value = "hashed_password"
            mock_email.return_value = MagicMock()
            
            result = await create_user(
                request=request,
                superuser_id=superuser_id,
                tenant_id=tenant_id,
                session=mock_session,
            )
            
            assert result.email == "newuser@example.com"
            mock_repo.create.assert_called_once()


class TestUsersUpdateSelfNotFound:
    """Tests for update_self user not found."""

    @pytest.mark.asyncio
    async def test_update_self_not_found_raises(self, mock_session):
        """Test update_self raises when user not found (lines 199-208)."""
        from app.api.v1.endpoints.users import update_self
        from app.api.v1.schemas.users import UserUpdateSelf
        
        current_user_id = uuid4()
        request = UserUpdateSelf(first_name="Updated")
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None  # User not found
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_self(
                    request=request,
                    current_user_id=current_user_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404
            assert "USER_NOT_FOUND" in str(exc.value.detail)


# =============================================================================
# AUTH.PY FINAL COVERAGE (lines 898, 936 - verify_email paths)
# =============================================================================

class TestAuthVerifyEmail:
    """Tests for verify_email endpoint coverage."""

    @pytest.mark.asyncio
    async def test_verify_email_user_not_found_after_model(self, mock_session):
        """Test verify_email when user entity not found after model (line 898)."""
        from app.api.v1.endpoints.auth import verify_email
        
        mock_user_model = MagicMock()
        mock_user_model.id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_model
        mock_session.execute.return_value = mock_result
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None  # User entity not found
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await verify_email(
                    token="valid_token",
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404
            assert "USER_NOT_FOUND" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_verify_email_token_expired(self, mock_session):
        """Test verify_email when token has expired (line 936)."""
        from app.api.v1.endpoints.auth import verify_email
        
        mock_user_model = MagicMock()
        mock_user_model.id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_model
        mock_session.execute.return_value = mock_result
        
        mock_user = MagicMock()
        mock_user.id = mock_user_model.id
        mock_user.verify_email.return_value = False  # Token expired
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.auth.settings") as mock_settings:
            
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            mock_settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await verify_email(
                    token="expired_token",
                    session=mock_session,
                )
            
            assert exc.value.status_code == 400
            assert "TOKEN_EXPIRED" in str(exc.value.detail)


# =============================================================================
# TENANTS SLUG/DOMAIN EXISTS (lines 216, 225)
# =============================================================================

class TestTenantsSlugDomainExists:
    """Tests for tenant slug and domain existence checks during update."""

    @pytest.mark.asyncio
    async def test_update_tenant_slug_exists_raises(self):
        """Test update_tenant raises when slug exists on another tenant."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        
        tenant_id = uuid4()
        
        data = TenantUpdate(slug="existing-slug")
        
        mock_repo = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "current-slug"
        mock_tenant.domain = None
        mock_tenant.mark_updated = MagicMock()
        
        mock_repo.get_by_id.return_value = mock_tenant
        # slug_exists returns True indicating the slug is taken by another tenant
        mock_repo.slug_exists.return_value = True
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=tenant_id,
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )
        
        assert exc.value.status_code == 409
        assert "slug" in str(exc.value.detail).lower() or "exists" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_update_tenant_domain_exists_raises(self):
        """Test update_tenant raises when domain exists on another tenant."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        
        tenant_id = uuid4()
        
        data = TenantUpdate(domain="existing-domain.com")
        
        mock_repo = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "current-slug"
        mock_tenant.domain = "old-domain.com"
        mock_tenant.mark_updated = MagicMock()
        
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.slug_exists.return_value = False
        # domain_exists returns True indicating the domain is taken
        mock_repo.domain_exists.return_value = True
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=tenant_id,
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )
        
        assert exc.value.status_code == 409
        assert "domain" in str(exc.value.detail).lower() or "exists" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_update_tenant_new_slug_success(self):
        """Test update_tenant successfully updates slug when not taken (line 216)."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate, TenantSettingsSchema
        
        tenant_id = uuid4()
        
        data = TenantUpdate(slug="new-unique-slug")
        
        mock_settings = TenantSettingsSchema(
            enable_2fa=True,
            enable_api_keys=True,
            enable_webhooks=False,
            max_users=10,
            max_api_keys_per_user=5,
            max_storage_mb=1024,
            primary_color="#000000",
            logo_url=None,
            password_min_length=8,
            session_timeout_minutes=60,
            require_email_verification=True,
        )
        
        mock_repo = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "old-slug"
        mock_tenant.domain = None
        mock_tenant.name = "Test Tenant"
        mock_tenant.email = None
        mock_tenant.phone = None
        mock_tenant.timezone = "UTC"
        mock_tenant.locale = "en"
        mock_tenant.plan = "free"
        mock_tenant.is_active = True
        mock_tenant.is_verified = True
        mock_tenant.created_at = datetime.now(timezone.utc)
        mock_tenant.updated_at = datetime.now(timezone.utc)
        mock_tenant.settings = mock_settings
        mock_tenant.mark_updated = MagicMock()
        
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.slug_exists.return_value = False  # Slug is available
        mock_repo.update.return_value = mock_tenant
        
        result = await update_tenant(
            tenant_id=tenant_id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )
        
        # Verify slug was updated
        assert mock_tenant.slug == "new-unique-slug"
        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tenant_new_domain_success(self):
        """Test update_tenant successfully updates domain when not taken (line 225)."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate, TenantSettingsSchema
        
        tenant_id = uuid4()
        
        data = TenantUpdate(domain="new-unique-domain.com")
        
        mock_settings = TenantSettingsSchema(
            enable_2fa=True,
            enable_api_keys=True,
            enable_webhooks=False,
            max_users=10,
            max_api_keys_per_user=5,
            max_storage_mb=1024,
            primary_color="#000000",
            logo_url=None,
            password_min_length=8,
            session_timeout_minutes=60,
            require_email_verification=True,
        )
        
        mock_repo = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.slug = "test-slug"
        mock_tenant.domain = "old-domain.com"
        mock_tenant.name = "Test Tenant"
        mock_tenant.email = None
        mock_tenant.phone = None
        mock_tenant.timezone = "UTC"
        mock_tenant.locale = "en"
        mock_tenant.plan = "free"
        mock_tenant.is_active = True
        mock_tenant.is_verified = True
        mock_tenant.created_at = datetime.now(timezone.utc)
        mock_tenant.updated_at = datetime.now(timezone.utc)
        mock_tenant.settings = mock_settings
        mock_tenant.mark_updated = MagicMock()
        
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.domain_exists.return_value = False  # Domain is available
        mock_repo.update.return_value = mock_tenant
        
        result = await update_tenant(
            tenant_id=tenant_id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )
        
        # Verify domain was updated
        assert mock_tenant.domain == "new-unique-domain.com"
        mock_repo.update.assert_called_once()


# =============================================================================
# AUTH.PY EMAIL EXCEPTION PATHS (lines 342-343, 663, 790-791, 853-855, 936)
# =============================================================================

class TestAuthEmailExceptionPaths:
    """Tests to cover email exception handling in auth.py."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock async database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_register_email_exception_silent_failure(self, mock_db_session):
        """
        Test register endpoint handles email exception silently (lines 342-343).
        When email service fails, registration should still succeed.
        """
        from app.api.v1.endpoints.auth import register
        from app.api.v1.schemas.auth import RegisterRequest
        
        request = RegisterRequest(
            email=f"test_{uuid4().hex[:8]}@example.com",
            password="SecurePass123!",
            first_name="Test",
            last_name="User",
        )
        
        # Create mock user entity
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.tenant_id = uuid4()
        mock_user.email = request.email
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.email_verified = False
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.roles = []
        mock_user.avatar_url = None
        mock_user.generate_email_verification_token = MagicMock(return_value="token123")
        
        mock_tenant = MagicMock()
        mock_tenant.id = mock_user.tenant_id
        mock_tenant.slug = "default"
        
        # Mock email service to raise exception
        mock_email_service = MagicMock()
        mock_email_service.send_verification_email = AsyncMock(
            side_effect=Exception("SMTP server down")
        )
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as MockUserRepo, \
             patch("app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository") as MockTenantRepo, \
             patch("app.infrastructure.email.get_email_service", return_value=mock_email_service), \
             patch("app.api.v1.endpoints.auth.create_access_token", return_value="access_token"), \
             patch("app.api.v1.endpoints.auth.create_refresh_token", return_value="refresh_token"), \
             patch("app.api.v1.endpoints.auth.settings") as mock_settings:
            
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_email.return_value = None
            mock_user_repo.create.return_value = mock_user
            MockUserRepo.return_value = mock_user_repo
            
            mock_tenant_repo = AsyncMock()
            mock_tenant_repo.get_default_tenant.return_value = mock_tenant
            MockTenantRepo.return_value = mock_tenant_repo
            
            mock_settings.EMAIL_VERIFICATION_REQUIRED = True
            mock_settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24
            mock_settings.CORS_ORIGINS = ["http://localhost:3000"]
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
            
            # Registration should succeed despite email failure
            result = await register(request=request, session=mock_db_session)
            
            assert result.tokens.access_token == "access_token"
            assert result.tokens.refresh_token == "refresh_token"

    @pytest.mark.asyncio
    async def test_forgot_password_email_exception_silent(self, mock_db_session):
        """
        Test forgot_password handles email exception silently (line 663).
        """
        from app.api.v1.endpoints.auth import forgot_password
        from app.api.v1.schemas.auth import ForgotPasswordRequest
        
        request = ForgotPasswordRequest(email="existing@example.com")
        
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "existing@example.com"
        mock_user.first_name = "Test"
        mock_user.is_active = True
        mock_user.is_deleted = False
        
        # Mock email service to raise exception
        mock_email_service = MagicMock()
        mock_email_service.send_password_reset_email = AsyncMock(
            side_effect=Exception("Email service error")
        )
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as MockUserRepo, \
             patch("app.infrastructure.email.get_email_service", return_value=mock_email_service), \
             patch("app.api.v1.endpoints.auth.settings") as mock_settings, \
             patch("app.api.v1.endpoints.auth._password_reset_tokens", {}), \
             patch("app.api.v1.endpoints.auth.secrets.token_urlsafe", return_value="reset_token"):
            
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_email.return_value = mock_user
            MockUserRepo.return_value = mock_user_repo
            
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            
            # Should succeed despite email failure
            result = await forgot_password(request=request, session=mock_db_session)
            
            assert result.success is True

    @pytest.mark.asyncio
    async def test_forgot_password_cleans_expired_tokens(self, mock_db_session):
        """
        Test forgot_password cleans up expired tokens (line 663 - del statement).
        """
        from app.api.v1.endpoints.auth import forgot_password, _password_reset_tokens
        from app.api.v1.schemas.auth import ForgotPasswordRequest
        
        request = ForgotPasswordRequest(email="existing@example.com")
        
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "existing@example.com"
        mock_user.first_name = "Test"
        mock_user.is_active = True
        mock_user.is_deleted = False
        
        # Add an expired token to be cleaned up
        expired_token = "expired_token_123"
        _password_reset_tokens[expired_token] = {
            "user_id": uuid4(),
            "email": "old@example.com",
            "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
        }
        
        # Mock email service
        mock_email_service = MagicMock()
        mock_email_service.send_password_reset_email = AsyncMock()
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as MockUserRepo, \
             patch("app.infrastructure.email.get_email_service", return_value=mock_email_service), \
             patch("app.api.v1.endpoints.auth.settings") as mock_settings, \
             patch("app.api.v1.endpoints.auth.secrets.token_urlsafe", return_value="new_reset_token"):
            
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_email.return_value = mock_user
            MockUserRepo.return_value = mock_user_repo
            
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            
            try:
                result = await forgot_password(request=request, session=mock_db_session)
                
                assert result.success is True
                # Expired token should be cleaned up
                assert expired_token not in _password_reset_tokens
            finally:
                # Cleanup any tokens we added
                if expired_token in _password_reset_tokens:
                    del _password_reset_tokens[expired_token]
                if "new_reset_token" in _password_reset_tokens:
                    del _password_reset_tokens["new_reset_token"]

    @pytest.mark.asyncio
    async def test_reset_password_email_exception_silent(self, mock_db_session):
        """
        Test reset_password handles email exception silently (lines 790-791).
        """
        from app.api.v1.endpoints.auth import reset_password, _password_reset_tokens
        from app.api.v1.schemas.auth import ResetPasswordRequest
        
        user_id = uuid4()
        token = "valid_reset_token"
        
        # Set up token in the tokens dict
        _password_reset_tokens[token] = {
            "user_id": user_id,
            "email": "test@example.com",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        
        request = ResetPasswordRequest(
            token=token,
            new_password="NewSecurePass123!",
        )
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.password_hash = "old_hash"
        mock_user.set_password = MagicMock()
        
        # Mock email service to raise exception
        mock_email_service = MagicMock()
        mock_email_service.send_password_changed_email = AsyncMock(
            side_effect=Exception("Email service unavailable")
        )
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as MockUserRepo, \
             patch("app.infrastructure.email.get_email_service", return_value=mock_email_service):
            
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_id.return_value = mock_user
            mock_user_repo.update.return_value = mock_user
            MockUserRepo.return_value = mock_user_repo
            
            try:
                result = await reset_password(request=request, session=mock_db_session)
                assert result.success is True
            finally:
                # Clean up token
                if token in _password_reset_tokens:
                    del _password_reset_tokens[token]

    @pytest.mark.asyncio
    async def test_send_verification_email_exception_silent(self, mock_db_session):
        """
        Test send_verification_email handles exception silently (lines 853-855).
        """
        from app.api.v1.endpoints.auth import send_verification_email
        
        user_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.email_verified = False
        mock_user.generate_email_verification_token = MagicMock(return_value="verification_token")
        
        # Mock email service to raise exception
        mock_email_service = MagicMock()
        mock_email_service.send_verification_email = AsyncMock(
            side_effect=Exception("Template rendering failed")
        )
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as MockUserRepo, \
             patch("app.infrastructure.email.get_email_service", return_value=mock_email_service), \
             patch("app.api.v1.endpoints.auth.settings") as mock_settings:
            
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_id.return_value = mock_user
            mock_user_repo.update.return_value = mock_user
            MockUserRepo.return_value = mock_user_repo
            
            mock_settings.CORS_ORIGINS = ["http://localhost:3000"]
            mock_settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24
            
            # Should succeed despite email failure
            result = await send_verification_email(user_id=user_id, session=mock_db_session)
            
            assert result.success is True
            assert "sent" in result.message.lower()

    @pytest.mark.asyncio
    async def test_verify_email_token_expired_raises(self, mock_db_session):
        """
        Test verify_email raises when token is expired (line 936).
        """
        from app.api.v1.endpoints.auth import verify_email
        from fastapi import HTTPException
        
        # Mock the database query to find a user with the token
        mock_user_model = MagicMock()
        mock_user_model.id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_model
        mock_db_session.execute.return_value = mock_result
        
        # Create a mock user entity where verify_email returns False (expired)
        mock_user_entity = MagicMock()
        mock_user_entity.id = mock_user_model.id
        mock_user_entity.verify_email = MagicMock(return_value=False)  # Token expired
        
        with patch("app.api.v1.endpoints.auth.SQLAlchemyUserRepository") as MockUserRepo, \
             patch("app.api.v1.endpoints.auth.settings") as mock_settings:
            
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_id.return_value = mock_user_entity
            MockUserRepo.return_value = mock_user_repo
            
            mock_settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24
            
            with pytest.raises(HTTPException) as exc:
                await verify_email(token="expired_token", session=mock_db_session)
            
            assert exc.value.status_code == 400
            assert "TOKEN_EXPIRED" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_get_verification_status_returns_user_status(self):
        """
        Test get_verification_status returns email verification status (line 936).
        """
        from app.api.v1.endpoints.auth import get_verification_status
        
        # Create mock user
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.email_verified = True
        
        with patch("app.api.v1.endpoints.auth.settings") as mock_settings:
            mock_settings.EMAIL_VERIFICATION_REQUIRED = True
            
            result = await get_verification_status(user=mock_user)
            
            assert result["email"] == "test@example.com"
            assert result["email_verified"] is True
            assert result["verification_required"] is True

    @pytest.mark.asyncio
    async def test_get_verification_status_unverified_user(self):
        """
        Test get_verification_status with unverified user.
        """
        from app.api.v1.endpoints.auth import get_verification_status
        
        # Create mock user
        mock_user = MagicMock()
        mock_user.email = "unverified@example.com"
        mock_user.email_verified = False
        
        with patch("app.api.v1.endpoints.auth.settings") as mock_settings:
            mock_settings.EMAIL_VERIFICATION_REQUIRED = False
            
            result = await get_verification_status(user=mock_user)
            
            assert result["email"] == "unverified@example.com"
            assert result["email_verified"] is False
            assert result["verification_required"] is False


# =============================================================================
# USERS.PY ADDITIONAL COVERAGE - lines 122-123, 131-132, 199-208, 241-242, 343, 369, 388-389, 432
# =============================================================================

class TestUsersEndpointsCoverage:
    """Tests for users.py remaining uncovered lines."""

    @pytest.mark.asyncio
    async def test_update_self_success(self, mock_session):
        """Test update_self success path (lines 199-208)."""
        from app.api.v1.endpoints.users import update_self
        from app.api.v1.schemas.users import UserUpdateSelf
        
        user_id = uuid4()
        request = UserUpdateSelf(first_name="John", last_name="Doe")
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.first_name = "Old"
        mock_user.last_name = "Name"
        mock_user.is_active = True
        mock_user.email_verified = True
        mock_user.is_superuser = False
        mock_user.avatar_url = None
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.mark_updated = MagicMock()
        
        updated_user = MagicMock()
        updated_user.id = user_id
        updated_user.email = "test@example.com"
        updated_user.first_name = "John"
        updated_user.last_name = "Doe"
        updated_user.is_active = True
        updated_user.email_verified = True
        updated_user.is_superuser = False
        updated_user.avatar_url = None
        updated_user.created_at = datetime.now(timezone.utc)
        updated_user.updated_at = datetime.now(timezone.utc)
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.return_value = updated_user
            mock_repo_cls.return_value = mock_repo
            
            result = await update_self(
                request=request,
                current_user_id=user_id,
                session=mock_session,
            )
            
            # Verify first_name and last_name were set
            assert mock_user.first_name == "John"
            assert mock_user.last_name == "Doe"
            mock_user.mark_updated.assert_called_once_with(by_user=user_id)
            mock_repo.update.assert_called_once_with(mock_user)
            assert result.first_name == "John"

    @pytest.mark.asyncio
    async def test_update_self_only_first_name(self, mock_session):
        """Test update_self with only first_name (line 200)."""
        from app.api.v1.endpoints.users import update_self
        from app.api.v1.schemas.users import UserUpdateSelf
        
        user_id = uuid4()
        request = UserUpdateSelf(first_name="NewFirst")  # Only first_name
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.first_name = "Old"
        mock_user.last_name = "Name"
        mock_user.is_active = True
        mock_user.email_verified = True
        mock_user.is_superuser = False
        mock_user.avatar_url = None
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.mark_updated = MagicMock()
        
        updated_user = MagicMock()
        updated_user.id = user_id
        updated_user.email = "test@example.com"
        updated_user.first_name = "NewFirst"
        updated_user.last_name = "Name"
        updated_user.is_active = True
        updated_user.email_verified = True
        updated_user.is_superuser = False
        updated_user.avatar_url = None
        updated_user.created_at = datetime.now(timezone.utc)
        updated_user.updated_at = datetime.now(timezone.utc)
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.return_value = updated_user
            mock_repo_cls.return_value = mock_repo
            
            result = await update_self(
                request=request,
                current_user_id=user_id,
                session=mock_session,
            )
            
            assert mock_user.first_name == "NewFirst"
            assert result.first_name == "NewFirst"

    @pytest.mark.asyncio
    async def test_update_self_only_last_name(self, mock_session):
        """Test update_self with only last_name (line 203)."""
        from app.api.v1.endpoints.users import update_self
        from app.api.v1.schemas.users import UserUpdateSelf
        
        user_id = uuid4()
        request = UserUpdateSelf(last_name="NewLast")  # Only last_name
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.first_name = "First"
        mock_user.last_name = "Old"
        mock_user.is_active = True
        mock_user.email_verified = True
        mock_user.is_superuser = False
        mock_user.avatar_url = None
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.mark_updated = MagicMock()
        
        updated_user = MagicMock()
        updated_user.id = user_id
        updated_user.email = "test@example.com"
        updated_user.first_name = "First"
        updated_user.last_name = "NewLast"
        updated_user.is_active = True
        updated_user.email_verified = True
        updated_user.is_superuser = False
        updated_user.avatar_url = None
        updated_user.created_at = datetime.now(timezone.utc)
        updated_user.updated_at = datetime.now(timezone.utc)
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.return_value = updated_user
            mock_repo_cls.return_value = mock_repo
            
            result = await update_self(
                request=request,
                current_user_id=user_id,
                session=mock_session,
            )
            
            assert mock_user.last_name == "NewLast"
            assert result.last_name == "NewLast"

    @pytest.mark.asyncio
    async def test_upload_avatar_invalid_content_type(self, mock_session):
        """Test upload_avatar with invalid content type (line 343)."""
        from app.api.v1.endpoints.users import upload_avatar
        
        user_id = uuid4()
        
        mock_file = MagicMock()
        mock_file.content_type = "application/pdf"  # Invalid type
        mock_file.filename = "test.pdf"
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await upload_avatar(
                file=mock_file,
                current_user_id=user_id,
                session=mock_session,
            )
        
        assert exc.value.status_code == 400
        assert "INVALID_FILE_TYPE" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_upload_avatar_file_too_large(self, mock_session):
        """Test upload_avatar with file too large (line 356)."""
        from app.api.v1.endpoints.users import upload_avatar
        
        user_id = uuid4()
        
        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "test.jpg"
        # 6MB file (over 5MB limit)
        mock_file.read = AsyncMock(return_value=b"x" * (6 * 1024 * 1024))
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await upload_avatar(
                file=mock_file,
                current_user_id=user_id,
                session=mock_session,
            )
        
        assert exc.value.status_code == 400
        assert "FILE_TOO_LARGE" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_upload_avatar_user_not_found(self, mock_session):
        """Test upload_avatar with user not found (line 369)."""
        from app.api.v1.endpoints.users import upload_avatar
        
        user_id = uuid4()
        
        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "test.jpg"
        mock_file.read = AsyncMock(return_value=b"x" * 1024)  # 1KB file
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None  # User not found
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await upload_avatar(
                    file=mock_file,
                    current_user_id=user_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404
            assert "USER_NOT_FOUND" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_upload_avatar_upload_failed(self, mock_session):
        """Test upload_avatar when upload fails (lines 388-389)."""
        from app.api.v1.endpoints.users import upload_avatar
        
        user_id = uuid4()
        
        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "test.jpg"
        mock_file.read = AsyncMock(return_value=b"x" * 1024)  # 1KB file
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.avatar_url = None
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls, \
             patch("app.api.v1.endpoints.users.get_storage") as mock_get_storage:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            mock_storage = AsyncMock()
            mock_storage.upload.side_effect = Exception("Storage error")
            mock_get_storage.return_value = mock_storage
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await upload_avatar(
                    file=mock_file,
                    current_user_id=user_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 500
            assert "UPLOAD_FAILED" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_delete_avatar_user_not_found(self, mock_session):
        """Test delete_avatar with user not found (line 432)."""
        from app.api.v1.endpoints.users import delete_avatar
        
        user_id = uuid4()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None  # User not found
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await delete_avatar(
                    current_user_id=user_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404
            assert "USER_NOT_FOUND" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_delete_avatar_no_avatar(self, mock_session):
        """Test delete_avatar when user has no avatar (line 432)."""
        from app.api.v1.endpoints.users import delete_avatar
        
        user_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.avatar_url = None  # No avatar
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await delete_avatar(
                    current_user_id=user_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 400
            assert "NO_AVATAR" in str(exc.value.detail)


# =============================================================================
# ROLES.PY LINE 203 - update_role with description
# =============================================================================

class TestRolesDescriptionCoverage:
    """Tests for roles.py update_role description assignment."""

    @pytest.mark.asyncio
    async def test_update_role_description(self, mock_session):
        """Test update_role with description change (line 203)."""
        from app.api.v1.endpoints.roles import update_role
        from app.api.v1.schemas.roles import RoleUpdate
        
        role_id = uuid4()
        superuser_id = uuid4()
        
        mock_role = MagicMock()
        mock_role.id = role_id
        mock_role.name = "TestRole"
        mock_role.description = "Old description"
        mock_role.permissions = []
        mock_role.is_default = False
        mock_role.created_at = datetime.now(timezone.utc)
        mock_role.updated_at = datetime.now(timezone.utc)
        mock_role.mark_updated = MagicMock()
        
        updated_role = MagicMock()
        updated_role.id = role_id
        updated_role.name = "TestRole"
        updated_role.description = "New description"
        updated_role.permissions = []
        updated_role.is_default = False
        updated_role.created_at = datetime.now(timezone.utc)
        updated_role.updated_at = datetime.now(timezone.utc)
        
        request = RoleUpdate(description="New description")
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_role
            mock_repo.update.return_value = updated_role
            mock_repo_cls.return_value = mock_repo
            
            result = await update_role(
                role_id=role_id,
                request=request,
                superuser_id=superuser_id,
                session=mock_session,
            )
            
            # Verify description was set
            assert mock_role.description == "New description"
            mock_role.mark_updated.assert_called_once_with(by_user=superuser_id)
            mock_repo.update.assert_called_once_with(mock_role)
            assert result.description == "New description"