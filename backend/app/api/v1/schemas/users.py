# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""User schemas for request/response validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.api.v1.schemas.common import NameStr, PaginatedResponse, PasswordStr, UrlStr

# ===========================================
# Request Schemas
# ===========================================


class UserCreate(BaseModel):
    """Create user request (admin)."""

    email: EmailStr = Field(
        ...,
        description="User's email address",
    )
    password: PasswordStr = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Initial password",
    )
    first_name: NameStr = Field(
        ...,
        min_length=1,
    )
    last_name: NameStr = Field(
        ...,
        min_length=1,
    )
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    roles: list[UUID] = Field(default_factory=list, max_length=50)


class UserUpdate(BaseModel):
    """Update user request."""

    email: EmailStr | None = None
    first_name: NameStr | None = Field(
        default=None,
        min_length=1,
    )
    last_name: NameStr | None = Field(
        default=None,
        min_length=1,
    )
    is_active: bool | None = None
    roles: list[UUID] | None = Field(default=None, max_length=50)


class UserUpdateSelf(BaseModel):
    """Update self request (limited fields)."""

    first_name: NameStr | None = Field(
        default=None,
        min_length=1,
    )
    last_name: NameStr | None = Field(
        default=None,
        min_length=1,
    )


# ===========================================
# Response Schemas
# ===========================================


class UserResponse(BaseModel):
    """User response with basic info."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: NameStr = Field(max_length=200)
    last_name: NameStr = Field(max_length=200)
    avatar_url: UrlStr | None = Field(default=None, max_length=2048)
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None

    @field_validator("email", mode="before")
    @classmethod
    def convert_email(cls, v: Any) -> str:
        """Convert Email value object to string."""
        if hasattr(v, "value"):
            return str(v.value)
        return str(v)


class UserDetailResponse(UserResponse):
    """User response with additional details."""

    roles: list[UUID] = Field(default_factory=list)
    tenant_id: UUID


UserListResponse = PaginatedResponse[UserResponse]
"""Paginated user list — alias for PaginatedResponse[UserResponse]."""
