# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for OAuth domain entities.

Tests for OAuth connections, SSO configuration, and related structures.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.entities.oauth import (
    OAuthConnection,
    OAuthProvider,
    OAuthState,
    OAuthUserInfo,
    SSOConfiguration,
)


class TestOAuthProvider:
    """Tests for OAuthProvider enum."""

    def test_implemented_providers(self) -> None:
        """Test implemented OAuth provider values."""
        assert OAuthProvider.GOOGLE.value == "google"
        assert OAuthProvider.GITHUB.value == "github"
        assert OAuthProvider.MICROSOFT.value == "microsoft"

    def test_all_providers_exist(self) -> None:
        """Test all expected providers are defined."""
        expected = {"google", "github", "microsoft"}
        actual = {p.value for p in OAuthProvider}
        assert actual == expected


class TestOAuthConnection:
    """Tests for OAuthConnection entity."""

    def test_create_basic_connection(self) -> None:
        """Test creating basic OAuth connection."""
        conn_id = uuid4()
        user_id = uuid4()
        tenant_id = uuid4()

        connection = OAuthConnection(
            id=conn_id,
            user_id=user_id,
            tenant_id=tenant_id,
            provider=OAuthProvider.GOOGLE,
            provider_user_id="123456789",
        )

        assert connection.id == conn_id
        assert connection.user_id == user_id
        assert connection.tenant_id == tenant_id
        assert connection.provider == OAuthProvider.GOOGLE
        assert connection.provider_user_id == "123456789"

    def test_default_values(self) -> None:
        """Test default values."""
        connection = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GITHUB,
            provider_user_id="12345",
        )

        assert connection.provider_email is None
        assert connection.provider_username is None
        assert connection.provider_display_name is None
        assert connection.provider_avatar_url is None
        assert connection.access_token is None
        assert connection.refresh_token is None
        assert connection.token_expires_at is None
        assert connection.scopes == []
        assert connection.raw_data == {}
        assert connection.is_primary is False
        assert connection.is_active is True
        assert connection.last_used_at is None
        assert connection.created_at is None
        assert connection.updated_at is None

    def test_with_provider_info(self) -> None:
        """Test connection with provider info."""
        connection = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            provider_user_id="123456789",
            provider_email="user@gmail.com",
            provider_username="john.doe",
            provider_display_name="John Doe",
            provider_avatar_url="https://example.com/avatar.jpg",
        )

        assert connection.provider_email == "user@gmail.com"
        assert connection.provider_username == "john.doe"
        assert connection.provider_display_name == "John Doe"
        assert connection.provider_avatar_url == "https://example.com/avatar.jpg"

    def test_with_tokens(self) -> None:
        """Test connection with tokens."""
        expires = datetime.now(UTC) + timedelta(hours=1)

        connection = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GITHUB,
            provider_user_id="12345",
            access_token="access_token_value",
            refresh_token="refresh_token_value",
            token_expires_at=expires,
        )

        assert connection.access_token == "access_token_value"
        assert connection.refresh_token == "refresh_token_value"
        assert connection.token_expires_at == expires

    def test_with_scopes(self) -> None:
        """Test connection with scopes."""
        connection = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            provider_user_id="123",
            scopes=["email", "profile", "openid"],
        )

        assert len(connection.scopes) == 3
        assert "email" in connection.scopes

    def test_primary_connection(self) -> None:
        """Test primary connection flag."""
        connection = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            provider_user_id="123",
            is_primary=True,
        )

        assert connection.is_primary is True

    def test_inactive_connection(self) -> None:
        """Test inactive connection."""
        connection = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            provider_user_id="123",
            is_active=False,
        )

        assert connection.is_active is False


class TestSSOConfiguration:
    """Tests for SSOConfiguration entity."""

    def test_create_basic_sso_config(self) -> None:
        """Test creating basic SSO configuration."""
        config_id = uuid4()
        tenant_id = uuid4()

        config = SSOConfiguration(
            id=config_id,
            tenant_id=tenant_id,
            provider=OAuthProvider.GOOGLE,
            name="Corporate SSO",
            client_id="client_123",
            client_secret="secret_456",
        )

        assert config.id == config_id
        assert config.tenant_id == tenant_id
        assert config.provider == OAuthProvider.GOOGLE
        assert config.name == "Corporate SSO"
        assert config.client_id == "client_123"
        assert config.client_secret == "secret_456"

    def test_default_values(self) -> None:
        """Test default values."""
        config = SSOConfiguration(
            id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            name="Test SSO",
            client_id="client",
            client_secret="secret",
        )

        assert config.authorization_url is None
        assert config.token_url is None
        assert config.userinfo_url is None
        assert config.scopes == []
        assert config.auto_create_users is True
        assert config.auto_update_users is True
        assert config.default_role_id is None
        assert config.allowed_domains == []
        assert config.is_required is False
        assert config.is_enabled is True
        assert config.created_at is None
        assert config.updated_at is None

    def test_default_attribute_mapping(self) -> None:
        """Test default attribute mapping."""
        config = SSOConfiguration(
            id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            name="Test SSO",
            client_id="client",
            client_secret="secret",
        )

        assert config.attribute_mapping["email"] == "email"
        assert config.attribute_mapping["name"] == "name"
        assert config.attribute_mapping["given_name"] == "given_name"
        assert config.attribute_mapping["family_name"] == "family_name"
        assert config.attribute_mapping["picture"] == "picture"

    def test_with_custom_urls(self) -> None:
        """Test SSO config with custom URLs."""
        config = SSOConfiguration(
            id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.MICROSOFT,
            name="Microsoft SSO",
            client_id="client",
            client_secret="secret",
            authorization_url="https://login.microsoftonline.com/auth",
            token_url="https://login.microsoftonline.com/token",
            userinfo_url="https://graph.microsoft.com/userinfo",
        )

        assert config.authorization_url == "https://login.microsoftonline.com/auth"
        assert config.token_url == "https://login.microsoftonline.com/token"
        assert config.userinfo_url == "https://graph.microsoft.com/userinfo"

    def test_with_domain_restrictions(self) -> None:
        """Test SSO config with domain restrictions."""
        config = SSOConfiguration(
            id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GITHUB,
            name="Corporate SSO",
            client_id="client",
            client_secret="secret",
            allowed_domains=["company.com", "subsidiary.com"],
        )

        assert len(config.allowed_domains) == 2
        assert "company.com" in config.allowed_domains

    def test_required_sso(self) -> None:
        """Test required SSO configuration."""
        config = SSOConfiguration(
            id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.MICROSOFT,
            name="Required SSO",
            client_id="client",
            client_secret="secret",
            is_required=True,
        )

        assert config.is_required is True


