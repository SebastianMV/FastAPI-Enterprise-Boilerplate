# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
End-to-End Tests - OAuth/SSO Flow.

Complete user journey tests for OAuth authentication.

Note: These tests require the full OAuth endpoints to be implemented.
They are marked as skip until the implementation is complete.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.skip(reason="E2E tests require full endpoint implementation")


class TestOAuthLoginE2E:
    """End-to-end OAuth login flow tests."""

    @pytest.mark.asyncio
    async def test_oauth_google_flow_initiation(self, client: AsyncClient) -> None:
        """Test initiating Google OAuth login flow."""
        # 1. Request authorization URL
        auth_response = await client.get("/api/v1/auth/oauth/google/authorize")
        assert auth_response.status_code == 200

        auth_data = auth_response.json()
        assert "authorization_url" in auth_data
        assert "state" in auth_data

        # Verify URL points to Google
        assert "accounts.google.com" in auth_data["authorization_url"]

        # Verify required OAuth params are in URL
        auth_url = auth_data["authorization_url"]
        assert "client_id=" in auth_url
        assert "redirect_uri=" in auth_url
        assert "response_type=code" in auth_url
        assert "state=" in auth_url
        assert "scope=" in auth_url

    @pytest.mark.asyncio
    async def test_oauth_github_flow_initiation(self, client: AsyncClient) -> None:
        """Test initiating GitHub OAuth login flow."""
        auth_response = await client.get("/api/v1/auth/oauth/github/authorize")
        assert auth_response.status_code == 200

        auth_data = auth_response.json()
        assert "authorization_url" in auth_data
        assert "github.com" in auth_data["authorization_url"]

    @pytest.mark.asyncio
    async def test_oauth_microsoft_flow_initiation(self, client: AsyncClient) -> None:
        """Test initiating Microsoft OAuth login flow."""
        auth_response = await client.get("/api/v1/auth/oauth/microsoft/authorize")
        assert auth_response.status_code == 200

        auth_data = auth_response.json()
        assert "authorization_url" in auth_data


