# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""SQLAlchemy implementation of Tenant repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.tenant import Tenant, TenantSettings
from app.domain.ports.tenant_repository import TenantRepositoryPort
from app.infrastructure.database.models.tenant import TenantModel


class SQLAlchemyTenantRepository(TenantRepositoryPort):
    """
    SQLAlchemy implementation of TenantRepositoryPort.

    Note: Tenant queries bypass RLS since tenants are the root
    of the multi-tenant hierarchy.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: TenantModel) -> Tenant:
        """Convert SQLAlchemy model to domain entity."""
        return Tenant(
            id=model.id,
            name=model.name,
            slug=model.slug,
            email=model.email,
            phone=model.phone,
            is_active=model.is_active,
            is_verified=model.is_verified,
            plan=model.plan,
            plan_expires_at=model.plan_expires_at,
            settings=TenantSettings.from_dict(model.settings or {}),
            domain=model.domain,
            timezone=model.timezone,
            locale=model.locale,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            updated_by=model.updated_by,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            deleted_by=model.deleted_by,
        )

    def _to_model(self, entity: Tenant) -> TenantModel:
        """Convert domain entity to SQLAlchemy model."""
        return TenantModel(
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            email=entity.email,
            phone=entity.phone,
            is_active=entity.is_active,
            is_verified=entity.is_verified,
            plan=entity.plan,
            plan_expires_at=entity.plan_expires_at,
            settings=entity.settings.to_dict(),
            domain=entity.domain,
            timezone=entity.timezone,
            locale=entity.locale,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            deleted_by=entity.deleted_by,
        )

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Get tenant by ID."""
        stmt = select(TenantModel).where(
            TenantModel.id == tenant_id,
            TenantModel.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Get tenant by URL slug."""
        stmt = select(TenantModel).where(
            TenantModel.slug == slug,
            TenantModel.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def get_by_domain(self, domain: str) -> Tenant | None:
        """Get tenant by custom domain."""
        stmt = select(TenantModel).where(
            TenantModel.domain == domain,
            TenantModel.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def create(self, tenant: Tenant) -> Tenant:
        """Create a new tenant."""
        model = self._to_model(tenant)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, tenant: Tenant) -> Tenant:
        """Update an existing tenant."""
        stmt = select(TenantModel).where(TenantModel.id == tenant.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError("Tenant not found")

        # Update fields
        model.name = tenant.name
        model.slug = tenant.slug
        model.email = tenant.email
        model.phone = tenant.phone
        model.is_active = tenant.is_active
        model.is_verified = tenant.is_verified
        model.plan = tenant.plan
        model.plan_expires_at = tenant.plan_expires_at
        model.settings = tenant.settings.to_dict()
        model.domain = tenant.domain
        model.timezone = tenant.timezone
        model.locale = tenant.locale
        model.updated_by = tenant.updated_by

        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def delete(self, tenant_id: UUID) -> bool:
        """Hard delete a tenant."""
        stmt = select(TenantModel).where(TenantModel.id == tenant_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self.session.delete(model)
        await self.session.flush()
        return True

    async def list_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> list[Tenant]:
        """List all tenants with pagination."""
        stmt = select(TenantModel).where(TenantModel.is_deleted.is_(False))

        if is_active is not None:
            stmt = stmt.where(TenantModel.is_active.is_(is_active))

        stmt = stmt.offset(skip).limit(limit).order_by(TenantModel.created_at.desc())

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models]

    async def count(self, *, is_active: bool | None = None) -> int:
        """Count total tenants."""
        stmt = select(func.count(TenantModel.id)).where(
            TenantModel.is_deleted.is_(False)
        )

        if is_active is not None:
            stmt = stmt.where(TenantModel.is_active.is_(is_active))

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def slug_exists(self, slug: str, exclude_id: UUID | None = None) -> bool:
        """Check if slug already exists."""
        stmt = select(func.count(TenantModel.id)).where(
            TenantModel.slug == slug,
            TenantModel.is_deleted.is_(False),
        )

        if exclude_id:
            stmt = stmt.where(TenantModel.id != exclude_id)

        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def domain_exists(self, domain: str, exclude_id: UUID | None = None) -> bool:
        """Check if domain already exists."""
        stmt = select(func.count(TenantModel.id)).where(
            TenantModel.domain == domain,
            TenantModel.is_deleted.is_(False),
        )

        if exclude_id:
            stmt = stmt.where(TenantModel.id != exclude_id)

        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def get_default_tenant(self) -> Tenant | None:
        """
        Get the default tenant for new user registration.

        Returns the first tenant with slug='default', or the first active tenant.
        """
        # First try to find a tenant with slug='default'
        stmt = select(TenantModel).where(
            TenantModel.slug == "default",
            TenantModel.is_deleted.is_(False),
            TenantModel.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)

        # Fallback: get any active tenant
        stmt = (
            select(TenantModel)
            .where(
                TenantModel.is_deleted.is_(False),
                TenantModel.is_active.is_(True),
            )
            .order_by(TenantModel.created_at.asc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None
