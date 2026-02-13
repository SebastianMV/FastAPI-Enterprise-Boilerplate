# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Tenant management endpoints.

These endpoints are superuser-only for managing tenants (organizations).
Optimized with Redis caching for frequently accessed tenant data.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_superuser
from app.api.v1.schemas.tenants import (
    TenantActivateRequest,
    TenantCreate,
    TenantListResponse,
    TenantPlanUpdate,
    TenantResponse,
    TenantSettingsSchema,
    TenantUpdate,
    TenantVerifyRequest,
)
from app.domain.entities.tenant import Tenant, TenantSettings
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories.cached_tenant_repository import (
    CachedTenantRepository,
    get_cached_tenant_repository,
)
from app.infrastructure.database.repositories.tenant_repository import (
    SQLAlchemyTenantRepository,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


def get_tenant_repository(
    session: AsyncSession = Depends(get_db_session),
) -> CachedTenantRepository:
    """Dependency to get cached tenant repository."""
    base_repo = SQLAlchemyTenantRepository(session)
    return get_cached_tenant_repository(base_repo)


# =============================================================================
# CRUD ENDPOINTS (Superuser only)
# =============================================================================


@router.get(
    "",
    response_model=TenantListResponse,
    summary="List all tenants",
    description="List all tenants with pagination. Superuser only.",
)
async def list_tenants(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    is_active: bool | None = Query(default=None),
    _: UUID = Depends(require_superuser),
    repo: CachedTenantRepository = Depends(get_tenant_repository),
) -> TenantListResponse:
    """List all tenants."""
    tenants = await repo.list_all(skip=skip, limit=limit, is_active=is_active)
    total = await repo.count(is_active=is_active)

    return TenantListResponse(
        items=[_to_response(t) for t in tenants],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant",
    description="Create a new tenant (organization). Superuser only.",
)
async def create_tenant(
    data: TenantCreate,
    current_user_id: UUID = Depends(require_superuser),
    repo: SQLAlchemyTenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Create a new tenant."""
    # Check slug uniqueness
    if await repo.slug_exists(data.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SLUG_EXISTS",
                "message": "A tenant with this slug already exists",
            },
        )

    # Check domain uniqueness
    if data.domain and await repo.domain_exists(data.domain):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DOMAIN_EXISTS",
                "message": "A tenant with this domain already exists",
            },
        )

    # Create tenant entity
    settings = TenantSettings()
    if data.settings:
        settings = TenantSettings(
            enable_2fa=data.settings.enable_2fa,
            enable_api_keys=data.settings.enable_api_keys,
            enable_webhooks=data.settings.enable_webhooks,
            max_users=data.settings.max_users,
            max_api_keys_per_user=data.settings.max_api_keys_per_user,
            max_storage_mb=data.settings.max_storage_mb,
            primary_color=data.settings.primary_color,
            logo_url=data.settings.logo_url,
            password_min_length=data.settings.password_min_length,
            session_timeout_minutes=data.settings.session_timeout_minutes,
            require_email_verification=data.settings.require_email_verification,
        )

    tenant = Tenant(
        name=data.name,
        slug=data.slug,
        email=data.email,
        phone=data.phone,
        domain=data.domain,
        timezone=data.timezone,
        locale=data.locale,
        plan=data.plan,
        settings=settings,
        created_by=current_user_id,
        updated_by=current_user_id,
    )

    created = await repo.create(tenant)
    return _to_response(created)


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get tenant by ID",
    description="Get tenant details by ID. Superuser only.",
)
async def get_tenant(
    tenant_id: UUID,
    _: UUID = Depends(require_superuser),
    repo: SQLAlchemyTenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Get tenant by ID."""
    tenant = await repo.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TENANT_NOT_FOUND", "message": "Tenant not found"},
        )

    return _to_response(tenant)


@router.get(
    "/by-slug/{slug}",
    response_model=TenantResponse,
    summary="Get tenant by slug",
    description="Get tenant details by URL slug. Superuser only.",
)
async def get_tenant_by_slug(
    slug: str,
    _: UUID = Depends(require_superuser),
    repo: SQLAlchemyTenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Get tenant by slug."""
    tenant = await repo.get_by_slug(slug)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TENANT_NOT_FOUND", "message": "Tenant not found"},
        )

    return _to_response(tenant)


@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant",
    description="Update tenant details. Superuser only.",
)
async def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    current_user_id: UUID = Depends(require_superuser),
    repo: SQLAlchemyTenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Update tenant."""
    tenant = await repo.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TENANT_NOT_FOUND", "message": "Tenant not found"},
        )

    # Check slug uniqueness
    if data.slug and data.slug != tenant.slug:
        if await repo.slug_exists(data.slug, exclude_id=tenant_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "SLUG_EXISTS",
                    "message": "A tenant with this slug already exists",
                },
            )
        tenant.slug = data.slug

    # Check domain uniqueness
    if data.domain and data.domain != tenant.domain:
        if await repo.domain_exists(data.domain, exclude_id=tenant_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DOMAIN_EXISTS",
                    "message": "A tenant with this domain already exists",
                },
            )
        tenant.domain = data.domain

    # Update fields
    if data.name is not None:
        tenant.name = data.name
    if data.email is not None:
        tenant.email = data.email
    if data.phone is not None:
        tenant.phone = data.phone
    if data.timezone is not None:
        tenant.timezone = data.timezone
    if data.locale is not None:
        tenant.locale = data.locale
    if data.plan is not None:
        tenant.plan = data.plan
    if data.settings is not None:
        tenant.settings = TenantSettings(
            enable_2fa=data.settings.enable_2fa,
            enable_api_keys=data.settings.enable_api_keys,
            enable_webhooks=data.settings.enable_webhooks,
            max_users=data.settings.max_users,
            max_api_keys_per_user=data.settings.max_api_keys_per_user,
            max_storage_mb=data.settings.max_storage_mb,
            primary_color=data.settings.primary_color,
            logo_url=data.settings.logo_url,
            password_min_length=data.settings.password_min_length,
            session_timeout_minutes=data.settings.session_timeout_minutes,
            require_email_verification=data.settings.require_email_verification,
        )

    tenant.mark_updated(by_user=current_user_id)

    updated = await repo.update(tenant)
    return _to_response(updated)


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant",
    description="Hard delete a tenant. WARNING: Deletes all tenant data. Superuser only.",
)
async def delete_tenant(
    tenant_id: UUID,
    _: UUID = Depends(require_superuser),
    repo: SQLAlchemyTenantRepository = Depends(get_tenant_repository),
) -> None:
    """Delete tenant."""
    deleted = await repo.delete(tenant_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TENANT_NOT_FOUND", "message": "Tenant not found"},
        )