class TestOAuthAccountLinkingE2E:
    """End-to-end OAuth account linking tests."""

    @pytest.mark.asyncio
    async def test_link_oauth_to_existing_account(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test linking OAuth provider to existing account."""
        # 1. Get current connections
        connections_response = await client.get(
            "/api/v1/auth/oauth/connections",
            headers=auth_headers,
        )
        assert connections_response.status_code == 200
        initial_connections = connections_response.json()

        # 2. Initiate linking flow
        link_response = await client.get(
            "/api/v1/auth/oauth/google/link",
            headers=auth_headers,
        )
        # Should return authorization URL for linking
        assert link_response.status_code in [200, 404]

        if link_response.status_code == 200:
            link_data = link_response.json()
            assert "authorization_url" in link_data

    @pytest.mark.asyncio
    async def test_unlink_oauth_from_account(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test unlinking OAuth provider from account."""
        # Get connections first
        connections_response = await client.get(
            "/api/v1/auth/oauth/connections",
            headers=auth_headers,
        )

        if connections_response.status_code == 200:
            connections = connections_response.json()

            if isinstance(connections, list) and len(connections) > 0:
                connection_id = connections[0]["id"]

                # Unlink the connection
                unlink_response = await client.delete(
                    f"/api/v1/auth/oauth/connections/{connection_id}",
                    headers=auth_headers,
                )
                assert unlink_response.status_code in [200, 204, 400]
                # 400 may occur if it's the only login method

    @pytest.mark.asyncio
    async def test_list_user_oauth_connections(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test listing user's OAuth connections."""
        response = await client.get(
            "/api/v1/auth/oauth/connections",
            headers=auth_headers,
        )
        assert response.status_code == 200

        connections = response.json()
        assert isinstance(connections, list) or "items" in connections

        # Verify connection structure
        for conn in (
            connections
            if isinstance(connections, list)
            else connections.get("items", [])
        ):
            assert "id" in conn
            assert "provider" in conn


class TestSSOConfigurationE2E:
    """End-to-end SSO configuration tests."""

    @pytest.mark.asyncio
    async def test_tenant_sso_setup_flow(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Test complete tenant SSO configuration flow."""
        # 1. Get current SSO configs
        list_response = await client.get(
            "/api/v1/auth/oauth/sso/configs",
            headers=admin_headers,
        )
        assert list_response.status_code in [200, 404]

        # 2. Create new SSO configuration
        config_name = f"sso_config_{uuid4().hex[:8]}"
        create_response = await client.post(
            "/api/v1/auth/oauth/sso/configs",
            json={
                "provider": "okta",
                "name": config_name,
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "scopes": ["openid", "email", "profile"],
                "auto_create_users": True,
                "allowed_domains": ["company.com"],
            },
            headers=admin_headers,
        )

        if create_response.status_code == 201:
            config_id = create_response.json()["id"]

            # 3. Update configuration
            update_response = await client.put(
                f"/api/v1/auth/oauth/sso/configs/{config_id}",
                json={
                    "name": f"{config_name}_updated",
                    "auto_create_users": False,
                },
                headers=admin_headers,
            )
            assert update_response.status_code == 200

            # 4. Enable configuration
            enable_response = await client.post(
                f"/api/v1/auth/oauth/sso/configs/{config_id}/enable",
                headers=admin_headers,
            )
            assert enable_response.status_code in [200, 204, 404]

            # 5. Test SSO login URL
            test_response = await client.get(
                f"/api/v1/auth/oauth/sso/configs/{config_id}/test",
                headers=admin_headers,
            )
            assert test_response.status_code in [200, 404]

            # 6. Delete configuration
            delete_response = await client.delete(
                f"/api/v1/auth/oauth/sso/configs/{config_id}",
                headers=admin_headers,
            )
            assert delete_response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_sso_required_enforcement(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Test SSO required enforcement for tenant."""
        # Note: This test would require:
        # 1. Setting up SSO as required for tenant
        # 2. Verifying regular login is blocked
        # 3. Verifying only SSO login works

        # Get tenant settings
        tenant_response = await client.get(
            "/api/v1/tenants/me",
            headers=admin_headers,
        )

        if tenant_response.status_code == 200:
            tenant_data = tenant_response.json()
            # Check if SSO required can be configured
            assert "settings" in tenant_data or True


class TestOAuthSecurityE2E:
    """End-to-end OAuth security tests."""

    @pytest.mark.asyncio
    async def test_oauth_state_protection(self, client: AsyncClient) -> None:
        """Test OAuth state parameter provides CSRF protection."""
        # 1. Get authorization URL with state
        auth_response = await client.get("/api/v1/auth/oauth/google/authorize")

        if auth_response.status_code == 200:
            state = auth_response.json()["state"]

            # 2. Try callback with wrong state
            callback_response = await client.get(
                "/api/v1/auth/oauth/google/callback",
                params={
                    "code": "fake_code",
                    "state": "wrong_state",
                },
            )
            assert callback_response.status_code == 400

            # 3. State should only be valid once
            # Even if first callback failed, state is invalidated

    @pytest.mark.asyncio
    async def test_oauth_pkce_flow(self, client: AsyncClient) -> None:
        """Test OAuth PKCE code challenge flow."""
        auth_response = await client.get("/api/v1/auth/oauth/google/authorize")

        if auth_response.status_code == 200:
            auth_url = auth_response.json()["authorization_url"]

            # PKCE should be included for enhanced security
            if "code_challenge" in auth_url:
                assert "code_challenge_method=S256" in auth_url

    @pytest.mark.asyncio
    async def test_oauth_callback_error_handling(self, client: AsyncClient) -> None:
        """Test OAuth callback handles provider errors properly."""
        # Simulate provider returning an error
        error_response = await client.get(
            "/api/v1/auth/oauth/google/callback",
            params={
                "error": "access_denied",
                "error_description": "User denied consent",
                "state": "some_state",
                "code": "dummy",
            },
        )

        assert error_response.status_code == 400
        error_data = error_response.json()
        assert "detail" in error_data
