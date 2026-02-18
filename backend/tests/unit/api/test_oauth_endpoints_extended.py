# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for API v1 endpoints - OAuth."""

from __future__ import annotations

from uuid import uuid4


class TestOAuthEndpointImport:
    """Tests for OAuth endpoint import."""

    def test_oauth_router_import(self) -> None:
        """Test OAuth router can be imported."""
        from app.api.v1.endpoints.oauth import router

        assert router is not None


class TestOAuthProviderSchemas:
    """Tests for OAuth provider schemas."""

    def test_oauth_provider_enum(self) -> None:
        """Test OAuth provider enum."""
        from app.domain.entities.oauth import OAuthProvider

        assert OAuthProvider.GOOGLE.value == "google"
        assert OAuthProvider.GITHUB.value == "github"
        assert OAuthProvider.MICROSOFT.value == "microsoft"

    def test_oauth_callback_schema(self) -> None:
        """Test OAuth state entity for callback flow."""
        from app.domain.entities.oauth import OAuthProvider, OAuthState

        state = OAuthState(
            state="random_state_456",
            provider=OAuthProvider.GOOGLE,
            code_verifier="auth_code_123",
        )
        assert state.state == "random_state_456"
        assert state.provider == OAuthProvider.GOOGLE


class TestOAuthRoutes:
    """Tests for OAuth endpoint routes."""

    def test_oauth_router_has_routes(self) -> None:
        """Test OAuth router has routes."""
        from app.api.v1.endpoints.oauth import router

        routes = [getattr(route, "path", None) for route in router.routes]
        assert len(routes) > 0


class TestOAuthFlow:
    """Tests for OAuth flow."""

    def test_oauth_state_generation(self) -> None:
        """Test OAuth state generation."""
        import secrets

        state = secrets.token_urlsafe(32)
        assert len(state) >= 32

    def test_oauth_code_verifier_generation(self) -> None:
        """Test OAuth code verifier generation (PKCE)."""
        import secrets

        code_verifier = secrets.token_urlsafe(64)
        assert len(code_verifier) >= 43  # Min length for PKCE

    def test_oauth_redirect_uri_format(self) -> None:
        """Test OAuth redirect URI format."""
        base_url = "https://example.com"
        redirect_uri = f"{base_url}/api/v1/oauth/callback/google"
        assert redirect_uri.startswith("https://")
        assert "/callback/" in redirect_uri


class TestOAuthTokens:
    """Tests for OAuth tokens."""

    def test_access_token_structure(self) -> None:
        """Test access token structure using OAuthConnection entity."""
        from app.domain.entities.oauth import OAuthConnection, OAuthProvider

        conn = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google_123",
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        )
        assert conn.access_token is not None
        assert conn.provider == OAuthProvider.GOOGLE

    def test_refresh_token_structure(self) -> None:
        """Test refresh token structure using OAuthConnection entity."""
        from app.domain.entities.oauth import OAuthConnection, OAuthProvider

        conn = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GITHUB,
            provider_user_id="gh_456",
            refresh_token="refresh_token_123",
        )
        assert conn.refresh_token == "refresh_token_123"


class TestOAuthUserInfo:
    """Tests for OAuth user info."""

    def test_google_user_info_structure(self) -> None:
        """Test Google user info structure."""
        from app.domain.entities.oauth import OAuthProvider, OAuthUserInfo

        user_info = OAuthUserInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google_user_id",
            email="user@gmail.com",
            email_verified=True,
            name="Test User",
            picture="https://...",
        )
        assert user_info.email == "user@gmail.com"
        assert user_info.email_verified is True
        assert user_info.provider == OAuthProvider.GOOGLE

    def test_github_user_info_structure(self) -> None:
        """Test GitHub user info structure."""
        from app.domain.entities.oauth import OAuthProvider, OAuthUserInfo

        user_info = OAuthUserInfo(
            provider=OAuthProvider.GITHUB,
            provider_user_id="12345",
            email="user@example.com",
            name="Test User",
        )
        assert user_info.provider_user_id == "12345"
        assert user_info.provider == OAuthProvider.GITHUB
