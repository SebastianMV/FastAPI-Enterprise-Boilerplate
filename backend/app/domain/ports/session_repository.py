# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Repository port (interface) for Session entity.

Defines the contract for session persistence (login sessions, refresh tokens).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID


class SessionRepositoryPort(ABC):
    """
    Abstract repository for user sessions.

    Implementations:
    - SQLAlchemySessionRepository (production)
    - InMemorySessionRepository (testing)
    """

    @abstractmethod
    async def create(self, user_session: Any) -> Any:
        """Create a new session and return the persisted entity."""
        ...

    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> Any | None:
        """Get session by its UUID."""
        ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> Any | None:
        """Get session by token hash."""
        ...

    @abstractmethod
    async def get_user_sessions(
        self,
        user_id: UUID,
        *,
        active_only: bool = True,
        tenant_id: UUID | None = None,
    ) -> list[Any]:
        """List all sessions for a user, optionally scoped to tenant."""
        ...

    @abstractmethod
    async def revoke(self, session_id: UUID) -> bool:
        """Revoke (deactivate) a session. Returns True if revoked."""
        ...

    @abstractmethod
    async def revoke_all(self, user_id: UUID, *, tenant_id: UUID | None = None) -> int:
        """Revoke all sessions for a user, optionally scoped to tenant. Returns count revoked."""
        ...

    @abstractmethod
    async def revoke_all_except(
        self, user_id: UUID, current_session_id: UUID, *, tenant_id: UUID | None = None
    ) -> int:
        """Revoke all sessions except the given one, optionally scoped to tenant. Returns count revoked."""
        ...

    @abstractmethod
    async def update_activity(
        self,
        session_id: UUID,
        *,
        ip_address: str | None = None,
    ) -> bool:
        """Update session last_activity timestamp."""
        ...

    @abstractmethod
    async def cleanup_old_sessions(self, older_than: datetime) -> int:
        """Remove sessions older than given datetime. Returns count deleted."""
        ...
