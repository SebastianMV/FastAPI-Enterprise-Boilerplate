# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
OAuth2/SSO domain entities.

Represents OAuth connections and SSO configurations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class OAuthProvider(str, Enum):
    """Supported OAuth2 providers."""

    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"


@dataclass
class OAuthConnection:
    """
    Represents a user's connection to an OAuth provider.

    A user can have multiple OAuth connections (e.g., Google + GitHub).
    """

    id: UUID
    user_id: UUID
    tenant_id: UUID
    provider: OAuthProvider
    provider_user_id: str  # User ID from the provider
    provider_email: str | None = None
    provider_username: str | None = None
    provider_display_name: str | None = None
    provider_avatar_url: str | None = None

    # Tokens (encrypted at rest)
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None

    # Scopes granted
    scopes: list[str] = field(default_factory=list)

    # Provider-specific data
    raw_data: dict[str, Any] = field(default_factory=dict)

    # Metadata
    is_primary: bool = False  # Primary login method
    is_active: bool = True
    last_used_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class SSOConfiguration:
    """
    SSO configuration for a tenant.

    Allows tenants to configure their own SSO provider
    (e.g., corporate Okta, Azure AD).
    """

    id: UUID
    tenant_id: UUID
    provider: OAuthProvider
    name: str  # Display name (e.g., "Corporate SSO")

    # OAuth2 Configuration
    client_id: str
    client_secret: str  # Encrypted
    authorization_url: str | None = None  # Custom auth URL
    token_url: str | None = None  # Custom token URL
    userinfo_url: str | None = None  # Custom userinfo URL

    # Scopes to request
    scopes: list[str] = field(default_factory=list)

    # User attribute mapping
    attribute_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "email": "email",
            "name": "name",
            "given_name": "given_name",
            "family_name": "family_name",
            "picture": "picture",
        }
    )

    # Auto-provisioning settings
    auto_create_users: bool = True
    auto_update_users: bool = True
    default_role_id: UUID | None = None

    # Domain restrictions (e.g., only @company.com)
    allowed_domains: list[str] = field(default_factory=list)

    # Enforcement
    is_required: bool = False  # Force SSO for all tenant users
    is_enabled: bool = True

    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class OAuthState:
    """
    OAuth state for CSRF protection.

    Stored temporarily during OAuth flow.
    """

    state: str  # Random state string
    provider: OAuthProvider
    tenant_id: UUID | None = None
    redirect_uri: str | None = None
    nonce: str | None = None  # For OpenID Connect
    code_verifier: str | None = None  # For PKCE
    created_at: datetime | None = None
    expires_at: datetime | None = None

    # Additional context
    is_linking: bool = False  # Linking to existing account
    existing_user_id: UUID | None = None


@dataclass
class OAuthUserInfo:
    """
    Normalized user info from OAuth provider.

    Different providers return data in different formats.
    This normalizes it to a common structure.
    """

    provider: OAuthProvider
    provider_user_id: str
    email: str | None = None
    email_verified: bool = False
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None
    locale: str | None = None

    # Raw data from provider
    raw_data: dict[str, Any] = field(default_factory=dict)
