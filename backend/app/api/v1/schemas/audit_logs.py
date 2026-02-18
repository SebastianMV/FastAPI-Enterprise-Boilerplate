# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Pydantic schemas for Audit Log endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.api.v1.schemas.common import DescriptionStr, NameStr, ShortStr

# Keys that must never appear in audit log value diffs
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "hashed_password",
        "secret",
        "access_token",
        "refresh_token",
        "token",
        "key_hash",
        "client_secret",
        "backup_codes",
        "code_verifier",
    }
)


def _strip_sensitive(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove sensitive keys from audit log value dicts."""
    if data is None:
        return None
    return {k: v for k, v in data.items() if k.lower() not in _SENSITIVE_KEYS}


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    action: ShortStr = Field(max_length=50)
    resource_type: ShortStr = Field(max_length=50)
    resource_id: NameStr | None = Field(default=None, max_length=200)
    resource_name: NameStr | None = Field(default=None, max_length=200)
    actor_id: UUID | None = None
    actor_email: EmailStr | None = None
    actor_ip: ShortStr | None = Field(default=None, max_length=45)
    actor_user_agent: DescriptionStr | None = Field(default=None, max_length=500)
    tenant_id: UUID | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    reason: DescriptionStr | None = Field(default=None, max_length=500)

    @field_validator("old_value", "new_value", mode="before")
    @classmethod
    def strip_sensitive_keys(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Strip sensitive keys from audit log value diffs."""
        return _strip_sensitive(v)


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
