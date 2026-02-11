# Copyright (c) 2025-2026 SebastiÃ¡n MuÃ±oz
# Licensed under the MIT License

"""
OAuth2 provider implementations.

Supports multiple OAuth2 providers with a pluggable architecture.
"""

import base64
import hashlib
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

# Timeout for all outbound OAuth HTTP calls (seconds)
_OAUTH_HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

from app.domain.entities.oauth import OAuthProvider, OAuthUserInfo
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OAuthTokenResponse:
    """Response from OAuth token endpoint."""

    access_token: str
    token_type: str
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None  # OpenID Connect


class OAuthProviderBase(ABC):
    """Base class for OAuth2 providers."""

    provider: OAuthProvider

    # OAuth2 endpoints
    authorization_url: str
    token_url: str
    userinfo_url: str
    revoke_url: str | None = None

    # Default scopes
    default_scopes: list[str] = []

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def generate_state(self) -> str:
        """Generate a secure random state string."""
        return secrets.token_urlsafe(32)

    def generate_pkce(self) -> tuple[str, str]:
        """
        Generate PKCE code verifier and challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        code_verifier = secrets.token_urlsafe(64)

        # SHA256 hash and base64url encode
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

        return code_verifier, code_challenge

    def get_authorization_url(
        self,
        state: str,
        scopes: list[str] | None = None,
        code_challenge: str | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        """
        Build the authorization URL.

        Args:
            state: CSRF state token
            scopes: OAuth scopes to request
            code_challenge: PKCE code challenge
            extra_params: Additional provider-specific params

        Returns:
            Full authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": " ".join(scopes or self.default_scopes),
        }

        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        if extra_params:
            params.update(extra_params)

        return f"{self.authorization_url}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        code_verifier: str | None = None,
    ) -> OAuthTokenResponse:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier (if PKCE was used)

        Returns:
            Token response
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        if code_verifier:
            data["code_verifier"] = code_verifier

        async with httpx.AsyncClient(timeout=_OAUTH_HTTP_TIMEOUT) as client:
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()

            result = response.json()

            return OAuthTokenResponse(
                access_token=result["access_token"],
                token_type=result.get("token_type", "Bearer"),
                expires_in=result.get("expires_in"),
                refresh_token=result.get("refresh_token"),
                scope=result.get("scope"),
                id_token=result.get("id_token"),
            )

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> OAuthTokenResponse:
        """Refresh an access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient(timeout=_OAUTH_HTTP_TIMEOUT) as client:
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()

            result = response.json()

            return OAuthTokenResponse(
                access_token=result["access_token"],
                token_type=result.get("token_type", "Bearer"),
                expires_in=result.get("expires_in"),
                refresh_token=result.get("refresh_token", refresh_token),
                scope=result.get("scope"),
            )

    @abstractmethod
    async def get_user_info(
        self,
        access_token: str,
    ) -> OAuthUserInfo:
        """
        Get user information from provider.

        Args:
            access_token: OAuth access token

        Returns:
            Normalized user info
        """

    async def revoke_token(self, token: str) -> bool:
        """Revoke an access or refresh token."""
        if not self.revoke_url:
            return False

        try:
            async with httpx.AsyncClient(timeout=_OAUTH_HTTP_TIMEOUT) as client:
                response = await client.post(
                    self.revoke_url,
                    data={"token": token},
                    auth=(self.client_id, self.client_secret),
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("Failed to revoke token: %s", e)
            return False


class GoogleOAuthProvider(OAuthProviderBase):
    """Google OAuth2 provider."""

    provider = OAuthProvider.GOOGLE
    authorization_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    revoke_url = "https://oauth2.googleapis.com/revoke"

    default_scopes = [
        "openid",
        "email",
        "profile",
    ]

    def get_authorization_url(
        self,
        state: str,
        scopes: list[str] | None = None,
        code_challenge: str | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        """Add Google-specific params."""
        params = extra_params or {}
        params.setdefault("access_type", "offline")  # Get refresh token
        params.setdefault("prompt", "consent")  # Always show consent screen

        return super().get_authorization_url(
            state=state,
            scopes=scopes,
            code_challenge=code_challenge,
            extra_params=params,
        )

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from Google."""
        async with httpx.AsyncClient(timeout=_OAUTH_HTTP_TIMEOUT) as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()

            data = response.json()

            return OAuthUserInfo(
                provider=self.provider,
                provider_user_id=data["sub"],
                email=data.get("email"),
                email_verified=data.get("email_verified", False),
                name=data.get("name"),
                given_name=data.get("given_name"),
                family_name=data.get("family_name"),
                picture=data.get("picture"),
                locale=data.get("locale"),
                raw_data=data,
            )


