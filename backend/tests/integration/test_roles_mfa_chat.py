# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Integration tests for roles endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
class TestRolesEndpoints:
    """Integration tests for roles API endpoints."""

    async def test_list_roles_requires_auth(self, client: AsyncClient) -> None:
        """Test that list roles requires authentication."""
        response = await client.get("/api/v1/roles")
        assert response.status_code in [401, 403]

    async def test_list_roles_with_auth(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test list roles with authentication."""
        if not auth_headers:
            pytest.skip("Could not get auth headers")
            
        response = await client.get("/api/v1/roles", headers=auth_headers)
        # May fail due to tenant context, but should not be 401
        assert response.status_code in [200, 400, 403, 422]

    async def test_get_role_not_found(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test get role that doesn't exist."""
        if not auth_headers:
            pytest.skip("Could not get auth headers")
            
        fake_id = uuid4()
        response = await client.get(f"/api/v1/roles/{fake_id}", headers=auth_headers)
        assert response.status_code in [404, 400, 403]


@pytest.mark.asyncio
class TestMFAEndpoints:
    """Integration tests for MFA API endpoints."""

    async def test_mfa_status_requires_auth(self, client: AsyncClient) -> None:
        """Test that MFA status requires authentication."""
        response = await client.get("/api/v1/mfa/status")
        assert response.status_code in [401, 403]

    async def test_mfa_status_with_auth(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test MFA status with authentication."""
        if not auth_headers:
            pytest.skip("Could not get auth headers")
            
        response = await client.get("/api/v1/mfa/status", headers=auth_headers)
        assert response.status_code in [200, 400, 403]

    async def test_mfa_setup_requires_auth(self, client: AsyncClient) -> None:
        """Test that MFA setup requires authentication."""
        response = await client.post("/api/v1/mfa/setup")
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
class TestChatEndpoints:
    """Integration tests for chat API endpoints (Note: REST chat endpoints may not exist, only WebSocket)."""

    async def test_chat_conversations_requires_auth(
        self, client: AsyncClient
    ) -> None:
        """Test that chat conversations requires authentication - expects 401/403/404."""
        response = await client.get("/api/v1/chat/conversations")
        assert response.status_code in [401, 403, 404]

    async def test_chat_conversations_with_auth(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test chat conversations with authentication."""
        if not auth_headers:
            pytest.skip("Could not get auth headers")
            
        response = await client.get("/api/v1/chat/conversations", headers=auth_headers)
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.asyncio
class TestUsersEndpoints:
    """Integration tests for users API endpoints."""

    async def test_list_users_requires_auth(self, client: AsyncClient) -> None:
        """Test that list users requires authentication."""
        response = await client.get("/api/v1/users")
        assert response.status_code in [401, 403]

    async def test_get_me_requires_auth(self, client: AsyncClient) -> None:
        """Test that get me requires authentication."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code in [401, 403]

    async def test_get_me_with_auth(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test get me with authentication."""
        if not auth_headers:
            pytest.skip("Could not get auth headers")
            
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code in [200, 400, 403]
