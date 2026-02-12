# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Pytest configuration and fixtures.

This module provides reusable fixtures for testing:
- Database sessions with automatic rollback
- Authenticated HTTP clients
- Mock services
- Factory fixtures for creating test data
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.infrastructure.auth.jwt_handler import create_access_token
from app.infrastructure.database.connection import Base
from app.main import app

# ===========================================
# Event Loop
# ===========================================


@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for entire test session.

    Note: Modern pytest-asyncio recommends asyncio_mode="auto" with
    loop_scope config, but this fixture is kept for backward compat
    with the current pytest-asyncio version.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ===========================================
# Database
# ===========================================


@pytest.fixture(scope="session")
async def test_engine():
    """
    Create test database engine.

    Uses PostgreSQL for integration tests (matches production),
    or SQLite for unit tests (fast, isolated).

    Set TEST_DATABASE_URL environment variable to use PostgreSQL:
        TEST_DATABASE_URL=postgresql+asyncpg://test_user:test_password@localhost:5433/test_boilerplate
    """
    # Check for PostgreSQL test database
    test_db_url = os.getenv("TEST_DATABASE_URL")

    if test_db_url:
        # PostgreSQL for integration tests
        print(
            f"\n🗄️  Using PostgreSQL for integration tests: {test_db_url.split('@')[1]}"
        )
        engine = create_async_engine(
            test_db_url,
            poolclass=NullPool,  # Disable pooling for tests
            echo=False,
        )

        # Don't create/drop tables - use existing schema from migrations
        # This avoids issues with foreign keys and RLS policies

        yield engine

        await engine.dispose()
    else:
        # SQLite for unit tests (fast, in-memory)
        print("\n💾 Using SQLite in-memory for unit tests")
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine

        await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession]:
    """
    Create database session with automatic rollback.

    Each test gets a fresh session that rolls back after completion,
    ensuring test isolation without needing to clean up data.

    Note: For PostgreSQL integration tests, data is cleaned before tests
    via the clean_test_data fixture in integration/conftest.py.
    """
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    session = async_session()

    # For PostgreSQL, clean test data first
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if test_db_url:
        # Clean in correct order respecting FKs - ignore errors for missing tables
        cleanup_queries = [
            "DELETE FROM sessions WHERE 1=1",
            "DELETE FROM api_keys WHERE 1=1",
            "DELETE FROM mfa_configs WHERE 1=1",
            "DELETE FROM oauth_connections WHERE 1=1",
            "DELETE FROM audit_logs WHERE 1=1",
            "DELETE FROM users WHERE email LIKE '%test%' OR email LIKE '%example%'",
            "DELETE FROM roles WHERE name NOT IN ('admin', 'user', 'manager')",
            "DELETE FROM tenants WHERE slug LIKE 'test-%'",
        ]
        for query in cleanup_queries:
            try:
                await session.execute(text(query))
            except Exception:
                await session.rollback()
        try:
            await session.commit()
        except Exception:
            await session.rollback()

        # For PostgreSQL: yield session directly (tests will commit)
        yield session
        # Clean up after test
        try:
            await session.rollback()
        except Exception:
            pass
        await session.close()
    else:
        # For SQLite: use transaction with rollback for isolation
        async with session.begin():
            yield session
            await session.rollback()
        await session.close()


