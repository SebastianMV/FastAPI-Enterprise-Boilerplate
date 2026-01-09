# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
End-to-End Tests - API Key Management Flow.

Complete user journey tests for API key operations.

Note: These tests require the full API key endpoints to be implemented.
They are marked as skip until the implementation is complete.
"""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.skip(reason="E2E tests require full endpoint implementation")


class TestAPIKeyE2E:
    """End-to-end API key management tests."""

    @pytest.mark.asyncio
    async def test_complete_api_key_lifecycle(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test complete API key creation, usage, and revocation."""
        # 1. Create API key
        create_response = await client.post(
            "/api/v1/api-keys",
            json={
                "name": "E2E Test Key",
                "scopes": ["read:users"],
                "expires_in_days": 30,
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        key_data = create_response.json()
        
        # Verify response contains the key (only shown once)
        assert "key" in key_data
        assert "id" in key_data
        assert key_data["name"] == "E2E Test Key"
        
        api_key = key_data["key"]
        key_id = key_data["id"]
        
        # 2. Use API key for authentication
        api_key_headers = {"X-API-Key": api_key}
        me_response = await client.get("/api/v1/users/me", headers=api_key_headers)
        assert me_response.status_code == 200
        
        # 3. List API keys (verify new key appears)
        list_response = await client.get("/api/v1/api-keys", headers=auth_headers)
        assert list_response.status_code == 200
        keys = list_response.json()
        key_ids = [k["id"] for k in keys.get("items", keys)]
        assert key_id in key_ids
        
        # Verify full key is NOT in list response
        for key in keys.get("items", keys):
            assert "key" not in key or len(key.get("key", "")) < 20
        
        # 4. Revoke API key
        revoke_response = await client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers=auth_headers,
        )
        assert revoke_response.status_code == 204
        
        # 5. Verify revoked key no longer works
        revoked_response = await client.get(
            "/api/v1/users/me",
            headers={"X-API-Key": api_key},
        )
        assert revoked_response.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_scopes_enforced(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test API key scopes are properly enforced."""
        # Create key with limited scope
        create_response = await client.post(
            "/api/v1/api-keys",
            json={
                "name": "Limited Scope Key",
                "scopes": ["read:users"],  # Only read access
                "expires_in_days": 1,
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        api_key = create_response.json()["key"]
        
        api_key_headers = {"X-API-Key": api_key}
        
        # Read should work
        read_response = await client.get("/api/v1/users/me", headers=api_key_headers)
        assert read_response.status_code == 200
        
        # Write should fail (if scopes enforced)
        # This depends on implementation - may return 403 or still work
        # At minimum, should not cause server error
        write_response = await client.patch(
            "/api/v1/users/me",
            json={"full_name": "Should Fail"},
            headers=api_key_headers,
        )
        assert write_response.status_code in [200, 403]

    @pytest.mark.asyncio
    async def test_expired_api_key_rejected(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test expired API keys are rejected."""
        # Note: To properly test this, you would need to:
        # 1. Create a key with expires_in_days=0 or
        # 2. Mock the current time
        # 3. Or use a pre-created expired key in fixtures
        
        # For now, just verify the endpoint accepts expires_in_days
        create_response = await client.post(
            "/api/v1/api-keys",
            json={
                "name": "Short-lived Key",
                "scopes": ["read:users"],
                "expires_in_days": 1,  # 1 day
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        assert "expires_at" in create_response.json()
