# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Notifications REST API endpoints.

Provides endpoints for:
- Notification listing and management
- Mark as read/unread
- Delete notifications
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.models.notification import NotificationModel


router = APIRouter(prefix="/notifications")


# ===========================================
# Schemas
# ===========================================

class NotificationResponse(BaseModel):
    """Notification response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    type: str
    title: str
    message: str
    priority: str
    data: Optional[dict] = None
    action_url: Optional[str] = None
    is_read: bool
    read_at: Optional[str] = None
    created_at: str


class NotificationListResponse(BaseModel):
    """List of notifications."""
    
    items: list[NotificationResponse]
    total: int
    unread_count: int


class MarkReadRequest(BaseModel):
    """Request to mark notifications as read."""
    
    notification_ids: list[str] = Field(..., min_length=1)


class UnreadCountResponse(BaseModel):
    """Unread notifications count."""
    
    count: int


# ===========================================
# Endpoints
# ===========================================

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
):
    """List user's notifications."""
    # Build query
    query = (
        select(NotificationModel)
        .where(
            NotificationModel.user_id == current_user.id,
            NotificationModel.is_deleted == False,
        )
    )
    
    if unread_only:
        query = query.where(NotificationModel.read_at.is_(None))
    
    query = query.order_by(NotificationModel.created_at.desc()).limit(limit).offset(offset)
    
    result = await session.execute(query)
    notifications = result.scalars().all()
    
    # Count total
    count_query = (
        select(func.count(NotificationModel.id))
        .where(
            NotificationModel.user_id == current_user.id,
            NotificationModel.is_deleted == False,
        )
    )
    if unread_only:
        count_query = count_query.where(NotificationModel.read_at.is_(None))
    
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0
    
    # Count unread
    unread_query = (
        select(func.count(NotificationModel.id))
        .where(
            NotificationModel.user_id == current_user.id,
            NotificationModel.is_deleted == False,
            NotificationModel.read_at.is_(None),
        )
    )
    unread_result = await session.execute(unread_query)
    unread_count = unread_result.scalar() or 0
    
    return NotificationListResponse(
        items=[
            NotificationResponse(
                id=str(n.id),
                type=n.type,
                title=n.title,
                message=n.message,
                priority=n.priority,
                data=n.metadata,
                action_url=n.action_url,
                is_read=n.read_at is not None,
                read_at=n.read_at.isoformat() if n.read_at else None,
                created_at=n.created_at.isoformat(),
            )
            for n in notifications
        ],
        total=total,
        unread_count=unread_count,
    )


@router.get("/unread/count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Get count of unread notifications."""
    query = (
        select(func.count(NotificationModel.id))
        .where(
            NotificationModel.user_id == current_user.id,
            NotificationModel.is_deleted == False,
            NotificationModel.read_at.is_(None),
        )
    )
    
    result = await session.execute(query)
    count = result.scalar() or 0
    
    return UnreadCountResponse(count=count)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a specific notification."""
    query = select(NotificationModel).where(
        NotificationModel.id == notification_id,
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_deleted == False,
    )
    
    result = await session.execute(query)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    
    return NotificationResponse(
        id=str(notification.id),
        type=notification.type,
        title=notification.title,
        message=notification.message,
        priority=notification.priority,
        data=notification.metadata,
        action_url=notification.action_url,
        is_read=notification.read_at is not None,
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        created_at=notification.created_at.isoformat(),
    )


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_as_read(
    request: MarkReadRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Mark notifications as read."""
    from datetime import datetime, timezone
    
    notification_ids = [UUID(nid) for nid in request.notification_ids]
    
    stmt = (
        update(NotificationModel)
        .where(
            NotificationModel.id.in_(notification_ids),
            NotificationModel.user_id == current_user.id,
            NotificationModel.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    
    await session.execute(stmt)
    await session.commit()


@router.post("/read/all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_as_read(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Mark all notifications as read."""
    from datetime import datetime, timezone
    
    stmt = (
        update(NotificationModel)
        .where(
            NotificationModel.user_id == current_user.id,
            NotificationModel.read_at.is_(None),
            NotificationModel.is_deleted == False,
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    
    await session.execute(stmt)
    await session.commit()


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a notification (soft delete)."""
    from datetime import datetime, timezone
    
    stmt = (
        update(NotificationModel)
        .where(
            NotificationModel.id == notification_id,
            NotificationModel.user_id == current_user.id,
            NotificationModel.is_deleted == False,
        )
        .values(is_deleted=True, deleted_at=datetime.now(timezone.utc))
    )
    
    result = await session.execute(stmt)
    await session.commit()


@router.delete("/read", status_code=status.HTTP_204_NO_CONTENT)
async def delete_read_notifications(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete all read notifications."""
    from datetime import datetime, timezone
    
    stmt = (
        update(NotificationModel)
        .where(
            NotificationModel.user_id == current_user.id,
            NotificationModel.read_at.isnot(None),
            NotificationModel.is_deleted == False,
        )
        .values(is_deleted=True, deleted_at=datetime.now(timezone.utc))
    )
    
    await session.execute(stmt)
    await session.commit()