# ===========================================
# HTTP Client
# ===========================================


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    """
    Create async HTTP client for testing endpoints.

    Example:
        async def test_health(client):
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def authenticated_client(client, test_user) -> AsyncGenerator[AsyncClient]:
    """
    Create HTTP client with authentication token.

    Example:
        async def test_protected_route(authenticated_client):
            response = await authenticated_client.get("/api/v1/users/me")
            assert response.status_code == 200
    """
    token = create_access_token(
        user_id=test_user["id"],
        tenant_id=test_user.get("tenant_id", uuid4()),
    )
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


@pytest.fixture
async def auth_headers(test_user) -> dict[str, str]:
    """
    Create authentication headers for tests.

    Returns headers dict that can be passed to client requests.

    Example:
        async def test_protected_route(client, auth_headers):
            response = await client.get("/api/v1/users/me", headers=auth_headers)
            assert response.status_code == 200
    """
    token = create_access_token(
        user_id=test_user["id"],
        tenant_id=test_user.get("tenant_id", uuid4()),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def superuser_auth_headers(test_superuser) -> dict[str, str]:
    """
    Create authentication headers for superuser tests.

    Returns headers dict with superuser token.

    Example:
        async def test_admin_route(client, superuser_auth_headers):
            response = await client.get("/api/v1/admin/stats", headers=superuser_auth_headers)
            assert response.status_code == 200
    """
    token = create_access_token(
        user_id=test_superuser["id"],
        tenant_id=test_superuser.get("tenant_id", uuid4()),
    )
    return {"Authorization": f"Bearer {token}"}


# ===========================================
# Test Data Factories
# ===========================================


@pytest.fixture
def user_factory():
    """
    Factory for creating test users.

    Example:
        def test_user_creation(user_factory):
            user = user_factory(email="test@example.com")
            assert user.email.value == "test@example.com"
    """

    def _factory(**kwargs) -> dict[str, Any]:
        defaults = {
            "id": uuid4(),
            "email": f"user-{uuid4().hex[:8]}@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_active": True,
            "is_superuser": False,
        }
        defaults.update(kwargs)
        return defaults

    return _factory


@pytest.fixture
async def test_user(db_session, user_factory) -> dict[str, Any]:
    """
    Create a test user in the database.

    Persists the user via the DB session so that endpoints checking
    ``require_permission`` or ``get_current_user`` find a real record.
    """
    user_data = user_factory()

    # Persist to DB for integration tests
    try:
        from app.infrastructure.database.models.user import UserModel
        from app.infrastructure.database.models.tenant import TenantModel

        # Ensure a tenant exists
        tenant_id = user_data.get("tenant_id", uuid4())
        user_data["tenant_id"] = tenant_id

        from sqlalchemy import select

        existing_tenant = (await db_session.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )).scalars().first()

        if not existing_tenant:
            from datetime import datetime, UTC

            tenant = TenantModel(
                id=tenant_id,
                name="Test Tenant",
                slug=f"test-{uuid4().hex[:8]}",
                is_active=True,
            )
            db_session.add(tenant)
            await db_session.flush()

        from app.infrastructure.auth.jwt_handler import hash_password

        user_model = UserModel(
            id=user_data["id"],
            email=user_data["email"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            password_hash=hash_password("TestPassword123!"),
            is_active=user_data["is_active"],
            is_superuser=user_data["is_superuser"],
            tenant_id=tenant_id,
            roles=[],
        )
        db_session.add(user_model)
        await db_session.flush()
    except Exception:
        # SQLite or missing tables — fall back to dict-only
        pass

    return user_data


@pytest.fixture
async def test_superuser(db_session, user_factory) -> dict[str, Any]:
    """
    Create a test superuser in the database.

    Persists the user via the DB session so that admin endpoints
    find a real record.
    """
    user_data = user_factory(is_superuser=True, email="admin@example.com")

    try:
        from app.infrastructure.database.models.user import UserModel
        from app.infrastructure.database.models.tenant import TenantModel

        tenant_id = user_data.get("tenant_id", uuid4())
        user_data["tenant_id"] = tenant_id

        from sqlalchemy import select

        existing_tenant = (await db_session.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )).scalars().first()

        if not existing_tenant:
            tenant = TenantModel(
                id=tenant_id,
                name="Test Tenant",
                slug=f"test-{uuid4().hex[:8]}",
                is_active=True,
            )
            db_session.add(tenant)
            await db_session.flush()

        from app.infrastructure.auth.jwt_handler import hash_password

        user_model = UserModel(
            id=user_data["id"],
            email=user_data["email"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            password_hash=hash_password("TestPassword123!"),
            is_active=True,
            is_superuser=True,
            tenant_id=tenant_id,
            roles=[],
        )
        db_session.add(user_model)
        await db_session.flush()
    except Exception:
        pass

    return user_data


# ===========================================
# Mock Services
# ===========================================


@pytest.fixture
def mock_email_service(monkeypatch):
    """
    Mock email service for tests.

    Prevents actual emails from being sent during tests.
    The email service is already mocked via EMAIL_BACKEND=console in test settings.
    """
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    # Email service is configured via EMAIL_BACKEND env var
    # In tests, use EMAIL_BACKEND=console which logs instead of sending
    return mock


@pytest.fixture
def mock_redis(monkeypatch):
    """
    Mock Redis for tests.

    Uses a simple dict-based implementation for caching tests.
    """

    class MockRedis:
        def __init__(self):
            self._store: dict[str, Any] = {}

        async def get(self, key: str) -> Any:
            return self._store.get(key)

        async def set(self, key: str, value: Any, ex: int = None) -> None:
            self._store[key] = value

        async def delete(self, key: str) -> None:
            self._store.pop(key, None)

        async def exists(self, key: str) -> bool:
            return key in self._store

    return MockRedis()


@pytest.fixture(autouse=True)
def mock_cache_global(monkeypatch):
    """
    Automatically mock get_cache() for all tests to avoid Redis dependency.

    This fixture runs for every test automatically (autouse=True).
    """
    from unittest.mock import MagicMock

    class MockCache:
        def __init__(self):
            self._store = {}

        async def get(self, key: str):
            return self._store.get(key)

        async def set(self, key: str, value: str, ex: int = None, ttl: int = None):
            self._store[key] = value
            return True

        async def delete(self, key: str):
            self._store.pop(key, None)
            return True

        async def exists(self, key: str) -> bool:
            return key in self._store

        async def get_and_delete(self, key: str):
            return self._store.pop(key, None)

        def get_redis_client(self):
            return None

    # Create a mock that returns the same MockCache instance
    mock_instance = MockCache()
    mock_factory = MagicMock(return_value=mock_instance)

    # Patch get_cache at module level
    monkeypatch.setattr("app.infrastructure.cache.get_cache", mock_factory)

    return mock_instance