class GitHubOAuthProvider(OAuthProviderBase):
    """GitHub OAuth2 provider."""

    provider = OAuthProvider.GITHUB
    authorization_url = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"
    userinfo_url = "https://api.github.com/user"
    emails_url = "https://api.github.com/user/emails"

    default_scopes = [
        "read:user",
        "user:email",
    ]

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from GitHub."""
        async with httpx.AsyncClient(timeout=_OAUTH_HTTP_TIMEOUT) as client:
            # Get user profile
            response = await client.get(
                self.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            data = response.json()

            # Get primary email
            email = data.get("email")
            email_verified = False

            if not email:
                # Fetch emails separately
                emails_response = await client.get(
                    self.emails_url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    for e in emails:
                        if e.get("primary"):
                            email = e.get("email")
                            email_verified = e.get("verified", False)
                            break

            return OAuthUserInfo(
                provider=self.provider,
                provider_user_id=str(data["id"]),
                email=email,
                email_verified=email_verified,
                name=data.get("name"),
                given_name=None,  # GitHub doesn't split names
                family_name=None,
                picture=data.get("avatar_url"),
                locale=None,
                raw_data=data,
            )


class MicrosoftOAuthProvider(OAuthProviderBase):
    """Microsoft (Azure AD) OAuth2 provider."""

    provider = OAuthProvider.MICROSOFT
    authorization_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    userinfo_url = "https://graph.microsoft.com/v1.0/me"

    default_scopes = [
        "openid",
        "email",
        "profile",
        "User.Read",
    ]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        tenant_id: str = "common",  # "common", "organizations", "consumers", or specific tenant
    ) -> None:
        super().__init__(client_id, client_secret, redirect_uri)
        self.tenant_id = tenant_id

        # Update URLs for specific tenant
        if tenant_id != "common":
            self.authorization_url = (
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
            )
            self.token_url = (
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            )

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from Microsoft Graph."""
        async with httpx.AsyncClient(timeout=_OAUTH_HTTP_TIMEOUT) as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()

            data = response.json()

            return OAuthUserInfo(
                provider=self.provider,
                provider_user_id=data["id"],
                email=data.get("mail") or data.get("userPrincipalName"),
                email_verified=True,  # Microsoft verifies emails
                name=data.get("displayName"),
                given_name=data.get("givenName"),
                family_name=data.get("surname"),
                picture=None,  # Requires separate Graph API call
                locale=data.get("preferredLanguage"),
                raw_data=data,
            )


# Provider registry
OAUTH_PROVIDERS: dict[OAuthProvider, type[OAuthProviderBase]] = {
    OAuthProvider.GOOGLE: GoogleOAuthProvider,
    OAuthProvider.GITHUB: GitHubOAuthProvider,
    OAuthProvider.MICROSOFT: MicrosoftOAuthProvider,
}


def get_oauth_provider(
    provider: OAuthProvider,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    **kwargs: Any,
) -> OAuthProviderBase:
    """
    Get an OAuth provider instance.

    Args:
        provider: The OAuth provider type
        client_id: OAuth client ID
        client_secret: OAuth client secret
        redirect_uri: OAuth redirect URI
        **kwargs: Provider-specific arguments

    Returns:
        Configured OAuth provider instance

    Raises:
        ValueError: If provider is not supported
    """
    provider_class = OAUTH_PROVIDERS.get(provider)

    if not provider_class:
        raise ValueError(f"Unsupported OAuth provider: {provider}")

    return provider_class(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        **kwargs,
    )
