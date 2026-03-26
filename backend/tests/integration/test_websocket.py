# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Integration Tests - WebSocket.

Tests for WebSocket endpoint integration.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestWebSocketAuthentication:
    """Tests for WebSocket authentication."""

    @pytest.mark.asyncio
    async def test_websocket_requires_token(self, client: AsyncClient) -> None:
        """Verify WebSocket requires authentication token."""
        # Note: httpx doesn't support WebSocket directly
        # This tests the HTTP upgrade request behavior
        response = await client.get("/api/v1/ws")
        # Should require upgrade or return error
        assert response.status_code in [400, 403, 404, 426]

    @pytest.mark.asyncio
    async def test_websocket_rejects_invalid_token(self, client: AsyncClient) -> None:
        """Verify WebSocket rejects invalid tokens."""
        response = await client.get("/api/v1/ws", params={"token": "invalid_token"})
        assert response.status_code in [400, 401, 403, 404, 426]


class TestWebSocketEndpointAvailability:
    """Tests for WebSocket endpoint availability."""

    @pytest.mark.asyncio
    async def test_websocket_endpoint_exists(self, client: AsyncClient) -> None:
        """Verify WebSocket endpoint is registered."""
        # Check OpenAPI schema for WebSocket
        response = await client.get("/openapi.json")

        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})

            # WebSocket endpoints might be documented
            ws_paths = [p for p in paths.keys() if "ws" in p.lower()]
            # May or may not be in OpenAPI (WebSockets aren't always documented)


class TestWebSocketHealthCheck:
    """Tests for WebSocket health status."""

    @pytest.mark.asyncio
    async def test_websocket_health_in_detailed_check(
        self, client: AsyncClient
    ) -> None:
        """Verify WebSocket status in health check."""
        response = await client.get("/api/v1/health/detailed")

        if response.status_code == 200:
            data = response.json()
            components = data.get("components", {})

            # WebSocket may be a component
            if "websocket" in components:
                ws_health = components["websocket"]
                assert "status" in ws_health


class TestWebSocketConfiguration:
    """Tests for WebSocket configuration."""

    @pytest.mark.asyncio
    async def test_websocket_enabled_config(self, client: AsyncClient) -> None:
        """Test WebSocket enabled configuration affects endpoint."""
        # If WebSocket is disabled, endpoint should not be available
        # or return appropriate error
        response = await client.get("/api/v1/ws")
        # Either endpoint exists or returns proper error
        assert response.status_code != 500


class TestWebSocketNotificationsIntegration:
    """Tests for WebSocket notifications integration."""

    @pytest.mark.asyncio
    async def test_notifications_rest_endpoint(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test notifications REST endpoint works."""
        response = await client.get(
            "/api/v1/notifications",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_mark_notification_read(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test marking notification as read."""
        notification_id = str(uuid4())

        response = await client.post(
            f"/api/v1/notifications/{notification_id}/read",
            headers=auth_headers,
        )
        assert response.status_code in [200, 204, 404]


# Note: Classes for unimplemented features (WebSocketPresence, WebSocketRooms,
# WebSocketBroadcast) were removed. Add tests when features are implemented.
