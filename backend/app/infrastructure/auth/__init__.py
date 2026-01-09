# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Infrastructure auth package - JWT, API keys, OAuth."""

from app.infrastructure.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

from app.infrastructure.auth.oauth_providers import (
    OAuthProviderBase,
    GoogleOAuthProvider,
    GitHubOAuthProvider,
    MicrosoftOAuthProvider,
    DiscordOAuthProvider,
    get_oauth_provider,
    OAUTH_PROVIDERS,
)


__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "verify_password",
    # OAuth
    "OAuthProviderBase",
    "GoogleOAuthProvider",
    "GitHubOAuthProvider",
    "MicrosoftOAuthProvider",
    "DiscordOAuthProvider",
    "get_oauth_provider",
    "OAUTH_PROVIDERS",
]
