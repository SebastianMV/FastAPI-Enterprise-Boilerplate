# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""User schemas for request/response validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ===========================================
# Request Schemas
# ===========================================


class UserCreate(BaseModel):
    """Create user request (admin)."""

    email: EmailStr = Field(
        ...,
        description="User's email address",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Initial password",
    )
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    roles: list[UUID] = Field(default_factory=list, max_length=50)


class UserUpdate(BaseModel):
    """Update user request."""

    email: EmailStr | None = None
    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    is_active: bool | None = None
    roles: list[UUID] | None = Field(default=None, max_length=50)


class UserUpdateSelf(BaseModel):
    """Update self request (limited fields)."""

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )


# ===========================================
# Response Schemas
# ===========================================


class UserResponse(BaseModel):
    """User response with basic info."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str = Field(max_length=320)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    avatar_url: str | None = Field(default=None, max_length=2048)
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
            return v.value
        return str(v)


class UserDetailResponse(UserResponse):
    """User response with additional details."""

    roles: list[UUID] = Field(default_factory=list)
    tenant_id: UUID


class UserListResponse(BaseModel):
    """Paginated user list response."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int
