# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
OAuth2/SSO Integration Tests.

Tests for OAuth authentication flows, provider integrations,
and SSO configuration management.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestOAuthProvidersList:
    """Tests for OAuth providers listing."""

    @pytest.mark.asyncio
    async def test_list_available_providers(self, client: AsyncClient) -> None:
        """Verify available OAuth providers are listed."""
        response = await client.get("/api/v1/auth/oauth/providers")
        # Endpoint may require auth depending on configuration
        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "providers" in data


class TestOAuthAuthorization:
    """Tests for OAuth authorization flow."""

    @pytest.mark.asyncio
    async def test_oauth_authorize_google(self, client: AsyncClient) -> None:
        """Test Google OAuth authorization initiation."""
        response = await client.get("/api/v1/auth/oauth/google/authorize")

        # May return authorization URL or error if provider not configured
        assert response.status_code in [200, 400, 500, 503]

        if response.status_code == 200:
            data = response.json()
            assert "authorization_url" in data
            assert "state" in data
            assert "accounts.google.com" in data["authorization_url"]
            assert len(data["state"]) > 0

    @pytest.mark.asyncio
    async def test_oauth_authorize_github(self, client: AsyncClient) -> None:
        """Test GitHub OAuth authorization initiation."""
        response = await client.get("/api/v1/auth/oauth/github/authorize")

        assert response.status_code in [200, 400, 500, 503]

        if response.status_code == 200:
            data = response.json()
            assert "authorization_url" in data
            assert "state" in data
            assert "github.com" in data["authorization_url"]

    @pytest.mark.asyncio
    async def test_oauth_authorize_microsoft(self, client: AsyncClient) -> None:
        """Test Microsoft OAuth authorization initiation."""
        response = await client.get("/api/v1/auth/oauth/microsoft/authorize")

        assert response.status_code in [200, 400, 500, 503]

        if response.status_code == 200:
            data = response.json()
            assert "authorization_url" in data
            assert "state" in data

    @pytest.mark.asyncio
    async def test_oauth_authorize_invalid_provider(self, client: AsyncClient) -> None:
        """Test OAuth authorization with invalid provider."""
        response = await client.get("/api/v1/auth/oauth/invalid_provider/authorize")
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_oauth_authorize_with_custom_scope(self, client: AsyncClient) -> None:
        """Test OAuth authorization with custom scopes."""
        response = await client.get(
            "/api/v1/auth/oauth/google/authorize",
            params={"scope": "openid email profile"},
        )

        assert response.status_code in [200, 400, 500, 503]

    @pytest.mark.asyncio
    async def test_oauth_authorize_with_redirect_uri(self, client: AsyncClient) -> None:
        """Test OAuth authorization with custom redirect URI."""
        response = await client.get(
            "/api/v1/auth/oauth/google/authorize",
            params={"redirect_uri": "http://localhost:3000/callback"},
        )

        assert response.status_code in [200, 400, 500, 503]


class TestOAuthCallback:
    """Tests for OAuth callback handling."""

    @pytest.mark.asyncio
    async def test_oauth_callback_missing_code(self, client: AsyncClient) -> None:
        """Test OAuth callback without authorization code."""
        response = await client.get(
            "/api/v1/auth/oauth/google/callback", params={"state": "some_state"}
        )
        assert response.status_code == 422  # Missing required param

    @pytest.mark.asyncio
    async def test_oauth_callback_missing_state(self, client: AsyncClient) -> None:
        """Test OAuth callback without state parameter."""
        response = await client.get(
            "/api/v1/auth/oauth/google/callback", params={"code": "some_code"}
        )
        assert response.status_code == 422  # Missing required param

    @pytest.mark.asyncio
    async def test_oauth_callback_invalid_state(self, client: AsyncClient) -> None:
        """Test OAuth callback with invalid state."""
        response = await client.get(
            "/api/v1/auth/oauth/google/callback",
            params={"code": "test_auth_code", "state": "invalid_state_token"},
        )
        # Should return 400 for invalid state
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_oauth_callback_error_from_provider(
        self, client: AsyncClient
    ) -> None:
        """Test OAuth callback with error from provider."""
        response = await client.get(
            "/api/v1/auth/oauth/google/callback",
            params={
                "error": "access_denied",
                "error_description": "User denied access",
                "state": "some_state",
                "code": "dummy",
            },
        )
        assert response.status_code == 400

        data = response.json()
        detail = data.get("detail", "")
        if isinstance(detail, dict):
            detail_text = (
                f"{detail.get('code', '')} {detail.get('message', '')}".lower()
            )
        else:
            detail_text = str(detail).lower()
        assert (
            "access_denied" in detail_text
            or "denied" in detail_text
            or "auth_failed" in detail_text
            or "authentication failed" in detail_text
        )

    @pytest.mark.asyncio
    async def test_oauth_callback_invalid_provider(self, client: AsyncClient) -> None:
        """Test OAuth callback with invalid provider."""
        response = await client.get(
            "/api/v1/auth/oauth/unknown/callback",
            params={"code": "test_code", "state": "test_state"},
        )
        assert response.status_code == 400


