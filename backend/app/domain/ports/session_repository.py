# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Repository port (interface) for Session entity.

Defines the contract for session persistence (login sessions, refresh tokens).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class SessionRepositoryPort(ABC):
    """
    Abstract repository for user sessions.

    Implementations:
    - Redis-based session store (production)
    - InMemorySessionRepository (testing)
    """

    @abstractmethod
    async def create(
        self,
        user_id: UUID,
        jti: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        expires_at: datetime | None = None,
    ) -> str:
        """Create a new session and return its identifier."""
        ...

    @abstractmethod
    async def get(self, session_id: str) -> dict | None:
        """Get session data by session identifier."""
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete (invalidate) a session. Returns True if deleted."""
        ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: UUID) -> int:
        """Delete all sessions for a user. Returns count deleted."""
        ...

    @abstractmethod
    async def list_for_user(self, user_id: UUID) -> list[dict]:
        """List all active sessions for a user."""
        ...
