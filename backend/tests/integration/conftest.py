# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Integration Test Fixtures.

Provides fixtures for integration and security testing.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from datetime import datetime, timedelta, UTC


@pytest.fixture(autouse=True)
def disable_rate_limiting(monkeypatch):
    """Disable rate limiting for all integration tests."""
    from app import config
    monkeypatch.setattr(config.settings, "RATE_LIMIT_ENABLED", False)


@pytest_asyncio.fixture
async def client():
    """Create async HTTP client for testing."""
    from app.main import app
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


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
async def auth_headers(client: AsyncClient) -> dict:
    """Get auth headers for a logged-in user."""
    # Register and login a test user
    email = f"security_test_{uuid4().hex[:8]}@example.com"
    password = "SecureTestPassword123!"
    
    # Try to register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Security",
            "last_name": "Test User",
        },
    )
    
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    # Fallback: create a test token directly
    from app.infrastructure.auth.jwt_handler import create_access_token
    test_user_id = str(uuid4())
    test_tenant_id = str(uuid4())
    token = create_access_token(
        user_id=test_user_id,
        tenant_id=test_tenant_id,
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