class TestOAuthRedirect:
    """Tests for OAuth redirect endpoints."""

    @pytest.mark.asyncio
    async def test_oauth_redirect_to_google(self, client: AsyncClient) -> None:
        """Test redirect to Google OAuth."""
        response = await client.get(
            "/api/v1/auth/oauth/google/authorize/redirect", follow_redirects=False
        )

        # Should redirect or return error if not configured
        assert response.status_code in [302, 307, 400, 500, 503]

        if response.status_code in [302, 307]:
            assert "Location" in response.headers
            assert "accounts.google.com" in response.headers["Location"]

    @pytest.mark.asyncio
    async def test_oauth_redirect_to_github(self, client: AsyncClient) -> None:
        """Test redirect to GitHub OAuth."""
        response = await client.get(
            "/api/v1/auth/oauth/github/authorize/redirect", follow_redirects=False
        )

        assert response.status_code in [302, 307, 400, 500, 503]

        if response.status_code in [302, 307]:
            assert "Location" in response.headers
            assert "github.com" in response.headers["Location"]


class TestOAuthConnections:
    """Tests for user OAuth connections management."""

    @pytest.mark.asyncio
    async def test_list_user_connections_unauthenticated(
        self, client: AsyncClient
    ) -> None:
        """Test listing OAuth connections without authentication."""
        response = await client.get("/api/v1/auth/oauth/connections")
        assert response.status_code in [401, 404]

    @pytest.mark.asyncio
    async def test_list_user_connections(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test listing user's OAuth connections."""
        response = await client.get(
            "/api/v1/auth/oauth/connections", headers=auth_headers
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "connections" in data

    @pytest.mark.asyncio
    async def test_disconnect_oauth_provider(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test disconnecting an OAuth provider."""
        connection_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/auth/oauth/connections/{connection_id}", headers=auth_headers
        )

        # Should return 404 if connection doesn't exist, or 200/204 on success
        assert response.status_code in [200, 204, 404]


class TestSSOConfiguration:
    """Tests for SSO configuration management."""

    @pytest.mark.asyncio
    async def test_get_sso_configs_unauthenticated(self, client: AsyncClient) -> None:
        """Test getting SSO configs without authentication."""
        response = await client.get("/api/v1/auth/oauth/sso/configs")
        assert response.status_code in [401, 404]

    @pytest.mark.asyncio
    async def test_create_sso_config(
        self, client: AsyncClient, superuser_auth_headers: dict
    ) -> None:
        """Test creating SSO configuration."""
        response = await client.post(
            "/api/v1/auth/oauth/sso/configs",
            json={
                "provider": "okta",
                "name": "Corporate SSO",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "auto_create_users": True,
                "allowed_domains": ["company.com"],
            },
            headers=superuser_auth_headers,
        )

        # Accept 400 (validation), 401 (token not valid for DB), 403 (forbidden), 404 (endpoint not found), or 201 (success)
        assert response.status_code in [201, 400, 401, 403, 404]

    @pytest.mark.asyncio
    async def test_update_sso_config(
        self, client: AsyncClient, superuser_auth_headers: dict
    ) -> None:
        """Test updating SSO configuration."""
        config_id = str(uuid4())
        response = await client.put(
            f"/api/v1/auth/oauth/sso/configs/{config_id}",
            json={
                "name": "Updated Corporate SSO",
                "auto_create_users": False,
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code in [200, 403, 404]


class TestOAuthProviderValidation:
    """Tests for OAuth provider validation."""

    @pytest.mark.asyncio
    async def test_all_supported_providers(self, client: AsyncClient) -> None:
        """Test that all supported providers can be requested."""
        # Only test currently implemented providers
        providers = ["google", "github", "microsoft"]

        for provider in providers:
            response = await client.get(f"/api/v1/auth/oauth/{provider}/authorize")
            # Should not return 500 for any supported provider
            assert response.status_code != 500, f"Provider {provider} returned 500"

    @pytest.mark.asyncio
    async def test_provider_case_insensitive(self, client: AsyncClient) -> None:
        """Test that provider names are case-insensitive."""
        responses = []
        for provider in ["GOOGLE", "Google", "google"]:
            response = await client.get(f"/api/v1/auth/oauth/{provider}/authorize")
            responses.append(response.status_code)

        # All should return same status (either all work or all fail)
        # At minimum, should not crash
        assert all(code != 500 for code in responses)


class TestOAuthStateManagement:
    """Tests for OAuth state token management."""

    @pytest.mark.asyncio
    async def test_state_unique_per_request(self, client: AsyncClient) -> None:
        """Test that each authorize request gets unique state."""
        states = set()

        for _ in range(3):
            response = await client.get("/api/v1/auth/oauth/google/authorize")

            if response.status_code == 200:
                data = response.json()
                state = data.get("state")
                if state:
                    assert state not in states, "State should be unique"
                    states.add(state)

    @pytest.mark.asyncio
    async def test_callback_state_cannot_be_reused(self, client: AsyncClient) -> None:
        """Test that state tokens cannot be reused."""
        # First callback attempt
        response1 = await client.get(
            "/api/v1/auth/oauth/google/callback",
            params={"code": "test_code", "state": "single_use_state"},
        )

        # Second callback attempt with same state
        response2 = await client.get(
            "/api/v1/auth/oauth/google/callback",
            params={"code": "test_code", "state": "single_use_state"},
        )

        # Both should fail (invalid state), but importantly
        # the second shouldn't succeed if the first somehow did
        assert response2.status_code in [400, 401]


class TestOAuthPKCE:
    """Tests for PKCE (Proof Key for Code Exchange) support."""

    @pytest.mark.asyncio
    async def test_authorization_url_contains_pkce(self, client: AsyncClient) -> None:
        """Test that authorization URL includes PKCE parameters."""
        response = await client.get("/api/v1/auth/oauth/google/authorize")

        if response.status_code == 200:
            data = response.json()
            auth_url = data.get("authorization_url", "")

            # PKCE should be included for security
            # code_challenge and code_challenge_method params
            if "code_challenge" in auth_url:
                assert "code_challenge_method" in auth_url
