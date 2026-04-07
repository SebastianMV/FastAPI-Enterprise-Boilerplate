# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Notifications REST API endpoints.

Provides endpoints for:
- Notification listing and management
- Mark as read/unread
- Delete notifications
"""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentTenantId, CurrentUser, require_permission
from app.api.v1.schemas.notifications import (
    MarkReadRequest,
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.models.notification import NotificationModel
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/notifications")

NotificationsReader = Annotated[
    UUID, Depends(require_permission("notifications", "read"))
]
NotificationsWriter = Annotated[
    UUID, Depends(require_permission("notifications", "write"))
]


# ===========================================
# Endpoints
# ===========================================


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: CurrentUser,
    _current_user_id: NotificationsReader,
    tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    """List user's notifications."""
    # Build query
    query = select(NotificationModel).where(
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_deleted.is_(False),
    )

    if tenant_id:
        query = query.where(NotificationModel.tenant_id == tenant_id)

    if unread_only:
        query = query.where(NotificationModel.read_at.is_(None))

    offset = (page - 1) * page_size
    query = (
        query.order_by(NotificationModel.created_at.desc())
        .limit(page_size)
        .offset(offset)
    )

    result = await session.execute(query)
    notifications = result.scalars().all()

    # Count total
    count_query = select(func.count(NotificationModel.id)).where(
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_deleted.is_(False),
    )
    if tenant_id:
        count_query = count_query.where(NotificationModel.tenant_id == tenant_id)
    if unread_only:
        count_query = count_query.where(NotificationModel.read_at.is_(None))

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Count unread
    unread_query = select(func.count(NotificationModel.id)).where(
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_deleted.is_(False),
        NotificationModel.read_at.is_(None),
    )
    if tenant_id:
        unread_query = unread_query.where(NotificationModel.tenant_id == tenant_id)
    unread_result = await session.execute(unread_query)
    unread_count = unread_result.scalar() or 0

    pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return NotificationListResponse(
        items=[
            NotificationResponse(
                id=n.id,
                type=n.type,
                title=n.title,
                message=n.message,
                priority=n.priority,
                data=n.extra_data,
                action_url=n.action_url,
                is_read=n.read_at is not None,
                read_at=n.read_at,
                created_at=n.created_at,
            )
            for n in notifications
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        unread_count=unread_count,
    )


@router.get("/unread/count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: CurrentUser,
    _current_user_id: NotificationsReader,
    tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
) -> UnreadCountResponse:
    """Get count of unread notifications."""
    query = select(func.count(NotificationModel.id)).where(
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_deleted.is_(False),
        NotificationModel.read_at.is_(None),
    )

    if tenant_id:
        query = query.where(NotificationModel.tenant_id == tenant_id)

    result = await session.execute(query)
    count = result.scalar() or 0

    return UnreadCountResponse(count=count)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    current_user: CurrentUser,
    _current_user_id: NotificationsReader,
    tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
) -> NotificationResponse:
    """Get a specific notification."""
    query = select(NotificationModel).where(
        NotificationModel.id == notification_id,
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_deleted.is_(False),
    )

    if tenant_id:
        query = query.where(NotificationModel.tenant_id == tenant_id)

    result = await session.execute(query)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOTIFICATION_NOT_FOUND",
                "message": "Notification not found",
            },
        )

    return NotificationResponse(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        priority=notification.priority,
        data=notification.extra_data,
        action_url=notification.action_url,
        is_read=notification.read_at is not None,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_as_read(
    request: MarkReadRequest,
    current_user: CurrentUser,
    _current_user_id: NotificationsWriter,
    tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Mark notifications as read."""

    stmt = (
        update(NotificationModel)
        .where(
            NotificationModel.id.in_(request.notification_ids),
            NotificationModel.user_id == current_user.id,
            NotificationModel.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )

    if tenant_id:
        stmt = stmt.where(NotificationModel.tenant_id == tenant_id)

    await session.execute(stmt)
    await session.commit()


@router.post("/read/all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_as_read(
    current_user: CurrentUser,
    _current_user_id: NotificationsWriter,
    tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Mark all notifications as read."""

    stmt = (
        update(NotificationModel)
        .where(
            NotificationModel.user_id == current_user.id,
            NotificationModel.read_at.is_(None),
            NotificationModel.is_deleted.is_(False),
        )
        .values(read_at=datetime.now(UTC))
    )

    if tenant_id:
        stmt = stmt.where(NotificationModel.tenant_id == tenant_id)

    await session.execute(stmt)
    await session.commit()


@router.delete("/read", status_code=status.HTTP_204_NO_CONTENT)
async def delete_read_notifications(
    current_user: CurrentUser,
    _current_user_id: NotificationsWriter,
    tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete all read notifications."""

    stmt = (
        update(NotificationModel)
        .where(
            NotificationModel.user_id == current_user.id,
            NotificationModel.read_at.is_not(None),
            NotificationModel.is_deleted.is_(False),
        )
        .values(is_deleted=True, deleted_at=datetime.now(UTC))
    )

    if tenant_id:
        stmt = stmt.where(NotificationModel.tenant_id == tenant_id)

    await session.execute(stmt)
    await session.commit()


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID,
    current_user: CurrentUser,
    _current_user_id: NotificationsWriter,
    tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a notification (soft delete)."""

    stmt = (
        update(NotificationModel)
        .where(
            NotificationModel.id == notification_id,
            NotificationModel.user_id == current_user.id,
            NotificationModel.is_deleted.is_(False),
        )
        .values(is_deleted=True, deleted_at=datetime.now(UTC))
    )

    if tenant_id:
        stmt = stmt.where(NotificationModel.tenant_id == tenant_id)

    cursor_result = await session.execute(stmt)
    await session.commit()

    if cursor_result.rowcount == 0:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOTIFICATION_NOT_FOUND",
                "message": "Notification not found",
            },
        )
