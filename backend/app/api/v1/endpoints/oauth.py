# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
OAuth2/SSO authentication endpoints.
"""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import (
    CurrentTenantId,
    CurrentUser,
    DbSession,
    SuperuserId,
)
from app.application.services.oauth_service import OAuthService
from app.config import settings
from app.domain.entities.oauth import OAuthProvider
from app.domain.exceptions.base import DomainException
from app.infrastructure.auth import create_access_token, create_refresh_token
from app.infrastructure.auth.jwt_handler import decode_token, hash_jti
from app.infrastructure.database.repositories.session_repository import (
    SQLAlchemySessionRepository,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth/oauth", tags=["OAuth"])


# ==============================================================================
# Schemas
# ==============================================================================


class OAuthConnectionResponse(BaseModel):
    """OAuth connection response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str = Field(max_length=50)
    provider_email: str | None = Field(default=None, max_length=320)
    provider_username: str | None = Field(default=None, max_length=200)
    provider_display_name: str | None = Field(default=None, max_length=200)
    provider_avatar_url: str | None = Field(default=None, max_length=2048)
    is_primary: bool
    last_used_at: datetime | None = None
    created_at: datetime | None = None


class OAuthAuthorizeResponse(BaseModel):
    """OAuth authorization response."""

    authorization_url: str = Field(max_length=4096)
    state: str = Field(max_length=256)


class OAuthTokenResponse(BaseModel):
    """OAuth token response after successful authentication."""

    access_token: str = Field(max_length=2048)
    refresh_token: str = Field(max_length=2048)
    token_type: str = Field(default="bearer", max_length=20)
    expires_in: int
    user_id: UUID
    is_new_user: bool


class SSOConfigRequest(BaseModel):
    """SSO configuration request."""

    provider: str = Field(
        ..., min_length=1, max_length=50, pattern="^[a-z][a-z0-9_-]*$"
    )
    name: str = Field(..., min_length=1, max_length=100)
    client_id: str = Field(..., min_length=1, max_length=256)
    client_secret: str = Field(..., min_length=1, max_length=512)
    scopes: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list, max_length=20
    )
    auto_create_users: bool = True
    auto_update_users: bool = True
    default_role_id: UUID | None = None
    allowed_domains: list[Annotated[str, Field(max_length=253)]] = Field(
        default_factory=list, max_length=50
    )
    is_required: bool = False


