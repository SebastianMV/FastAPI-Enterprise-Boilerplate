# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Notification service for managing user notifications.

Provides business logic for:
- Creating notifications
- Real-time delivery via WebSocket
- Batch operations (mark read, delete)
"""

import html as html_mod
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)
from app.domain.ports.websocket import MessageType, WebSocketMessage, WebSocketPort
from app.infrastructure.database.models.notification import NotificationModel
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """
    Service for managing notifications.

    Handles notification creation, delivery, and lifecycle management.

    # TODO: Extract NotificationRepository to comply with hexagonal architecture.
    # Currently uses direct SQLAlchemy queries for pragmatic reasons.
    """

    def __init__(
        self,
        session: AsyncSession,
        ws_manager: WebSocketPort | None = None,
    ) -> None:
        """
        Initialize the notification service.

        Args:
            session: Database session
            ws_manager: WebSocket manager for real-time delivery
        """
        self._session = session
        self._ws_manager = ws_manager

    async def create_notification(
        self,
        user_id: UUID,
        type: NotificationType,
        title: str,
        message: str,
        *,
        tenant_id: UUID | None = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        category: str | None = None,
        metadata: dict | None = None,
        action_url: str | None = None,
        channels: list[NotificationChannel] | None = None,
        expires_at: datetime | None = None,
        group_key: str | None = None,
    ) -> Notification:
        """
        Create and deliver a notification.

        Args:
            user_id: Target user ID
            type: Notification type
            title: Short title
            message: Full message
            tenant_id: Optional tenant ID
            priority: Priority level
            category: Custom category
            metadata: Additional data
            action_url: Click action URL
            channels: Delivery channels
            expires_at: Expiration time
            group_key: Grouping key

        Returns:
            Created notification entity
        """
        notification_id = uuid4()
        now = datetime.now(UTC)
        channels = channels or [NotificationChannel.IN_APP]

        # Create database record
        notification_model = NotificationModel(
            id=notification_id,
            tenant_id=tenant_id,
            user_id=user_id,
            type=type.value,
            title=title,
            message=message,
            metadata=metadata or {},
            priority=priority.value,
            category=category,
            channels=[c.value for c in channels],
            delivery_status={},
            action_url=action_url,
            expires_at=expires_at,
            group_key=group_key,
            created_at=now,
            updated_at=now,
        )

        self._session.add(notification_model)
        await self._session.flush()

        notification = Notification(
            id=notification_id,
            tenant_id=tenant_id,  # type: ignore[arg-type]
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            metadata=metadata or {},
            priority=priority,
            category=category,
            channels=channels,
            action_url=action_url,
            expires_at=expires_at,
            group_key=group_key,
            created_at=now,
            updated_at=now,
        )

        # Deliver via WebSocket if available
        if NotificationChannel.IN_APP in channels and self._ws_manager:
            try:
                await self._deliver_via_websocket(notification)
            except Exception:
                logger.warning(
                    "websocket_delivery_failed",
                    notification_id=str(notification.id),
                    user_id=str(user_id),
                    exc_info=True,
                )

        return notification

    async def _deliver_via_websocket(self, notification: Notification) -> None:
        """Deliver notification via WebSocket."""
        if not self._ws_manager:
            return

        ws_message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload=notification.to_websocket_payload(),
        )

        sent = await self._ws_manager.send_to_user(notification.user_id, ws_message)

        if sent > 0:
            notification.mark_delivered(NotificationChannel.IN_APP)

            # Update delivery status in DB
            await self._session.execute(
                update(NotificationModel)
                .where(NotificationModel.id == notification.id)
                .values(delivery_status=notification.delivery_status)
            )

    async def get_notification(
        self,
        notification_id: UUID,
        user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> Notification | None:
        """
        Get a notification by ID.

        Args:
            notification_id: Notification ID
            user_id: User ID (for access control)
            tenant_id: Optional tenant ID for defense-in-depth isolation

        Returns:
            Notification entity or None
        """
        conditions = [
            NotificationModel.id == notification_id,
            NotificationModel.user_id == user_id,
            NotificationModel.is_deleted.is_(False),
        ]
        if tenant_id is not None:
            conditions.append(NotificationModel.tenant_id == tenant_id)
        stmt = select(NotificationModel).where(*conditions)

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def get_user_notifications(
        self,
        user_id: UUID,
        *,
        unread_only: bool = False,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
        tenant_id: UUID | None = None,
    ) -> list[Notification]:
        """
        Get notifications for a user.

        Args:
            user_id: User ID
            unread_only: Filter to unread only
            category: Filter by category
            limit: Max results
            offset: Pagination offset
            tenant_id: Optional tenant ID for defense-in-depth isolation

        Returns:
            List of notifications
        """
        conditions = [
            NotificationModel.user_id == user_id,
            NotificationModel.is_deleted.is_(False),
        ]
        if tenant_id is not None:
            conditions.append(NotificationModel.tenant_id == tenant_id)
        stmt = select(NotificationModel).where(*conditions)

        if unread_only:
            stmt = stmt.where(NotificationModel.is_read.is_(False))

        if category:
            stmt = stmt.where(NotificationModel.category == category)

        stmt = stmt.order_by(NotificationModel.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models]

    async def get_unread_count(
        self,
        user_id: UUID,
        category: str | None = None,
        tenant_id: UUID | None = None,
    ) -> int:
        """
        Get count of unread notifications.

        Args:
            user_id: User ID
            category: Optional category filter
            tenant_id: Optional tenant ID for defense-in-depth isolation

        Returns:
            Count of unread notifications
        """
        from sqlalchemy import func

        conditions = [
            NotificationModel.user_id == user_id,
            NotificationModel.is_read.is_(False),
            NotificationModel.is_deleted.is_(False),
        ]
        if tenant_id is not None:
            conditions.append(NotificationModel.tenant_id == tenant_id)
        stmt = select(func.count(NotificationModel.id)).where(*conditions)

        if category:
            stmt = stmt.where(NotificationModel.category == category)

        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def mark_as_read(
        self,
        notification_id: UUID,
        user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID
            user_id: User ID
            tenant_id: Optional tenant ID for defense-in-depth isolation

        Returns:
            True if updated
        """
        now = datetime.now(UTC)

        conditions = [
            NotificationModel.id == notification_id,
            NotificationModel.user_id == user_id,
            NotificationModel.is_read.is_(False),
        ]
        if tenant_id is not None:
            conditions.append(NotificationModel.tenant_id == tenant_id)

        result = await self._session.execute(
            update(NotificationModel)
            .where(*conditions)
            .values(is_read=True, read_at=now, updated_at=now)
        )

        return result.rowcount > 0  # type: ignore

    async def mark_all_as_read(
        self,
        user_id: UUID,
        category: str | None = None,
        tenant_id: UUID | None = None,
    ) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User ID
            category: Optional category filter
            tenant_id: Optional tenant ID for defense-in-depth isolation

        Returns:
            Number of notifications marked
        """
        now = datetime.now(UTC)

        conditions = [
            NotificationModel.user_id == user_id,
            NotificationModel.is_read.is_(False),
            NotificationModel.is_deleted.is_(False),
        ]
        if tenant_id is not None:
            conditions.append(NotificationModel.tenant_id == tenant_id)

        stmt = (
            update(NotificationModel)
            .where(*conditions)
            .values(is_read=True, read_at=now, updated_at=now)
        )

        if category:
            stmt = stmt.where(NotificationModel.category == category)

        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore

    async def delete_notification(
        self,
        notification_id: UUID,
        user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> bool:
        """
        Soft delete a notification.

        Args:
            notification_id: Notification ID
            user_id: User ID
            tenant_id: Optional tenant ID for defense-in-depth isolation

        Returns:
            True if deleted
        """
        now = datetime.now(UTC)

        conditions = [
            NotificationModel.id == notification_id,
            NotificationModel.user_id == user_id,
            NotificationModel.is_deleted.is_(False),
        ]
        if tenant_id is not None:
            conditions.append(NotificationModel.tenant_id == tenant_id)

        result = await self._session.execute(
            update(NotificationModel)
            .where(*conditions)
            .values(is_deleted=True, deleted_at=now, updated_at=now)
        )

        return result.rowcount > 0  # type: ignore

    async def delete_all_read(
        self,
        user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> int:
        """
        Soft delete all read notifications.

        Args:
            user_id: User ID
            tenant_id: Optional tenant ID for defense-in-depth isolation

        Returns:
            Number deleted
        """
        now = datetime.now(UTC)

        conditions = [
            NotificationModel.user_id == user_id,
            NotificationModel.is_read.is_(True),
            NotificationModel.is_deleted.is_(False),
        ]
        if tenant_id is not None:
            conditions.append(NotificationModel.tenant_id == tenant_id)

        result = await self._session.execute(
            update(NotificationModel)
            .where(*conditions)
            .values(is_deleted=True, deleted_at=now, updated_at=now)
        )

        return result.rowcount  # type: ignore

    # =========================================
    # Convenience methods for common notifications
    # =========================================

    async def notify_welcome(
        self,
        user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> Notification:
        """Send welcome notification to new user."""
        return await self.create_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            type=NotificationType.WELCOME,
            title="notification.welcome.title",
            message="notification.welcome.message",
            priority=NotificationPriority.NORMAL,
            action_url="/getting-started",
        )

    async def notify_password_changed(
        self,
        user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> Notification:
        """Send password change notification."""
        return await self.create_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            type=NotificationType.PASSWORD_CHANGED,
            title="notification.passwordChanged.title",
            message="notification.passwordChanged.message",
            priority=NotificationPriority.HIGH,
            category="security",
        )

    async def notify_login_alert(
        self,
        user_id: UUID,
        ip_address: str,
        location: str | None = None,
        tenant_id: UUID | None = None,
    ) -> Notification:
        """Send login alert notification."""
        safe_ip = html_mod.escape(ip_address)
        safe_location = html_mod.escape(location) if location else None
        return await self.create_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            type=NotificationType.LOGIN_ALERT,
            title="notification.loginAlert.title",
            message="notification.loginAlert.message",
            priority=NotificationPriority.HIGH,
            category="security",
            metadata={"ip_address": safe_ip, "location": safe_location},
        )

    async def notify_mention(
        self,
        user_id: UUID,
        mentioned_by: str,
        context: str,
        action_url: str,
        tenant_id: UUID | None = None,
    ) -> Notification:
        """Send mention notification."""
        safe_mentioned_by = html_mod.escape(mentioned_by)
        safe_context = html_mod.escape(context)
        return await self.create_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            type=NotificationType.MENTION,
            title="notification.mention.title",
            message="notification.mention.message",
            metadata={"mentioned_by": safe_mentioned_by, "context": safe_context},
            priority=NotificationPriority.NORMAL,
            action_url=action_url,
            group_key=f"mentions:{user_id}",
        )

    def _to_entity(self, model: NotificationModel) -> Notification:
        """Convert NotificationModel to Notification entity."""
        return Notification(
            id=UUID(str(model.id)),
            tenant_id=UUID(str(model.tenant_id)) if model.tenant_id else None,
            user_id=UUID(str(model.user_id)),
            type=NotificationType(model.type),
            title=model.title,
            message=model.message,
            metadata=model.metadata,
            priority=NotificationPriority(model.priority),
            category=model.category,
            channels=[NotificationChannel(c) for c in model.channels],
            delivery_status=model.delivery_status,
            is_read=model.is_read,
            read_at=model.read_at,
            expires_at=model.expires_at,
            group_key=model.group_key,
            action_url=model.action_url,
            action_clicked=model.action_clicked,
            action_clicked_at=model.action_clicked_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
