# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Pydantic schemas for Audit Log endpoints."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    timestamp: datetime
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    actor_id: Optional[UUID] = None
    actor_email: Optional[str] = None
    actor_ip: Optional[str] = None
    actor_user_agent: Optional[str] = None
    tenant_id: Optional[UUID] = None
    old_value: Optional[dict[str, Any]] = None
    new_value: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = None


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list."""
    
    items: list[AuditLogResponse]
    total: int
    skip: int
    limit: int


class AuditLogFilters(BaseModel):
    """Schema for audit log filter options."""
    
    action: Optional[str] = None
    resource_type: Optional[str] = None
    actor_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AuditLogStatsResponse(BaseModel):
    """Schema for audit log statistics."""
    
    total_entries: int
    actions_breakdown: dict[str, int]
    resource_types_breakdown: dict[str, int]
    recent_login_attempts: int
    failed_login_attempts: int
