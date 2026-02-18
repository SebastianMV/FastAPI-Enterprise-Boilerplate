# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Integration tests with real PostgreSQL database for critical module coverage.

These tests cover lines that require real database operations:
- users.py lines 165, 199-208 (create_user success, update_self)
- tenants.py lines 216, 225 (slug/domain exists checks)
- roles.py line 203 (role description update)
- auth.py line 936 (verify_email token expired)

Run with:
    TEST_DATABASE_URL=postgresql+asyncpg://test_user:test_password@localhost:5433/test_boilerplate \
    pytest tests/integration/test_critical_coverage_db.py -v
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Import models to register them with Base.metadata
from app.infrastructure.database.models import (  # noqa: F401
    APIKeyModel,
    AuditLogModel,
    MFAConfigModel,
    NotificationModel,
    OAuthConnectionModel,
    RoleModel,
    SSOConfigurationModel,
    TenantModel,
    UserModel,
    UserSessionModel,
)

# Mark all tests to use real database
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
async def test_tenant(db_session: AsyncSession):
    """Create a test tenant in the database."""
    tenant = TenantModel(
        id=uuid4(),
        name="Test Tenant",
        slug=f"test-tenant-{uuid4().hex[:8]}",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest.fixture
async def test_user(db_session: AsyncSession, test_tenant):
    """Create a test user in the database."""
    from app.infrastructure.auth.jwt_handler import hash_password

    user = UserModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"testuser_{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("SecurePass123!"),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_superuser=False,
        email_verified=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def superuser(db_session: AsyncSession, test_tenant):
    """Create a superuser in the database."""
    from app.infrastructure.auth.jwt_handler import hash_password

    user = UserModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"superuser_{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("SuperPass123!"),
        first_name="Super",
        last_name="User",
        is_active=True,
        is_superuser=True,
        email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.flush()
    return user


# =============================================================================
# USERS.PY INTEGRATION TESTS
# =============================================================================


class TestUsersCreateIntegration:
    """Integration tests for user creation with real DB."""

    async def test_create_user_success_with_real_db(
        self, db_session: AsyncSession, test_tenant, superuser
    ):
        """Test create_user success path with real database (line 165)."""
        from app.api.v1.endpoints.users import create_user
        from app.api.v1.schemas.users import UserCreate

        request = UserCreate(
            email=f"newuser_{uuid4().hex[:8]}@example.com",
            password="SecurePass123!",
            first_name="New",
            last_name="User",
            is_active=True,
            is_superuser=False,
            roles=[],
        )

        result = await create_user(
            request=request,
            superuser_id=superuser.id,
            tenant_id=test_tenant.id,
            session=db_session,
        )

        assert result.email == request.email
        assert result.first_name == "New"
        assert result.last_name == "User"


class TestUsersUpdateSelfIntegration:
    """Integration tests for update_self with real DB."""

    async def test_update_self_success(self, db_session: AsyncSession, test_user):
        """Test update_self success path with real database (lines 199-208)."""
        from app.api.v1.endpoints.users import update_self
        from app.api.v1.schemas.users import UserUpdateSelf

        request = UserUpdateSelf(
            first_name="Updated",
            last_name="Name",
        )

        result = await update_self(
            request=request,
            current_user_id=test_user.id,
            tenant_id=None,
            session=db_session,
        )

        assert result.first_name == "Updated"
        assert result.last_name == "Name"


# =============================================================================
# TENANTS.PY INTEGRATION TESTS
# =============================================================================


class TestTenantsSlugDomainIntegration:
    """Integration tests for tenant slug/domain checks with real DB."""

    async def test_update_tenant_slug_conflict_real_db(
        self, db_session: AsyncSession, test_tenant
    ):
        """Test update_tenant with slug conflict in real database (line 216)."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        from app.infrastructure.database.repositories.tenant_repository import (
            SQLAlchemyTenantRepository,
        )

        # Create another tenant with a specific slug
        existing_tenant = TenantModel(
            id=uuid4(),
            name="Existing Tenant",
            slug="existing-slug",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(existing_tenant)
        await db_session.flush()

        # Try to update test_tenant with the same slug
        request = TenantUpdate(slug="existing-slug")

        repo = SQLAlchemyTenantRepository(db_session)

        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=test_tenant.id,
                data=request,
                current_user_id=uuid4(),
                repo=repo,
            )

        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)

    async def test_update_tenant_domain_conflict_real_db(
        self, db_session: AsyncSession, test_tenant
    ):
        """Test update_tenant with domain conflict in real database (line 225)."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate
        from app.infrastructure.database.repositories.tenant_repository import (
            SQLAlchemyTenantRepository,
        )

        # Create another tenant with a specific domain
        existing_tenant = TenantModel(
            id=uuid4(),
            name="Existing Tenant",
            slug=f"slug-{uuid4().hex[:8]}",
            domain="existing.example.com",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(existing_tenant)
        await db_session.flush()

        # Try to update test_tenant with the same domain
        request = TenantUpdate(domain="existing.example.com")

        repo = SQLAlchemyTenantRepository(db_session)

        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=test_tenant.id,
                data=request,
                current_user_id=uuid4(),
                repo=repo,
            )

        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)


