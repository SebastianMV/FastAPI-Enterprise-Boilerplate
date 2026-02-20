# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Cached Role Repository implementation.

Wraps SQLAlchemyRoleRepository with Redis caching for frequently
accessed role data. Roles are stable data that change rarely but
are queried frequently (on every authorization check).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.config import settings
from app.domain.entities.role import Role
from app.infrastructure.cache import CacheKeyBuilder, get_cache_service
from app.infrastructure.database.repositories.role_repository import (
    SQLAlchemyRoleRepository,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class CachedRoleRepository:
    """
    Repository wrapper that adds caching to role queries.

    Cache strategy:
    - get_by_id: Cache individual roles by ID
    - list: Cache role lists by tenant
    - get_user_roles: Cache user's roles
    - Invalidate on create/update/delete
    """

    CACHE_PREFIX = "role"

    def __init__(self, base_repo: SQLAlchemyRoleRepository) -> None:
        self._repo = base_repo
        self._ttl = settings.CACHE_ROLE_TTL

    async def get_by_id(self, role_id: UUID) -> Role | None:
        """Get role by ID with caching."""
        cache = await get_cache_service()
        cache_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "id", role_id)

        # Try cache
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("cache_hit_role", role_id=str(role_id))
            return self._dict_to_role(cached)

        # Fetch from DB
        role = await self._repo.get_by_id(role_id)

        # Cache result
        if role:
            await cache.set(cache_key, self._role_to_dict(role), self._ttl)

        return role

    async def get_by_name(self, name: str, tenant_id: UUID) -> Role | None:
        """Get role by name (not cached - less frequent)."""
        return await self._repo.get_by_name(name, tenant_id)

    async def create(self, role: Role) -> Role:
        """Create role and invalidate cache."""
        created = await self._repo.create(role)
        await self._invalidate_tenant_cache(role.tenant_id)
        return created

    async def update(self, role: Role) -> Role:
        """Update role and invalidate cache."""
        updated = await self._repo.update(role)
        await self._invalidate_role_cache(role.id, role.tenant_id)
        return updated

    async def delete(self, role_id: UUID) -> None:
        """Delete role and invalidate cache."""
        role = await self._repo.get_by_id(role_id)
        await self._repo.delete(role_id)
        if role:
            await self._invalidate_role_cache(role_id, role.tenant_id)

    async def count(
        self,
        *,
        tenant_id: UUID,
    ) -> int:
        """Count roles for tenant (not cached — cheap DB query)."""
        return await self._repo.count(tenant_id=tenant_id)

    async def list(
        self,
        *,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Role]:
        """List roles for tenant with caching."""
        cache = await get_cache_service()
        cache_key = CacheKeyBuilder.build(
            self.CACHE_PREFIX,
            "list",
            tenant_id,
            skip=skip,
            limit=limit,
        )

        # Try cache
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("cache_hit_roles_for_tenant", tenant_id=str(tenant_id))
            return [self._dict_to_role(r) for r in cached]

        # Fetch from DB
        roles = await self._repo.list(tenant_id=tenant_id, skip=skip, limit=limit)

        # Cache result
        await cache.set(
            cache_key,
            [self._role_to_dict(r) for r in roles],
            self._ttl,
        )

        return roles

    async def list_by_ids(self, role_ids: list[UUID]) -> list[Role]:  # type: ignore[valid-type]
        """Get multiple roles by IDs with caching."""
        if not role_ids:
            return []

        cache = await get_cache_service()
        roles: list[Role] = []
        missing_ids: list[UUID] = []

        # Check cache for each role
        for role_id in role_ids:  # type: ignore[attr-defined]
            cache_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "id", role_id)
            cached = await cache.get(cache_key)
            if cached:
                roles.append(self._dict_to_role(cached))
            else:
                missing_ids.append(role_id)

        # Fetch missing from DB
        if missing_ids:
            db_roles = await self._repo.list_by_ids(missing_ids)
            for role in db_roles:  # type: ignore[attr-defined]
                # Cache each role
                cache_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "id", role.id)
                await cache.set(cache_key, self._role_to_dict(role), self._ttl)
                roles.append(role)

        return roles

    async def get_user_roles(self, user_id: UUID) -> list[Role]:  # type: ignore[valid-type]
        """Get all roles assigned to a user with caching."""
        cache = await get_cache_service()
        cache_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "user", user_id)

        # Try cache
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("cache_hit_roles_for_user", user_id=str(user_id))
            return [self._dict_to_role(r) for r in cached]

        # Fetch from DB
        roles = await self._repo.get_user_roles(user_id)

        # Cache result (shorter TTL since user-role assignment changes more)
        await cache.set(
            cache_key,
            [self._role_to_dict(r) for r in roles],  # type: ignore[attr-defined]
            min(self._ttl, 60),  # Max 1 minute for user roles
        )

        return roles

    async def _invalidate_role_cache(
        self,
        role_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Invalidate cache for a specific role."""
        cache = await get_cache_service()

        # Delete specific role cache
        cache_key = CacheKeyBuilder.build(self.CACHE_PREFIX, "id", role_id)
        await cache.delete(cache_key)

        # Invalidate tenant list cache
        await self._invalidate_tenant_cache(tenant_id)

    async def _invalidate_tenant_cache(self, tenant_id: UUID) -> None:
        """Invalidate all role caches for a tenant."""
        cache = await get_cache_service()
        await cache.delete_pattern(f"{self.CACHE_PREFIX}:list:{tenant_id}:*")

    @staticmethod
    def _role_to_dict(role: Role) -> dict[str, Any]:
        """Convert Role to cacheable dict."""
        return {
            "id": str(role.id),
            "tenant_id": str(role.tenant_id),
            "name": role.name,
            "description": role.description,
            "permissions": role.permission_strings,
            "is_system": role.is_system,
            "created_at": role.created_at.isoformat() if role.created_at else None,
            "updated_at": role.updated_at.isoformat() if role.updated_at else None,
            "created_by": str(role.created_by) if role.created_by else None,
            "updated_by": str(role.updated_by) if role.updated_by else None,
            "is_deleted": role.is_deleted,
            "deleted_at": role.deleted_at.isoformat() if role.deleted_at else None,
        }

    @staticmethod
    def _dict_to_role(data: dict[str, Any]) -> Role:
        """Convert cached dict back to Role."""
        from datetime import UTC, datetime

        from app.domain.entities.role import Permission

        permissions = [
            Permission.from_string(p) for p in (data.get("permissions") or [])
        ]

        return Role(
            id=UUID(data["id"]),
            tenant_id=UUID(data["tenant_id"]),
            name=data["name"],
            description=data.get("description", ""),
            permissions=permissions,
            is_system=data.get("is_system", False),
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
        )


def get_cached_role_repository(
    base_repo: SQLAlchemyRoleRepository,
) -> CachedRoleRepository:
    """Factory function for CachedRoleRepository."""
    return CachedRoleRepository(base_repo)
