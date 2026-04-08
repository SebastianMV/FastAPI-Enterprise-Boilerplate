# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Integration Test Fixtures.

Provides fixtures for integration and security testing.
"""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


def _is_postgresql_test() -> bool:
    """Check if running with PostgreSQL test database."""
    return bool(os.getenv("TEST_DATABASE_URL"))


@pytest.fixture(autouse=True)
def disable_rate_limiting(monkeypatch):
    """Disable rate limiting for all integration tests."""
    from app import config

    monkeypatch.setattr(config.settings, "RATE_LIMIT_ENABLED", False)


@pytest_asyncio.fixture(scope="function")
async def clean_test_data():
    """
    Clean up test data before each integration test.

    Removes data created by previous tests to ensure isolation.
    Only runs when using PostgreSQL test database.
    """
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        yield
        return

    from sqlalchemy import text

    engine = create_async_engine(test_db_url, poolclass=NullPool, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Clean test data in correct order (respect foreign keys)
        # Only delete test data, not seed data
        # Ignore errors for tables that might not exist
        cleanup_queries = [
            "DELETE FROM sessions WHERE 1=1",
            "DELETE FROM api_keys WHERE 1=1",
            "DELETE FROM mfa_secrets WHERE 1=1",
            "DELETE FROM oauth_connections WHERE 1=1",
            "DELETE FROM audit_logs WHERE 1=1",
            "DELETE FROM users WHERE email LIKE '%test%' OR email LIKE '%example%'",
            "DELETE FROM roles WHERE name NOT IN ('admin', 'user', 'manager')",
            "DELETE FROM tenants WHERE slug LIKE 'test-%' OR slug LIKE 'admin-tenant-%'",
        ]

        for query in cleanup_queries:
            try:
                await session.execute(text(query))
            except Exception:
                # Table might not exist or FK constraint - ignore
                await session.rollback()

        try:
            await session.commit()
        except Exception:
            await session.rollback()

    await engine.dispose()
    yield


@pytest_asyncio.fixture(scope="function")
async def integration_db_session(clean_test_data):
    """Create a database session for integration tests with real user creation."""
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        yield None
        return

    engine = create_async_engine(test_db_url, poolclass=NullPool, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    session = async_session()
    try:
        # Connect the session to the database
        conn = await session.connection()
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(integration_db_session):
    """
    Create async HTTP client for testing with shared DB session.

    IMPORTANT: This fixture overrides the database session dependency
    to share the same session used by fixtures. This prevents deadlocks
    when fixtures create data in transactions that endpoints try to access.
    """
    from app.infrastructure.database.connection import get_db_session
    from app.main import app

    # Override get_db_session to use the same session from fixtures
    if integration_db_session:

        async def override_get_db_session():
            yield integration_db_session

        app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def expired_token() -> str:
    """Generate an expired JWT token."""
    import jwt

    # This should match your JWT settings
    payload = {
        "sub": str(uuid4()),
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "type": "access",
    }

    # Use a test secret - in real tests, use your actual secret
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


@pytest_asyncio.fixture
async def real_test_user(integration_db_session):
    """
    Create a real user in the database for integration tests.

    Returns tuple of (user, tenant) that exists in DB.
    """
    if not integration_db_session:
        return None

    from app.domain.entities.tenant import Tenant
    from app.domain.entities.user import User
    from app.domain.value_objects.email import Email
    from app.infrastructure.auth.jwt_handler import hash_password
    from app.infrastructure.database.repositories.tenant_repository import (
        SQLAlchemyTenantRepository,
    )
    from app.infrastructure.database.repositories.user_repository import (
        SQLAlchemyUserRepository,
    )

    unique_id = str(uuid4())[:8]
    tenant_id = uuid4()
    user_id = uuid4()

    # Create tenant
    tenant_repo = SQLAlchemyTenantRepository(integration_db_session)
    tenant = Tenant(
        id=tenant_id,
        name=f"Test Tenant {unique_id}",
        slug=f"test-tenant-{unique_id}",
        plan="free",
        is_active=True,
    )
    await tenant_repo.create(tenant)
    await integration_db_session.flush()

    # Create user (roles is a list of UUIDs, not strings - leave empty for test)
    user_repo = SQLAlchemyUserRepository(integration_db_session)
    user = User(
        id=user_id,
        email=Email(f"testuser-{unique_id}@example.com"),
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name="User",
        tenant_id=tenant_id,
        is_active=True,
        email_verified=True,
        roles=[],  # Empty list - roles are UUID references, not strings
    )
    await user_repo.create(user)
    await integration_db_session.flush()

    return {"user": user, "tenant": tenant, "user_id": user_id, "tenant_id": tenant_id}


@pytest_asyncio.fixture
async def auth_headers(real_test_user) -> dict:
    """
    Get auth headers for a logged-in user.

    Creates a real user in the database when running integration tests
    to ensure endpoints that verify user existence work correctly.
    """
    from app.infrastructure.auth.jwt_handler import create_access_token

    if real_test_user:
        # Use real user from database
        token = create_access_token(
            user_id=real_test_user["user_id"],
            tenant_id=real_test_user["tenant_id"],
            extra_claims={"roles": ["user"]},
        )
    else:
        # Fallback for non-PostgreSQL tests
        token = create_access_token(
            user_id=uuid4(),
            tenant_id=uuid4(),
            extra_claims={"roles": ["user"]},
        )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def real_admin_user(integration_db_session):
    """
    Create a real admin user in the database for integration tests.
    """
    if not integration_db_session:
        return None

    from app.domain.entities.tenant import Tenant
    from app.domain.entities.user import User
    from app.domain.value_objects.email import Email
    from app.infrastructure.auth.jwt_handler import hash_password
    from app.infrastructure.database.repositories.tenant_repository import (
        SQLAlchemyTenantRepository,
    )
    from app.infrastructure.database.repositories.user_repository import (
        SQLAlchemyUserRepository,
    )

    unique_id = str(uuid4())[:8]
    tenant_id = uuid4()
    user_id = uuid4()

    # Create tenant
    tenant_repo = SQLAlchemyTenantRepository(integration_db_session)
    tenant = Tenant(
        id=tenant_id,
        name=f"Admin Tenant {unique_id}",
        slug=f"admin-tenant-{unique_id}",
        plan="enterprise",
        is_active=True,
    )
    await tenant_repo.create(tenant)
    await integration_db_session.flush()

    # Create admin user (roles is list of UUID, use is_superuser for admin permissions)
    user_repo = SQLAlchemyUserRepository(integration_db_session)
    user = User(
        id=user_id,
        email=Email(f"admin-{unique_id}@example.com"),
        password_hash=hash_password("AdminPassword123!"),
        first_name="Admin",
        last_name="User",
        tenant_id=tenant_id,
        is_active=True,
        is_superuser=True,
        email_verified=True,
        roles=[],  # Empty list - roles are UUID references. Use is_superuser for admin
    )
    await user_repo.create(user)
    await integration_db_session.flush()

    return {"user": user, "tenant": tenant, "user_id": user_id, "tenant_id": tenant_id}


@pytest_asyncio.fixture
async def admin_headers(real_admin_user) -> dict:
    """
    Get auth headers for an admin user.

    Creates a real admin user in the database when running integration tests.
    """
    from app.infrastructure.auth.jwt_handler import create_access_token

    if real_admin_user:
        # Use real admin from database
        token = create_access_token(
            user_id=real_admin_user["user_id"],
            tenant_id=real_admin_user["tenant_id"],
            extra_claims={"roles": ["admin", "user"], "is_superuser": True},
        )
    else:
        # Fallback for non-PostgreSQL tests
        token = create_access_token(
            user_id=uuid4(),
            tenant_id=uuid4(),
            extra_claims={"roles": ["admin", "user"], "is_superuser": True},
        )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_token() -> str:
    """Get a valid user token (non-admin)."""
    import jwt

    payload = {
        "sub": str(uuid4()),
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        "type": "access",
        "roles": ["user"],
    }

    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


@pytest.fixture
def other_user_id() -> str:
    """Get a random user ID for cross-access testing."""
    return str(uuid4())


@pytest.fixture
def tenant_a_token() -> str:
    """Get a token for Tenant A."""
    import jwt

    payload = {
        "sub": str(uuid4()),
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        "type": "access",
        "tenant_id": str(uuid4()),  # Tenant A
    }

    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


@pytest.fixture
def tenant_b_user_id() -> str:
    """Get a user ID from Tenant B."""
    return str(uuid4())


@pytest_asyncio.fixture
async def valid_api_key(client: AsyncClient, auth_headers: dict) -> str:
    """Create and return a valid API key."""
    if not auth_headers:
        pytest.skip("Auth not available")

    response = await client.post(
        "/api/v1/api-keys",
        json={
            "name": "Test API Key",
            "scopes": ["read:users", "write:users"],
            "expires_in_days": 30,
        },
        headers=auth_headers,
    )

    if response.status_code == 201:
        return response.json()["key"]

    pytest.skip("API key creation not available")


@pytest.fixture
def revoked_api_key() -> str:
    """Return a revoked/invalid API key."""
    return "blt_revoked_key_12345678901234567890"


# ===========================================
# Superuser Fixtures for Integration Tests
# ===========================================


@pytest_asyncio.fixture
async def test_superuser(integration_db_session):
    """
    Create a real superuser in the database for integration tests.

    Returns dict with user info that can be used in tests.
    """
    if not integration_db_session:
        # Fallback for non-PostgreSQL tests
        return {
            "id": uuid4(),
            "email": "superuser@example.com",
            "tenant_id": uuid4(),
            "is_superuser": True,
        }

    from app.domain.entities.tenant import Tenant
    from app.domain.entities.user import User
    from app.domain.value_objects.email import Email
    from app.infrastructure.auth.jwt_handler import hash_password
    from app.infrastructure.database.repositories.tenant_repository import (
        SQLAlchemyTenantRepository,
    )
    from app.infrastructure.database.repositories.user_repository import (
        SQLAlchemyUserRepository,
    )

    unique_id = str(uuid4())[:8]
    tenant_id = uuid4()
    user_id = uuid4()

    # Create tenant
    tenant_repo = SQLAlchemyTenantRepository(integration_db_session)
    tenant = Tenant(
        id=tenant_id,
        name=f"Superuser Tenant {unique_id}",
        slug=f"super-tenant-{unique_id}",
        plan="enterprise",
        is_active=True,
    )
    await tenant_repo.create(tenant)

    # Create superuser
    user_repo = SQLAlchemyUserRepository(integration_db_session)
    user = User(
        id=user_id,
        email=Email(f"superuser-{unique_id}@example.com"),
        password_hash=hash_password("SuperSecure123!"),
        first_name="Super",
        last_name="User",
        tenant_id=tenant_id,
        is_active=True,
        is_superuser=True,
        email_verified=True,
        roles=[],
    )
    await user_repo.create(user)

    # Commit so the user is visible to endpoints
    await integration_db_session.commit()

    return {
        "id": user_id,
        "email": f"superuser-{unique_id}@example.com",
        "tenant_id": tenant_id,
        "is_superuser": True,
        "user": user,
        "tenant": tenant,
    }


@pytest_asyncio.fixture
async def superuser_auth_headers(test_superuser) -> dict:
    """
    Get auth headers for a superuser.

    Creates a real superuser in the database when running integration tests.
    """
    from app.infrastructure.auth.jwt_handler import create_access_token

    token = create_access_token(
        user_id=test_superuser["id"],
        tenant_id=test_superuser["tenant_id"],
        extra_claims={"roles": ["admin", "user"], "is_superuser": True},
    )
    return {"Authorization": f"Bearer {token}"}
