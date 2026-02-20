# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Repository port (interface) for OAuth/SSO configuration entity.

Defines the contract for OAuth provider configuration persistence.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class OAuthRepositoryPort(ABC):
    """
    Abstract repository for OAuth/SSO configuration.

    Implementations:
    - SQLAlchemyOAuthRepository (PostgreSQL)
    - InMemoryOAuthRepository (testing)
    """

    @abstractmethod
    async def get_by_provider(
        self, provider: str, tenant_id: UUID | None = None
    ) -> dict[str, Any] | None:
        """Get OAuth configuration for a given provider."""
        ...

    @abstractmethod
    async def list_providers(self, tenant_id: UUID | None = None) -> list[dict[str, Any]]:
        """List all configured OAuth providers."""
        ...

    @abstractmethod
    async def create(self, config: dict[str, Any]) -> dict[str, Any]:
        """Create a new OAuth provider configuration."""
        ...

    @abstractmethod
    async def update(self, provider: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an existing OAuth provider configuration."""
        ...

    @abstractmethod
    async def delete(self, provider: str, tenant_id: UUID | None = None) -> bool:
        """Delete an OAuth provider configuration."""
        ...
