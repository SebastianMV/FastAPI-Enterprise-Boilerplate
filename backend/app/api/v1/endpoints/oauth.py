# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
OAuth2/SSO authentication endpoints.
"""

from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import (
    CurrentUser,
    DbSession,
    CurrentTenantId,
)
from app.application.services.oauth_service import OAuthService
from app.config import settings
from app.domain.entities.oauth import OAuthProvider
from app.infrastructure.auth import create_access_token, create_refresh_token


router = APIRouter(prefix="/auth/oauth", tags=["OAuth"])


# ==============================================================================
# Schemas
# ==============================================================================


class OAuthConnectionResponse(BaseModel):
    """OAuth connection response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    provider: str
    provider_email: str | None = None
    provider_username: str | None = None
    provider_display_name: str | None = None
    provider_avatar_url: str | None = None
    is_primary: bool
    last_used_at: datetime | None = None
    created_at: datetime | None = None


class OAuthAuthorizeResponse(BaseModel):
    """OAuth authorization response."""
    
    authorization_url: str
    state: str


class OAuthTokenResponse(BaseModel):
    """OAuth token response after successful authentication."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: UUID
    is_new_user: bool


class SSOConfigRequest(BaseModel):
    """SSO configuration request."""
    
    provider: str
    name: str = Field(..., min_length=1, max_length=100)
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)
    scopes: list[str] = Field(default_factory=list)
    auto_create_users: bool = True
    auto_update_users: bool = True
    default_role_id: UUID | None = None
    allowed_domains: list[str] = Field(default_factory=list)
    is_required: bool = False


class SSOConfigResponse(BaseModel):
    """SSO configuration response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    provider: str
    name: str
    is_enabled: bool
    auto_create_users: bool
    auto_update_users: bool
    default_role_id: UUID | None = None
    allowed_domains: list[str]
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
    provider: str,
    request: Request,
    session: DbSession,
    tenant_id: CurrentTenantId = None,
    redirect_uri: str | None = None,
    scope: str | None = None,
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
            detail=f"Unsupported OAuth provider: {provider}",
        )
    
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
    provider: str,
    request: Request,
    session: DbSession,
    tenant_id: CurrentTenantId = None,
    redirect_uri: str | None = None,
    scope: str | None = None,
) -> RedirectResponse:
    """
    Redirect to OAuth provider authorization page.
    """
    try:
        oauth_provider = OAuthProvider(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )
    
    service = OAuthService(session)
    
    scopes = scope.split() if scope else None
    
    auth_url, _ = await service.initiate_oauth(
        provider=oauth_provider,
        tenant_id=tenant_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
    )
    
    return RedirectResponse(url=auth_url, status_code=302)


@router.get(
    "/{provider}/callback",
    summary="OAuth callback",
    description="Handle OAuth provider callback with authorization code.",
)
async def callback(
    provider: str,
    session: DbSession,
    code: str = Query(..., description="Authorization code from provider"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    error: str | None = Query(None, description="Error from provider"),
    error_description: str | None = Query(None, description="Error description"),
) -> OAuthTokenResponse:
    """
    Handle OAuth callback from provider.
    
    Exchanges authorization code for tokens and creates/updates user.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_description or error,
        )
    
    try:
        oauth_provider = OAuthProvider(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )
    
    service = OAuthService(session)
    
    try:
        user, connection, is_new_user = await service.handle_callback(
            provider=oauth_provider,
            code=code,
            state=state,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    await session.commit()
    
    # Generate tokens
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
    )
    
    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
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
    provider: str,
    session: DbSession,
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    frontend_url: str = Query("http://localhost:5173", description="Frontend URL to redirect to"),
) -> RedirectResponse:
    """
    Handle OAuth callback and redirect to frontend with tokens.
    """
    if error:
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error={error}&error_description={error_description or ''}",
            status_code=302,
        )
    
    try:
        oauth_provider = OAuthProvider(provider.lower())
    except ValueError:
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error=invalid_provider",
            status_code=302,
        )
    
    service = OAuthService(session)
    
    try:
        user, connection, is_new_user = await service.handle_callback(
            provider=oauth_provider,
            code=code,
            state=state,
        )
        await session.commit()
        
        # Generate tokens
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
        )
        
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?access_token={access_token}&refresh_token={refresh_token}&is_new_user={is_new_user}",
            status_code=302,
        )
        
    except ValueError as e:
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error=auth_failed&error_description={str(e)}",
            status_code=302,
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
) -> list[OAuthConnectionResponse]:
    """
    List all OAuth connections for the current user.
    """
    service = OAuthService(session)
    
    connections = await service.get_user_connections(
        user_id=current_user.id,
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
    provider: str,
    session: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId = None,
    scope: str | None = None,
) -> OAuthAuthorizeResponse:
    """
    Start OAuth flow to link account to current user.
    """
    try:
        oauth_provider = OAuthProvider(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )
    
    service = OAuthService(session)
    
    scopes = scope.split() if scope else None
    
    auth_url, state = await service.initiate_oauth(
        provider=oauth_provider,
        tenant_id=tenant_id,
        scopes=scopes,
        linking_user_id=current_user.id,
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
) -> None:
    """
    Unlink OAuth account from current user.
    """
    service = OAuthService(session)
    
    try:
        success = await service.unlink_oauth_account(
            user_id=current_user.id,
            connection_id=connection_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth connection not found",
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
    current_user: CurrentUser,
    tenant_id: CurrentTenantId,
) -> list[SSOConfigResponse]:
    """
    List all SSO configurations for the tenant.
    
    Requires admin privileges.
    """
    # Check admin privileges
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can manage SSO configurations",
        )
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID is required for SSO configuration",
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
    current_user: CurrentUser,
    tenant_id: CurrentTenantId,
) -> SSOConfigResponse:
    """
    Create new SSO configuration.
    
    Requires admin privileges.
    """
    # Check admin privileges
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can manage SSO configurations",
        )
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID is required for SSO configuration",
        )
    
    try:
        provider = OAuthProvider(data.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {data.provider}",
        )
    
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
        {
            "provider": "discord",
            "name": "Discord",
            "icon": "discord",
            "available": bool(getattr(settings, "OAUTH_DISCORD_CLIENT_ID", "")),
        },
    ]
    
    # Add tenant SSO configs if available
    if tenant_id:
        service = OAuthService(session)
        sso_configs = await service.get_sso_config(tenant_id)
        
        for config in sso_configs:
            providers.append({
                "provider": config.provider.value,
                "name": config.name,
                "icon": config.provider.value,
                "available": config.is_enabled,
                "is_sso": True,
                "is_required": config.is_required,
            })
    
    # Add built-in providers
    for config in provider_configs:
        # Skip if there's an SSO config that overrides it
        if not any(p.get("provider") == config["provider"] for p in providers):
            providers.append(config)
    
    return providers
