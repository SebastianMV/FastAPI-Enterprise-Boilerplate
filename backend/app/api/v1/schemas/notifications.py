# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Pydantic schemas for Notification endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    """Notification response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str = Field(max_length=50)
    title: str = Field(max_length=200)
    message: str = Field(max_length=2000)
    priority: str = Field(max_length=20)
    data: dict[str, Any] | None = None
    action_url: str | None = Field(default=None, max_length=2048)
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated list of notifications with unread count."""

    items: list[NotificationResponse]
    total: int
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")
    unread_count: int


class MarkReadRequest(BaseModel):
    """Request to mark notifications as read."""

    notification_ids: list[UUID] = Field(..., min_length=1, max_length=100)


class UnreadCountResponse(BaseModel):
    """Unread notifications count."""

    count: int
