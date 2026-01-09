# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
E2E Test Fixtures.

Provides fixtures for end-to-end testing.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from uuid import uuid4


@pytest.fixture(autouse=True)
def disable_rate_limiting(monkeypatch):
    """Disable rate limiting for all E2E tests."""
    from app import config
    monkeypatch.setattr(config.settings, "RATE_LIMIT_ENABLED", False)


@pytest_asyncio.fixture
async def client():
    """Create async HTTP client for testing."""
    from app.main import app
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict:
    """Create a registered user for testing."""
    email = f"test_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"
    
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
        },
    )
    
    if response.status_code == 201:
        return {
            "email": email,
            "password": password,
            **response.json(),
        }
    
    # If registration endpoint doesn't exist, return mock data
    return {
        "email": email,
        "password": password,
        "id": str(uuid4()),
    }


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, registered_user: dict) -> dict:
    """Get auth headers for a logged-in user."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    # Return empty headers if login fails
    return {}


@pytest_asyncio.fixture
async def user_headers(auth_headers: dict) -> dict:
    """Alias for auth_headers."""
    return auth_headers


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient) -> dict:
    """Get auth headers for an admin user."""
    # Try to login as default admin
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@example.com",
            "password": "AdminPassword123!",
        },
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    return {}


@pytest_asyncio.fixture
async def superuser_headers(client: AsyncClient) -> dict:
    """Get auth headers for a superuser."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "superuser@example.com",
            "password": "SuperuserPassword123!",
        },
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    return {}


@pytest_asyncio.fixture
async def tenant_a_admin_headers(client: AsyncClient) -> dict:
    """Get auth headers for Tenant A admin."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin_a@example.com",
            "password": "TenantAAdmin123!",
        },
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    return {}


@pytest_asyncio.fixture
async def tenant_b_admin_headers(client: AsyncClient) -> dict:
    """Get auth headers for Tenant B admin."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin_b@example.com",
            "password": "TenantBAdmin123!",
        },
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    return {}