# =============================================================================
# MANAGEMENT ENDPOINTS
# =============================================================================


@router.post(
    "/{tenant_id}/activate",
    response_model=TenantResponse,
    summary="Activate/Deactivate tenant",
    description="Activate or deactivate a tenant. Superuser only.",
)
async def set_tenant_active(
    tenant_id: UUID,
    data: TenantActivateRequest,
    current_user_id: UUID = Depends(require_superuser),
    repo: SQLAlchemyTenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Activate or deactivate tenant."""
    tenant = await repo.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TENANT_NOT_FOUND", "message": "Tenant not found"},
        )

    if data.is_active:
        tenant.activate()
    else:
        tenant.deactivate()

    tenant.mark_updated(by_user=current_user_id)

    updated = await repo.update(tenant)
    return _to_response(updated)


@router.post(
    "/{tenant_id}/verify",
    response_model=TenantResponse,
    summary="Verify tenant",
    description="Mark tenant as verified. Superuser only.",
)
async def set_tenant_verified(
    tenant_id: UUID,
    data: TenantVerifyRequest,
    current_user_id: UUID = Depends(require_superuser),
    repo: SQLAlchemyTenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Verify tenant."""
    tenant = await repo.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TENANT_NOT_FOUND", "message": "Tenant not found"},
        )

    if data.is_verified:
        tenant.verify()

    tenant.mark_updated(by_user=current_user_id)

    updated = await repo.update(tenant)
    return _to_response(updated)


@router.post(
    "/{tenant_id}/plan",
    response_model=TenantResponse,
    summary="Update tenant plan",
    description="Update tenant subscription plan. Superuser only.",
)
async def update_tenant_plan(
    tenant_id: UUID,
    data: TenantPlanUpdate,
    current_user_id: UUID = Depends(require_superuser),
    repo: SQLAlchemyTenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Update tenant plan."""
    tenant = await repo.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TENANT_NOT_FOUND", "message": "Tenant not found"},
        )

    tenant.update_plan(data.plan, data.expires_at)
    tenant.mark_updated(by_user=current_user_id)

    updated = await repo.update(tenant)
    return _to_response(updated)


# =============================================================================
# HELPERS
# =============================================================================


def _to_response(tenant: Tenant) -> TenantResponse:
    """Convert tenant entity to response schema."""
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        email=tenant.email,
        phone=tenant.phone,
        is_active=tenant.is_active,
        is_verified=tenant.is_verified,
        plan=tenant.plan,
        plan_expires_at=tenant.plan_expires_at,
        settings=TenantSettingsSchema(
            enable_2fa=tenant.settings.enable_2fa,
            enable_api_keys=tenant.settings.enable_api_keys,
            enable_webhooks=tenant.settings.enable_webhooks,
            max_users=tenant.settings.max_users,
            max_api_keys_per_user=tenant.settings.max_api_keys_per_user,
            max_storage_mb=tenant.settings.max_storage_mb,
            primary_color=tenant.settings.primary_color,
            logo_url=tenant.settings.logo_url,
            password_min_length=tenant.settings.password_min_length,
            session_timeout_minutes=tenant.settings.session_timeout_minutes,
            require_email_verification=tenant.settings.require_email_verification,
        ),
        domain=tenant.domain,
        timezone=tenant.timezone,
        locale=tenant.locale,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )
