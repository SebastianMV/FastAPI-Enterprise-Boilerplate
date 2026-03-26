# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Repository port (interface) for Notification entity.

Defines the contract for notification persistence and retrieval.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class NotificationRepositoryPort(ABC):
    """
    Abstract repository for Notification entity.

    Implementations:
    - SQLAlchemyNotificationRepository (PostgreSQL)
    - InMemoryNotificationRepository (testing)
    """

    @abstractmethod
    async def create(self, notification: dict[str, Any]) -> dict[str, Any]:
        """Create a new notification."""
        ...

    @abstractmethod
    async def get_by_id(self, notification_id: UUID) -> dict[str, Any] | None:
        """Get notification by ID."""
        ...

    @abstractmethod
    async def list_for_user(
        self,
        user_id: UUID,
        *,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List notifications for a user."""
        ...

    @abstractmethod
    async def mark_as_read(self, notification_id: UUID) -> bool:
        """Mark a single notification as read."""
        ...

    @abstractmethod
    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user. Returns count updated."""
        ...

    @abstractmethod
    async def delete(self, notification_id: UUID) -> bool:
        """Delete a notification."""
        ...

    @abstractmethod
    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for a user."""
        ...