class SSOConfigResponse(BaseModel):
    """SSO configuration response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str = Field(max_length=50)
    name: str = Field(max_length=100)
    is_enabled: bool
    auto_create_users: bool
    auto_update_users: bool
    default_role_id: UUID | None = None
    allowed_domains: list[Annotated[str, Field(max_length=253)]] = Field(
        default_factory=list
    )
    is_required: bool
    created_at: datetime | None = None


# ==============================================================================
# OAuth Flow Endpoints
# ==============================================================================


@router.get(
    "/{provider}/authorize",
    response_model=OAuthAuthorizeResponse,
    summary="Start OAuth authorization",
    description="Initiate OAuth flow for the specified provider.",
)
async def authorize(
    provider: str = Path(..., max_length=50),
    *,
    request: Request,
    session: DbSession,
    tenant_id: CurrentTenantId = None,
    redirect_uri: str | None = Query(default=None, max_length=2048),
    scope: str | None = Query(default=None, max_length=1000),
) -> OAuthAuthorizeResponse:
    """
    Start OAuth authorization flow.

    Returns authorization URL to redirect user to.
    """
    try:
        oauth_provider = OAuthProvider(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_PROVIDER",
                "message": "Unsupported OAuth provider",
            },
        ) from None

    service = OAuthService(session)

    scopes = scope.split() if scope else None

    auth_url, state = await service.initiate_oauth(
        provider=oauth_provider,
        tenant_id=tenant_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
    )

    return OAuthAuthorizeResponse(
        authorization_url=auth_url,
        state=state,
    )


@router.get(
    "/{provider}/authorize/redirect",
    summary="Redirect to OAuth provider",
    description="Redirect user to OAuth provider authorization page.",
    responses={
        302: {"description": "Redirect to OAuth provider"},
    },
)
async def authorize_redirect(
    provider: str = Path(..., max_length=50),
    *,
    request: Request,
    session: DbSession,
    tenant_id: CurrentTenantId = None,
    redirect_uri: str | None = Query(default=None, max_length=2048),
    scope: str | None = Query(default=None, max_length=1000),
) -> RedirectResponse:
    """
    Redirect to OAuth provider authorization page.
    """
    try:
        oauth_provider = OAuthProvider(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_PROVIDER",
                "message": "Unsupported OAuth provider",
            },
        ) from None

    service = OAuthService(session)

    scopes = scope.split() if scope else None

    auth_url, _ = await service.initiate_oauth(
        provider=oauth_provider,
        tenant_id=tenant_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
    )

    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/{provider}/callback",
    summary="OAuth callback",
    description="Handle OAuth provider callback with authorization code.",
)
async def callback(
    provider: str = Path(..., max_length=50),
    *,
    session: DbSession,
    response: Response,
    code: str = Query(
        ..., max_length=2048, description="Authorization code from provider"
    ),
    state: str = Query(
        ..., max_length=2048, description="State parameter for CSRF protection"
    ),
    error: str | None = Query(None, max_length=200, description="Error from provider"),
    error_description: str | None = Query(
        None, max_length=2000, description="Error description"
    ),
) -> OAuthTokenResponse:
    """
    Handle OAuth callback from provider.

    Exchanges authorization code for tokens and creates/updates user.
    Tokens are set as HttpOnly cookies.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "AUTH_FAILED",
                "message": "Authentication failed. Please try again.",
            },
        )

    try:
        oauth_provider = OAuthProvider(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_PROVIDER",
                "message": "Unsupported OAuth provider",
            },
        ) from None

    service = OAuthService(session)

    try:
        user, connection, is_new_user = await service.handle_callback(
            provider=oauth_provider,
            code=code,
            state=state,
        )
    except DomainException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "AUTH_FAILED",
                "message": "Authentication failed. Please try again.",
            },
        ) from None

    await session.commit()

    # Generate tokens with user claims (is_superuser, roles)
    extra_claims = {
        "is_superuser": user.is_superuser,
        "roles": [str(r) for r in (user.roles or [])],
    }
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        extra_claims=extra_claims,
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
    )

    # Create OAuth session record (B29)
    payload = decode_token(refresh_token)
    jti = payload.get("jti", "")
    session_repo = SQLAlchemySessionRepository(session)
    from app.domain.entities.session import UserSession

    user_session = UserSession(
        user_id=user.id,
        tenant_id=user.tenant_id,
        refresh_token_hash=hash_jti(jti),
        device_name="OAuth Login",
        device_type="desktop",
        browser="",
        os="",
        ip_address="",
        location="",
        last_activity=datetime.now(UTC),
    )
    await session_repo.create(user_session)
    await session.commit()

    # Set tokens as HttpOnly cookies (not in response body)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth/refresh",
    )

    return OAuthTokenResponse(
        access_token="",
        refresh_token="",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        is_new_user=is_new_user,
    )


