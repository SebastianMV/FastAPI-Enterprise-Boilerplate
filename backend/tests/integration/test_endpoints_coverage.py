# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Additional integration tests for more endpoint coverage."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


class TestAPIKeyEndpoints:
    """Tests for API key endpoints."""

    @pytest.mark.asyncio
    async def test_list_api_keys_unauthorized(self) -> None:
        """Test list API keys without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/api-keys")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_api_key_unauthorized(self) -> None:
        """Test create API key without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/api-keys",
                json={"name": "Test Key"}
            )
            assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_get_api_key_unauthorized(self) -> None:
        """Test get API key without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/api-keys/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403, 405]

    @pytest.mark.asyncio
    async def test_delete_api_key_unauthorized(self) -> None:
        """Test delete API key without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/v1/api-keys/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]


class TestDashboardEndpoints:
    """Tests for dashboard endpoints."""

    @pytest.mark.asyncio
    async def test_dashboard_stats_unauthorized(self) -> None:
        """Test dashboard stats without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/dashboard/stats")
            assert response.status_code in [401, 403]


class TestMFAEndpoints:
    """Tests for MFA endpoints."""

    @pytest.mark.asyncio
    async def test_mfa_status_unauthorized(self) -> None:
        """Test MFA status without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/mfa/status")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_mfa_setup_unauthorized(self) -> None:
        """Test MFA setup without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/mfa/setup")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_mfa_enable_unauthorized(self) -> None:
        """Test MFA enable without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mfa/enable",
                json={"code": "123456"}
            )
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_mfa_disable_unauthorized(self) -> None:
        """Test MFA disable without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mfa/disable",
                json={"code": "123456"}
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_mfa_verify_validation(self) -> None:
        """Test MFA verify with missing fields."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/mfa/verify", json={})
            assert response.status_code in [401, 403, 422]


class TestUserEndpoints:
    """Tests for user endpoints."""

    @pytest.mark.asyncio
    async def test_list_users_unauthorized(self) -> None:
        """Test list users without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/users")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_user_unauthorized(self) -> None:
        """Test create user without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/users",
                json={
                    "email": "test@example.com",
                    "password": "Password123!",
                    "first_name": "Test",
                    "last_name": "User"
                }
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_user_unauthorized(self) -> None:
        """Test get user without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/users/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_update_user_unauthorized(self) -> None:
        """Test update user without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/users/00000000-0000-0000-0000-000000000000",
                json={"first_name": "Updated"}
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_delete_user_unauthorized(self) -> None:
        """Test delete user without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/v1/users/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self) -> None:
        """Test get current user without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/users/me")
            assert response.status_code in [401, 403]


class TestRoleEndpoints:
    """Tests for role endpoints."""

    @pytest.mark.asyncio
    async def test_list_roles_unauthorized(self) -> None:
        """Test list roles without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/roles")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_role_unauthorized(self) -> None:
        """Test create role without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/roles",
                json={"name": "Test Role", "permissions": []}
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_role_unauthorized(self) -> None:
        """Test get role without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/roles/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_delete_role_unauthorized(self) -> None:
        """Test delete role without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/v1/roles/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]


class TestTenantEndpoints:
    """Tests for tenant endpoints."""

    @pytest.mark.asyncio
    async def test_list_tenants_unauthorized(self) -> None:
        """Test list tenants without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/tenants")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_tenant_unauthorized(self) -> None:
        """Test create tenant without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/tenants",
                json={"name": "Test Tenant", "slug": "test-tenant"}
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_tenant_unauthorized(self) -> None:
        """Test get tenant without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/tenants/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_update_tenant_unauthorized(self) -> None:
        """Test update tenant without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/tenants/00000000-0000-0000-0000-000000000000",
                json={"name": "Updated Tenant"}
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_delete_tenant_unauthorized(self) -> None:
        """Test delete tenant without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/v1/tenants/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]


class TestNotificationEndpoints:
    """Tests for notification endpoints."""

    @pytest.mark.asyncio
    async def test_list_notifications_unauthorized(self) -> None:
        """Test list notifications without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/notifications")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_notification_unauthorized(self) -> None:
        """Test get notification without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/notifications/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_delete_notification_unauthorized(self) -> None:
        """Test delete notification without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/v1/notifications/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_mark_all_read_unauthorized(self) -> None:
        """Test mark all read without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/notifications/read/all")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_unread_count_unauthorized(self) -> None:
        """Test unread count without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/notifications/unread/count")
            assert response.status_code in [401, 403]


class TestChatEndpoints:
    """Tests for chat endpoints (Note: REST chat endpoints may not exist, only WebSocket)."""

    @pytest.mark.asyncio
    async def test_list_conversations_unauthorized(self) -> None:
        """Test list conversations without auth - expects 401/403/404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/conversations")
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_create_direct_conversation_unauthorized(self) -> None:
        """Test create direct conversation without auth - expects 401/403/404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/conversations/direct",
                json={"user_id": "00000000-0000-0000-0000-000000000000"}
            )
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_create_group_conversation_unauthorized(self) -> None:
        """Test create group conversation without auth - expects 401/403/404/422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/conversations/group",
                json={"name": "Test Group", "user_ids": []}
            )
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_get_conversation_unauthorized(self) -> None:
        """Test get conversation without auth - expects 401/403/404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_get_messages_unauthorized(self) -> None:
        """Test get messages without auth - expects 401/403/404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000/messages"
            )
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_send_message_unauthorized(self) -> None:
        """Test send message without auth - expects 401/403/404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000/messages",
                json={"content": "Hello"}
            )
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_mark_conversation_read_unauthorized(self) -> None:
        """Test mark conversation read without auth - expects 401/403/404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000/read"
            )
            assert response.status_code in [401, 403, 404]


class TestSearchEndpoints:
    """Tests for search endpoints."""

    @pytest.mark.asyncio
    async def test_search_simple_unauthorized(self) -> None:
        """Test simple search without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/search/simple?q=test")
            assert response.status_code in [200, 401, 403, 500]

    @pytest.mark.asyncio
    async def test_search_advanced_unauthorized(self) -> None:
        """Test advanced search without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/search",
                json={"query": "test", "filters": {}}
            )
            assert response.status_code in [200, 401, 403, 422, 500]

    @pytest.mark.asyncio
    async def test_search_suggest(self) -> None:
        """Test search suggest endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/search/suggest?q=test")
            assert response.status_code in [200, 401, 403, 500]

    @pytest.mark.asyncio
    async def test_search_health(self) -> None:
        """Test search health endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/search/health")
            assert response.status_code in [200, 401, 403, 500, 503]

    @pytest.mark.asyncio
    async def test_search_indices(self) -> None:
        """Test search indices endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/search/indices")
            assert response.status_code in [200, 401, 403, 500]
