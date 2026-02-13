# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Pydantic schemas for Audit Log endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import NameStr, ShortStr, TextStr


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    action: str = Field(max_length=50)
    resource_type: str = Field(max_length=50)
    resource_id: str | None = Field(default=None, max_length=200)
    resource_name: str | None = Field(default=None, max_length=200)
    actor_id: UUID | None = None
    actor_email: str | None = Field(default=None, max_length=320)
    actor_ip: str | None = Field(default=None, max_length=45)
    actor_user_agent: str | None = Field(default=None, max_length=500)
    tenant_id: UUID | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = Field(default=None, max_length=500)


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list."""

    items: list[AuditLogResponse]
    total: int
    skip: int
    limit: int


class AuditLogFilters(BaseModel):
    """Schema for audit log filter options."""

    action: ShortStr | None = None
    resource_type: ShortStr | None = None
    actor_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class AuditLogStatsResponse(BaseModel):
    """Schema for audit log statistics."""

    total_entries: int
    actions_breakdown: dict[str, int]
    resource_types_breakdown: dict[str, int]
    recent_login_attempts: int
    failed_login_attempts: int
