# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Repository port (interface) for API Key entity.

Defines the contract for API key persistence and validation.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class APIKeyRepositoryPort(ABC):
    """
    Abstract repository for API Key entity.

    Implementations:
    - SQLAlchemyAPIKeyRepository (PostgreSQL)
    - InMemoryAPIKeyRepository (testing)
    """

    @abstractmethod
    async def create(self, api_key: dict[str, Any]) -> dict[str, Any]:
        """Create a new API key record."""
        ...

    @abstractmethod
    async def get_by_id(self, key_id: UUID) -> dict[str, Any] | None:
        """Get API key by ID."""
        ...

    @abstractmethod
    async def get_by_key_hash(self, key_hash: str) -> dict[str, Any] | None:
        """Look up an API key by its hashed value."""
        ...

    @abstractmethod
    async def list_for_user(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List all API keys for a user."""
        ...

    @abstractmethod
    async def update(self, key_id: UUID, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an API key's metadata (name, scopes, active status)."""
        ...

    @abstractmethod
    async def delete(self, key_id: UUID) -> bool:
        """Delete (revoke) an API key."""
        ...

    @abstractmethod
    async def record_usage(self, key_id: UUID) -> None:
        """Record that the API key was used (last_used_at)."""
        ...