@router.get(
    "/{provider}/callback/redirect",
    summary="OAuth callback with redirect",
    description="Handle OAuth callback and redirect to frontend.",
    responses={
        302: {"description": "Redirect to frontend with tokens"},
    },
)
async def callback_redirect(
    provider: str = Path(..., max_length=50),
    *,
    session: DbSession,
    code: str = Query(..., max_length=2048),
    state: str = Query(..., max_length=2048),
    error: str | None = Query(None, max_length=200),
    error_description: str | None = Query(None, max_length=2000),
    frontend_url: str = Query(
        None, max_length=2048, description="Frontend URL to redirect to"
    ),
) -> RedirectResponse:
    """
    Handle OAuth callback and redirect to frontend with tokens.
    """
    # Fallback to configured FRONTEND_URL if not provided
    if not frontend_url:
        frontend_url = settings.FRONTEND_URL

    # Validate frontend_url against allowlist to prevent open redirect
    allowed_origins = {settings.FRONTEND_URL}
    from urllib.parse import urlparse

    parsed_frontend = urlparse(frontend_url)
    if not any(
        urlparse(origin).netloc == parsed_frontend.netloc for origin in allowed_origins
    ):
        frontend_url = settings.FRONTEND_URL

    if error:
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error=provider_error",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        oauth_provider = OAuthProvider(provider.lower())
    except ValueError:
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error=invalid_provider",
            status_code=status.HTTP_302_FOUND,
        )

    service = OAuthService(session)

    try:
        user, connection, is_new_user = await service.handle_callback(
            provider=oauth_provider,
            code=code,
            state=state,
        )
        await session.commit()

        # Generate tokens with user claims (is_superuser, roles)
        extra_claims = {
            "is_superuser": user.is_superuser,
            "roles": [str(r) for r in (user.roles or [])],
        }
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            extra_claims=extra_claims,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
        )

        # Create OAuth session record (B29)
        payload = decode_token(refresh_token)
        jti = payload.get("jti", "")
        session_repo = SQLAlchemySessionRepository(session)
        from app.domain.entities.session import UserSession as UserSessionEntity

        user_session = UserSessionEntity(
            user_id=user.id,
            tenant_id=user.tenant_id,
            refresh_token_hash=hash_jti(jti),
            device_name="OAuth Login",
            device_type="desktop",
            browser="",
            os="",
            ip_address="",
            location="",
            last_activity=datetime.now(UTC),
        )
        await session_repo.create(user_session)
        await session.commit()

        # Set tokens via HttpOnly cookies (never in URL query params)
        redirect = RedirectResponse(
            url=f"{frontend_url}/auth/callback?is_new_user={is_new_user}",
            status_code=status.HTTP_302_FOUND,
        )
        redirect.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )
        redirect.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            path="/api/v1/auth/refresh",
        )
        return redirect

    except DomainException:
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error=auth_failed",
            status_code=status.HTTP_302_FOUND,
        )


# ==============================================================================
# Connection Management Endpoints
# ==============================================================================


@router.get(
    "/connections",
    response_model=list[OAuthConnectionResponse],
    summary="List OAuth connections",
    description="Get all OAuth connections for the current user.",
)
async def list_connections(
    session: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId = None,
) -> list[OAuthConnectionResponse]:
    """
    List all OAuth connections for the current user.
    """
    service = OAuthService(session)

    connections = await service.get_user_connections(
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    return [
        OAuthConnectionResponse(
            id=conn.id,
            provider=conn.provider.value,
            provider_email=conn.provider_email,
            provider_username=conn.provider_username,
            provider_display_name=conn.provider_display_name,
            provider_avatar_url=conn.provider_avatar_url,
            is_primary=conn.is_primary,
            last_used_at=conn.last_used_at,
            created_at=conn.created_at,
        )
        for conn in connections
    ]


@router.post(
    "/{provider}/link",
    response_model=OAuthAuthorizeResponse,
    summary="Link OAuth account",
    description="Link an OAuth provider to the current user account.",
)
async def link_account(
    provider: str = Path(..., max_length=50),
    *,
    session: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId = None,
    scope: str | None = Query(default=None, max_length=1000),
) -> OAuthAuthorizeResponse:
    """
    Start OAuth flow to link account to current user.
    """
    try:
        oauth_provider = OAuthProvider(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_PROVIDER",
                "message": "Unsupported OAuth provider",
            },
        ) from None

    service = OAuthService(session)

    scopes = scope.split() if scope else None

    auth_url, state = await service.initiate_oauth(
        provider=oauth_provider,
        tenant_id=tenant_id,
        scopes=scopes,
        linking_user_id=current_user.id,
    )

    logger.info(
        "oauth_link_initiated",
        user_id=str(current_user.id),
        provider=provider,
    )

    return OAuthAuthorizeResponse(
        authorization_url=auth_url,
        state=state,
    )


@router.delete(
    "/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unlink OAuth account",
    description="Remove an OAuth connection from the current user account.",
)
async def unlink_account(
    connection_id: UUID,
    session: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId = None,
) -> None:
    """
    Unlink OAuth account from current user.
    """
    service = OAuthService(session)

    try:
        success = await service.unlink_oauth_account(
            user_id=current_user.id,
            connection_id=connection_id,
            tenant_id=tenant_id,
        )
    except DomainException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNLINK_FAILED",
                "message": "Cannot unlink this OAuth connection. Ensure you have another login method configured.",
            },
        ) from None

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONNECTION_NOT_FOUND",
                "message": "OAuth connection not found",
            },
        )

    logger.info(
        "oauth_account_unlinked",
        user_id=str(current_user.id),
        connection_id=str(connection_id),
    )

    await session.commit()


