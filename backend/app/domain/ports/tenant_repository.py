# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Port (interface) for Tenant repository."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.tenant import Tenant


class TenantRepositoryPort(ABC):
    """
    Abstract interface for Tenant repository.

    Infrastructure layer must implement this interface.
    Domain/Application layers depend only on this abstraction.
    """

    @abstractmethod
    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        """
        Get tenant by ID.

        Args:
            tenant_id: Unique identifier

        Returns:
            Tenant if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Tenant | None:
        """
        Get tenant by URL slug.

        Args:
            slug: URL-friendly identifier

        Returns:
            Tenant if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_domain(self, domain: str) -> Tenant | None:
        """
        Get tenant by custom domain.

        Args:
            domain: Custom domain name

        Returns:
            Tenant if found, None otherwise
        """
        ...

    @abstractmethod
    async def create(self, tenant: Tenant) -> Tenant:
        """
        Create a new tenant.

        Args:
            tenant: Tenant entity to create

        Returns:
            Created tenant with ID assigned
        """
        ...

    @abstractmethod
    async def update(self, tenant: Tenant) -> Tenant:
        """
        Update an existing tenant.

        Args:
            tenant: Tenant entity with updated data

        Returns:
            Updated tenant
        """
        ...

    @abstractmethod
    async def delete(self, tenant_id: UUID) -> bool:
        """
        Hard delete a tenant.

        Warning: This deletes all tenant data. Use with caution.

        Args:
            tenant_id: Tenant to delete

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def list_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> list[Tenant]:
        """
        List all tenants with pagination.

        Note: This bypasses RLS and should only be used
        by superadmin operations.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            is_active: Filter by active status

        Returns:
            List of tenants
        """
        ...

    @abstractmethod
    async def count(self, *, is_active: bool | None = None) -> int:
        """
        Count total tenants.

        Args:
            is_active: Filter by active status

        Returns:
            Total count
        """
        ...

    @abstractmethod
    async def slug_exists(self, slug: str, exclude_id: UUID | None = None) -> bool:
        """
        Check if slug already exists.

        Args:
            slug: Slug to check
            exclude_id: Tenant ID to exclude (for updates)

        Returns:
            True if slug exists
        """
        ...

    @abstractmethod
    async def domain_exists(self, domain: str, exclude_id: UUID | None = None) -> bool:
        """
        Check if domain already exists.

        Args:
            domain: Domain to check
            exclude_id: Tenant ID to exclude (for updates)

        Returns:
            True if domain exists
        """
        ...

    @abstractmethod
    async def get_default_tenant(self) -> Tenant | None:
        """
        Get the default tenant for new user registration.

        Returns:
            Default tenant if found, None otherwise
        """
        ...