class TestOAuthState:
    """Tests for OAuthState entity."""

    def test_create_basic_state(self) -> None:
        """Test creating basic OAuth state."""
        state = OAuthState(
            state="random_state_string",
            provider=OAuthProvider.GOOGLE,
        )

        assert state.state == "random_state_string"
        assert state.provider == OAuthProvider.GOOGLE

    def test_default_values(self) -> None:
        """Test default values."""
        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.GITHUB,
        )

        assert state.tenant_id is None
        assert state.redirect_uri is None
        assert state.nonce is None
        assert state.code_verifier is None
        assert state.created_at is None
        assert state.expires_at is None
        assert state.is_linking is False
        assert state.existing_user_id is None

    def test_with_tenant_and_redirect(self) -> None:
        """Test state with tenant and redirect."""
        tenant_id = uuid4()

        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.GOOGLE,
            tenant_id=tenant_id,
            redirect_uri="https://app.example.com/callback",
        )

        assert state.tenant_id == tenant_id
        assert state.redirect_uri == "https://app.example.com/callback"

    def test_with_pkce(self) -> None:
        """Test state with PKCE code verifier."""
        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.GOOGLE,
            code_verifier="pkce_code_verifier_value",
        )

        assert state.code_verifier == "pkce_code_verifier_value"

    def test_with_openid_connect(self) -> None:
        """Test state with OpenID Connect nonce."""
        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.GOOGLE,
            nonce="random_nonce_value",
        )

        assert state.nonce == "random_nonce_value"

    def test_linking_state(self) -> None:
        """Test state for account linking."""
        existing_user = uuid4()

        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.GITHUB,
            is_linking=True,
            existing_user_id=existing_user,
        )

        assert state.is_linking is True
        assert state.existing_user_id == existing_user

    def test_with_expiration(self) -> None:
        """Test state with expiration."""
        created = datetime.now(UTC)
        expires = created + timedelta(minutes=10)

        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.GOOGLE,
            created_at=created,
            expires_at=expires,
        )

        assert state.created_at == created
        assert state.expires_at == expires


class TestOAuthUserInfo:
    """Tests for OAuthUserInfo entity."""

    def test_create_basic_user_info(self) -> None:
        """Test creating basic user info."""
        info = OAuthUserInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="123456789",
        )

        assert info.provider == OAuthProvider.GOOGLE
        assert info.provider_user_id == "123456789"

    def test_default_values(self) -> None:
        """Test default values."""
        info = OAuthUserInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="123",
        )

        assert info.email is None
        assert info.email_verified is False
        assert info.name is None
        assert info.given_name is None
        assert info.family_name is None
        assert info.picture is None
        assert info.locale is None
        assert info.raw_data == {}

    def test_with_full_profile(self) -> None:
        """Test user info with full profile."""
        info = OAuthUserInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="123456789",
            email="user@gmail.com",
            email_verified=True,
            name="John Doe",
            given_name="John",
            family_name="Doe",
            picture="https://example.com/avatar.jpg",
            locale="en-US",
        )

        assert info.email == "user@gmail.com"
        assert info.email_verified is True
        assert info.name == "John Doe"
        assert info.given_name == "John"
        assert info.family_name == "Doe"
        assert info.picture == "https://example.com/avatar.jpg"
        assert info.locale == "en-US"

    def test_with_raw_data(self) -> None:
        """Test user info with raw data."""
        raw = {
            "sub": "123456789",
            "email": "user@gmail.com",
            "hd": "example.com",
            "custom_field": "value",
        }

        info = OAuthUserInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="123456789",
            raw_data=raw,
        )

        assert info.raw_data["sub"] == "123456789"
        assert info.raw_data["hd"] == "example.com"
