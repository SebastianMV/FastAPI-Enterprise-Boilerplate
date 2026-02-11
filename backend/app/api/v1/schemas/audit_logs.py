# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Pydantic schemas for Audit Log endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    action: str
    resource_type: str
    resource_id: str | None = None
    resource_name: str | None = None
    actor_id: UUID | None = None
    actor_email: str | None = None
    actor_ip: str | None = None
    actor_user_agent: str | None = None
    tenant_id: UUID | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list."""

    items: list[AuditLogResponse]
    total: int
    skip: int
    limit: int


class AuditLogFilters(BaseModel):
    """Schema for audit log filter options."""

    action: str | None = None
    resource_type: str | None = None
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
