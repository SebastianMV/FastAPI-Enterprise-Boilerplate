# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Cached Tenant Repository implementation.

Wraps SQLAlchemyTenantRepository with Redis caching for frequently
accessed tenant data. Tenants are very stable data that change rarely
but are queried on almost every request for RLS context.
"""

from datetime import UTC, datetime
from uuid import UUID

from app.config import settings
from app.domain.entities.tenant import Tenant, TenantSettings
from app.infrastructure.cache import CacheKeyBuilder, get_cache_service
from app.infrastructure.database.repositories.tenant_repository import (
    SQLAlchemyTenantRepository,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class CachedTenantRepository:
    """
    Repository wrapper that adds caching to tenant queries.

    Cache strategy:
    - get_by_id: Cache tenants by ID (most frequent)
    - get_by_slug: Cache tenants by slug (subdomain routing)
    - get_by_domain: Cache tenants by custom domain
    - Invalidate on update/delete

    Note: Tenants have the longest TTL since they change very rarely.
    """

    CACHE_PREFIX = "tenant"

    def __init__(self, base_repo: SQLAlchemyTenantRepository) -> None:
        self._repo = base_repo
        self._ttl = settings.CACHE_TENANT_TTL

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Get tenant by ID with caching."""
        cache = await get_cache_service()
        cache_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "id", tenant_id)

        # Try cache
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("cache_hit_tenant", tenant_id=str(tenant_id))
            return self._dict_to_tenant(cached)

        # Fetch from DB
        tenant = await self._repo.get_by_id(tenant_id)

        # Cache result
        if tenant:
            await cache.set(cache_key, self._tenant_to_dict(tenant), self._ttl)

        return tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Get tenant by slug with caching."""
        cache = await get_cache_service()
        cache_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "slug", slug)

        # Try cache
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("cache_hit_tenant_slug", slug=slug)
            return self._dict_to_tenant(cached)

        # Fetch from DB
        tenant = await self._repo.get_by_slug(slug)

        # Cache result
        if tenant:
            # Cache by slug AND by ID for cross-reference
            await cache.set(cache_key, self._tenant_to_dict(tenant), self._ttl)
            id_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "id", tenant.id)
            await cache.set(id_key, self._tenant_to_dict(tenant), self._ttl)

        return tenant

    async def get_by_domain(self, domain: str) -> Tenant | None:
        """Get tenant by custom domain with caching."""
        cache = await get_cache_service()
        cache_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "domain", domain)

        # Try cache
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("cache_hit_tenant_domain", domain=domain)
            return self._dict_to_tenant(cached)

        # Fetch from DB
        tenant = await self._repo.get_by_domain(domain)

        # Cache result
        if tenant:
            await cache.set(cache_key, self._tenant_to_dict(tenant), self._ttl)
            # Also cache by ID
            id_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "id", tenant.id)
            await cache.set(id_key, self._tenant_to_dict(tenant), self._ttl)

        return tenant

    async def create(self, tenant: Tenant) -> Tenant:
        """Create tenant (no cache to invalidate for new tenant)."""
        return await self._repo.create(tenant)

    async def update(self, tenant: Tenant) -> Tenant:
        """Update tenant and invalidate cache."""
        updated = await self._repo.update(tenant)
        await self._invalidate_tenant_cache(tenant)
        return updated

    async def delete(self, tenant_id: UUID) -> bool:
        """Delete tenant and invalidate cache."""
        tenant = await self._repo.get_by_id(tenant_id)
        result = await self._repo.delete(tenant_id)
        if tenant:
            await self._invalidate_tenant_cache(tenant)
        return result

    async def list_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> list[Tenant]:
        """List all tenants with caching."""
        cache = await get_cache_service()
        cache_key = CacheKeyBuilder.build(
            self.CACHE_PREFIX,
            "list",
            skip=skip,
            limit=limit,
            is_active=is_active,
        )

        # Try cache
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("cache_hit_tenant_list")
            return [self._dict_to_tenant(t) for t in cached]

        # Fetch from DB
        tenants = await self._repo.list_all(skip=skip, limit=limit, is_active=is_active)

        # Cache result
        await cache.set(
            cache_key,
            [self._tenant_to_dict(t) for t in tenants],
            self._ttl,
        )

        return tenants

    async def count(self, *, is_active: bool | None = None) -> int:
        """Count tenants (not cached - admin operation)."""
        return await self._repo.count(is_active=is_active)

    async def slug_exists(self, slug: str) -> bool:
        """Check if slug exists (not cached)."""
        return await self._repo.slug_exists(slug)

    async def domain_exists(self, domain: str) -> bool:
        """Check if domain exists (not cached)."""
        return await self._repo.domain_exists(domain)

    async def _invalidate_tenant_cache(self, tenant: Tenant) -> None:
        """Invalidate all cache entries for a tenant."""
        cache = await get_cache_service()

        # Invalidate by ID
        id_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "id", tenant.id)
        await cache.delete(id_key)

        # Invalidate by slug
        slug_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "slug", tenant.slug)
        await cache.delete(slug_key)

        # Invalidate by domain if exists
        if tenant.domain:
            domain_key = CacheKeyBuilder.build(
                self.CACHE_PREFIX, "domain", tenant.domain
            )
            await cache.delete(domain_key)

        # Invalidate list cache
        await cache.delete_pattern(f"{self.CACHE_PREFIX}:list:*")

    @staticmethod
    def _tenant_to_dict(tenant: Tenant) -> dict:
        """Convert Tenant to cacheable dict."""
        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "email": tenant.email,
            "phone": tenant.phone,
            "is_active": tenant.is_active,
            "is_verified": tenant.is_verified,
            "plan": tenant.plan,
            "plan_expires_at": (
                tenant.plan_expires_at.isoformat() if tenant.plan_expires_at else None
            ),
            "settings": tenant.settings.to_dict() if tenant.settings else {},
            "domain": tenant.domain,
            "timezone": tenant.timezone,
            "locale": tenant.locale,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
            "created_by": str(tenant.created_by) if tenant.created_by else None,
            "updated_by": str(tenant.updated_by) if tenant.updated_by else None,
            "is_deleted": tenant.is_deleted,
            "deleted_at": tenant.deleted_at.isoformat() if tenant.deleted_at else None,
            "deleted_by": str(tenant.deleted_by) if tenant.deleted_by else None,
        }

    @staticmethod
    def _dict_to_tenant(data: dict) -> Tenant:
        """Convert cached dict back to Tenant."""

        return Tenant(
            id=UUID(data["id"]),
            name=data["name"],
            slug=data["slug"],
            email=data.get("email"),
            phone=data.get("phone"),
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
            plan=data.get("plan", "free"),
            plan_expires_at=(
                datetime.fromisoformat(data["plan_expires_at"])
                if data.get("plan_expires_at")
                else None
            ),
            settings=TenantSettings.from_dict(data.get("settings", {})),
            domain=data.get("domain"),
            timezone=data.get("timezone", "UTC"),
            locale=data.get("locale", "en"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now(UTC)
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if data.get("updated_at")
                else datetime.now(UTC)
            ),
            created_by=UUID(data["created_by"]) if data.get("created_by") else None,
            updated_by=UUID(data["updated_by"]) if data.get("updated_by") else None,
            is_deleted=data.get("is_deleted", False),
            deleted_at=(
                datetime.fromisoformat(data["deleted_at"])
                if data.get("deleted_at")
                else None
            ),
            deleted_by=UUID(data["deleted_by"]) if data.get("deleted_by") else None,
        )


def get_cached_tenant_repository(
    base_repo: SQLAlchemyTenantRepository,
) -> CachedTenantRepository:
    """Factory function for CachedTenantRepository."""
    return CachedTenantRepository(base_repo)
