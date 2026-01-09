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
from collections.abc import AsyncGenerator, Generator
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.infrastructure.database.connection import Base
from app.infrastructure.auth.jwt_handler import create_access_token


# ===========================================
# Event Loop
# ===========================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create event loop for entire test session.
    
    This ensures async fixtures work correctly with pytest-asyncio.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===========================================
# Database
# ===========================================

@pytest.fixture(scope="session")
async def test_engine():
    """
    Create test database engine.
    
    Uses SQLite in-memory for fast tests, or PostgreSQL for integration tests.
    """
    # Use SQLite for unit tests (fast)
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
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session with automatic rollback.
    
    Each test gets a fresh session that rolls back after completion,
    ensuring test isolation without needing to clean up data.
    """
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ===========================================
# HTTP Client
# ===========================================

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
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
async def authenticated_client(client, test_user) -> AsyncGenerator[AsyncClient, None]:
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
    
    Returns the user data for use in tests.
    Note: For integration tests that need actual DB persistence,
    use the user_factory and save via SQLAlchemyUserRepository.
    This fixture returns a dict for unit test mocking purposes.
    """
    user_data = user_factory()
    return user_data


@pytest.fixture
async def test_superuser(db_session, user_factory) -> dict[str, Any]:
    """
    Create a test superuser in the database.
    
    Note: For integration tests that need actual DB persistence,
    use the user_factory and save via SQLAlchemyUserRepository.
    This fixture returns a dict for unit test mocking purposes.
    """
    user_data = user_factory(is_superuser=True, email="admin@example.com")
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