# ==============================================================================
# SSO Configuration Endpoints (Admin)
# ==============================================================================


@router.get(
    "/sso/configs",
    response_model=list[SSOConfigResponse],
    summary="List SSO configurations",
    description="Get all SSO configurations for the current tenant.",
)
async def list_sso_configs(
    session: DbSession,
    _superuser_id: SuperuserId,
    tenant_id: CurrentTenantId,
) -> list[SSOConfigResponse]:
    """
    List all SSO configurations for the tenant.

    Requires admin privileges.
    """
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TENANT_REQUIRED",
                "message": "Tenant ID is required for SSO configuration",
            },
        )

    service = OAuthService(session)

    configs = await service.get_sso_config(tenant_id)

    return [
        SSOConfigResponse(
            id=config.id,
            provider=config.provider.value,
            name=config.name,
            is_enabled=config.is_enabled,
            auto_create_users=config.auto_create_users,
            auto_update_users=config.auto_update_users,
            default_role_id=config.default_role_id,
            allowed_domains=config.allowed_domains,
            is_required=config.is_required,
            created_at=config.created_at,
        )
        for config in configs
    ]


@router.post(
    "/sso/configs",
    response_model=SSOConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create SSO configuration",
    description="Create a new SSO configuration for the tenant.",
)
async def create_sso_config(
    data: SSOConfigRequest,
    session: DbSession,
    _superuser_id: SuperuserId,
    tenant_id: CurrentTenantId,
) -> SSOConfigResponse:
    """
    Create new SSO configuration.

    Requires admin privileges.
    """
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TENANT_REQUIRED",
                "message": "Tenant ID is required for SSO configuration",
            },
        )

    try:
        provider = OAuthProvider(data.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_PROVIDER",
                "message": "Unsupported OAuth provider",
            },
        ) from None

    service = OAuthService(session)

    config = await service.create_sso_config(
        tenant_id=tenant_id,
        provider=provider,
        name=data.name,
        client_id=data.client_id,
        client_secret=data.client_secret,
        scopes=data.scopes,
        auto_create_users=data.auto_create_users,
        auto_update_users=data.auto_update_users,
        default_role_id=data.default_role_id,
        allowed_domains=data.allowed_domains,
        is_required=data.is_required,
    )

    await session.commit()

    return SSOConfigResponse(
        id=config.id,
        provider=config.provider.value,
        name=config.name,
        is_enabled=config.is_enabled,
        auto_create_users=config.auto_create_users,
        auto_update_users=config.auto_update_users,
        default_role_id=config.default_role_id,
        allowed_domains=config.allowed_domains,
        is_required=config.is_required,
        created_at=config.created_at,
    )


# ==============================================================================
# Available Providers Endpoint
# ==============================================================================


@router.get(
    "/providers",
    summary="List available OAuth providers",
    description="Get list of available OAuth providers and their status.",
)
async def list_providers(
    session: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId = None,
) -> list[dict]:
    """
    List available OAuth providers.

    Returns configured providers with their availability status.
    """
    from app.config import settings

    providers = []

    # Check built-in providers
    provider_configs = [
        {
            "provider": "google",
            "name": "Google",
            "icon": "google",
            "available": bool(getattr(settings, "OAUTH_GOOGLE_CLIENT_ID", "")),
        },
        {
            "provider": "github",
            "name": "GitHub",
            "icon": "github",
            "available": bool(getattr(settings, "OAUTH_GITHUB_CLIENT_ID", "")),
        },
        {
            "provider": "microsoft",
            "name": "Microsoft",
            "icon": "microsoft",
            "available": bool(getattr(settings, "OAUTH_MICROSOFT_CLIENT_ID", "")),
        },
    ]

    # Add tenant SSO configs if available
    if tenant_id:
        service = OAuthService(session)
        sso_configs = await service.get_sso_config(tenant_id)

        for config in sso_configs:
            providers.append(
                {
                    "provider": config.provider.value,
                    "name": config.name,
                    "icon": config.provider.value,
                    "available": config.is_enabled,
                    "is_sso": True,
                    "is_required": config.is_required,
                }
            )

    # Add built-in providers
    for config in provider_configs:
        # Skip if there's an SSO config that overrides it
        if not any(p.get("provider") == config["provider"] for p in providers):
            providers.append(config)

    return providers
