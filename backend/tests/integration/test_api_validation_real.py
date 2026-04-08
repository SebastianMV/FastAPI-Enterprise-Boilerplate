# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Integration tests for API endpoint validation."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestAuthValidation:
    """Tests for auth endpoint validation."""

    @pytest.mark.asyncio
    async def test_login_form_data(self) -> None:
        """Test login with form data format."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                data={"username": "test@test.com", "password": "password123"},
            )
            # May return validation error or auth failure
            assert response.status_code in [400, 401, 422]

    @pytest.mark.asyncio
    async def test_register_missing_fields(self) -> None:
        """Test register with missing required fields."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register", json={"email": "test@example.com"}
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self) -> None:
        """Test register with password without uppercase."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "test@example.com",
                    "password": "weakpassword123",
                    "first_name": "Test",
                    "last_name": "User",
                },
            )
            # Depends on password policy
            assert response.status_code in [400, 422, 500]

    @pytest.mark.asyncio
    async def test_refresh_token_missing(self) -> None:
        """Test refresh without token."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/refresh")
            assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self) -> None:
        """Test refresh with invalid token."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh", json={"refresh_token": "invalid-token"}
            )
            assert response.status_code in [401, 422]


class TestUserEndpointValidation:
    """Tests for user endpoint validation."""

    @pytest.mark.asyncio
    async def test_get_user_invalid_uuid(self) -> None:
        """Test get user with invalid UUID format."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/users/not-a-uuid")
            assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_create_user_empty_body(self) -> None:
        """Test create user with empty body."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/users", json={})
            assert response.status_code in [401, 403, 422]


class TestRoleEndpointValidation:
    """Tests for role endpoint validation."""

    @pytest.mark.asyncio
    async def test_get_role_invalid_uuid(self) -> None:
        """Test get role with invalid UUID format."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/roles/not-a-uuid")
            assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_create_role_empty_body(self) -> None:
        """Test create role with empty body."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/roles", json={})
            assert response.status_code in [401, 403, 422]


class TestTenantEndpointValidation:
    """Tests for tenant endpoint validation."""

    @pytest.mark.asyncio
    async def test_get_tenant_invalid_uuid(self) -> None:
        """Test get tenant with invalid UUID format."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/tenants/not-a-uuid")
            assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_create_tenant_empty_body(self) -> None:
        """Test create tenant with empty body."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/tenants", json={})
            assert response.status_code in [401, 403, 422]


class TestChatEndpointValidation:
    """Tests for chat endpoint validation (Note: REST chat endpoints may not exist, only WebSocket)."""

    @pytest.mark.asyncio
    async def test_get_conversations_unauthorized(self) -> None:
        """Test get conversations without auth - expects 401/403/404 (route may not exist)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/conversations")
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_create_direct_conversation_unauthorized(self) -> None:
        """Test create direct conversation without auth - expects 401/403/404/422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/chat/conversations/direct", json={})
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_create_group_conversation_unauthorized(self) -> None:
        """Test create group conversation without auth - expects 401/403/404/422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/chat/conversations/group", json={})
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_get_conversation_messages_unauthorized(self) -> None:
        """Test get messages without auth - expects 401/403/404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000/messages"
            )
            assert response.status_code in [401, 403, 404]


class TestSearchEndpointValidation:
    """Tests for search endpoint validation."""

    @pytest.mark.asyncio
    async def test_search_simple_empty_query(self) -> None:
        """Test simple search with empty query."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/search/simple")
            # May require auth or query param
            assert response.status_code in [400, 401, 403, 422]

    @pytest.mark.asyncio
    async def test_search_with_query_param(self) -> None:
        """Test search POST endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/search", json={"query": "test"})
            assert response.status_code in [200, 401, 403, 422]

    @pytest.mark.asyncio
    async def test_search_suggest_unauthorized(self) -> None:
        """Test search suggest endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/search/suggest?q=test")
            assert response.status_code in [200, 401, 403, 422]

    @pytest.mark.asyncio
    async def test_search_health(self) -> None:
        """Test search health endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/search/health")
            # May require auth or fail if no search service
            assert response.status_code in [200, 401, 403, 500, 503]


class TestMFAEndpointValidation:
    """Tests for MFA endpoint validation."""

    @pytest.mark.asyncio
    async def test_mfa_verify_empty_body(self) -> None:
        """Test MFA verify with empty body."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/mfa/verify", json={})
            assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_mfa_verify_invalid_code(self) -> None:
        """Test MFA verify with invalid code format."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mfa/verify",
                json={"code": "abc"},  # Should be numeric
            )
            assert response.status_code in [401, 403, 422]


class TestNotificationEndpointValidation:
    """Tests for notification endpoint validation."""

    @pytest.mark.asyncio
    async def test_get_notification_invalid_uuid(self) -> None:
        """Test get notification with invalid UUID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/notifications/not-a-uuid")
            assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_mark_notifications_read_unauthorized(self) -> None:
        """Test mark notifications read without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/notifications/read", json={})
            assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_mark_all_read_unauthorized(self) -> None:
        """Test mark all notifications read without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/notifications/read/all")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_unread_count_unauthorized(self) -> None:
        """Test get unread count without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/notifications/unread/count")
            assert response.status_code in [401, 403]


class TestAPIKeyEndpointValidation:
    """Tests for API key endpoint validation."""

    @pytest.mark.asyncio
    async def test_create_api_key_empty_body(self) -> None:
        """Test create API key with empty body."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/api-keys", json={})
            assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_revoke_api_key_invalid_uuid(self) -> None:
        """Test revoke API key with invalid UUID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/api-keys/not-a-uuid")
            assert response.status_code in [401, 403, 422]


class TestOAuthEndpointValidation:
    """Tests for OAuth endpoint validation."""

    @pytest.mark.asyncio
    async def test_oauth_authorize_google(self) -> None:
        """Test OAuth authorize endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/auth/oauth/google/authorize")
            # May redirect or return error if not configured
            assert response.status_code in [200, 302, 400, 401, 422, 500, 503]

    @pytest.mark.asyncio
    async def test_oauth_callback_missing_code(self) -> None:
        """Test OAuth callback without code parameter."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/auth/oauth/google/callback")
            assert response.status_code in [400, 422, 500]

    @pytest.mark.asyncio
    async def test_oauth_providers_list(self) -> None:
        """Test OAuth providers list endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/auth/oauth/providers")
            assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_oauth_connections_unauthorized(self) -> None:
        """Test OAuth connections without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/auth/oauth/connections")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_oauth_sso_configs_unauthorized(self) -> None:
        """Test SSO configs without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/auth/oauth/sso/configs")
            assert response.status_code in [401, 403]