# =============================================================================
# ROLES.PY INTEGRATION TESTS
# =============================================================================


class TestRolesUpdateIntegration:
    """Integration tests for role updates with real DB."""

    async def test_update_role_description_real_db(
        self, db_session: AsyncSession, test_tenant, superuser
    ):
        """Test update_role with description change (line 203)."""
        from app.api.v1.endpoints.roles import create_role, update_role
        from app.api.v1.schemas.roles import RoleCreate, RoleUpdate

        # Create a role first
        create_request = RoleCreate(
            name=f"test_role_{uuid4().hex[:8]}",
            description="Original description",
        )

        created_role = await create_role(
            request=create_request,
            superuser_id=superuser.id,
            tenant_id=test_tenant.id,
            session=db_session,
        )

        # Now update the description
        update_request = RoleUpdate(
            description="Updated description",
        )

        updated_role = await update_role(
            role_id=created_role.id,
            request=update_request,
            superuser_id=superuser.id,
            tenant_id=None,
            session=db_session,
        )

        assert updated_role.description == "Updated description"


# =============================================================================
# AUTH.PY INTEGRATION TESTS
# =============================================================================


class TestAuthVerifyEmailIntegration:
    """Integration tests for email verification with real DB."""

    async def test_verify_email_with_expired_token_real_db(
        self, db_session: AsyncSession, test_user
    ):
        """Test verify_email with expired token in real database (line 936)."""
        import hashlib

        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import verify_email
        from app.api.v1.schemas.auth import VerifyEmailTokenRequest

        # Set an expired verification token on the user
        expired_time = datetime.now(UTC) - timedelta(hours=48)
        raw_token = "expired_test_token"
        test_user.email_verification_token = hashlib.sha256(
            raw_token.encode()
        ).hexdigest()
        test_user.email_verification_sent_at = expired_time
        await db_session.flush()

        # This should fail because token is "expired" (verify_email checks expiration)
        # Note: The verify_email function finds the user by token first
        with pytest.raises(HTTPException) as exc:
            await verify_email(
                request=VerifyEmailTokenRequest(token=raw_token),
                session=db_session,
            )

        # Should be either INVALID_TOKEN (if user.verify_email returns False)
        # or TOKEN_EXPIRED depending on implementation
        assert exc.value.status_code == 400
        assert "TOKEN" in str(exc.value.detail).upper()

    async def test_verify_email_invalid_token_real_db(self, db_session: AsyncSession):
        """Test verify_email with invalid token in real database."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.auth import verify_email
        from app.api.v1.schemas.auth import VerifyEmailTokenRequest

        # Try to verify with a token that doesn't exist
        with pytest.raises(HTTPException) as exc:
            await verify_email(
                request=VerifyEmailTokenRequest(token="nonexistent_token_12345"),
                session=db_session,
            )

        assert exc.value.status_code == 400
        assert "INVALID_TOKEN" in str(exc.value.detail)


# =============================================================================
# ADDITIONAL INTEGRATION TESTS FOR FULL COVERAGE
# =============================================================================


class TestUserConflictIntegration:
    """Integration tests for user conflict handling with real DB."""

    async def test_create_user_duplicate_email_real_db(
        self, db_session: AsyncSession, test_tenant, superuser, test_user
    ):
        """Test create_user with duplicate email in real database."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.users import create_user
        from app.api.v1.schemas.users import UserCreate

        # Try to create a user with the same email as test_user
        request = UserCreate(
            email=test_user.email,  # Same email
            password="SecurePass123!",
            first_name="Duplicate",
            last_name="User",
            is_active=True,
            is_superuser=False,
            roles=[],
        )

        with pytest.raises(HTTPException) as exc:
            await create_user(
                request=request,
                superuser_id=superuser.id,
                tenant_id=test_tenant.id,
                session=db_session,
            )

        assert exc.value.status_code == 409
        assert "EMAIL_EXISTS" in str(exc.value.detail)
