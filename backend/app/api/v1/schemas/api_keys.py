# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Pydantic schemas for API Key endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""

    name: str = Field(..., min_length=1, max_length=255)
    scopes: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Permission scopes (e.g., 'users:read', 'roles:*')",
    )
    expires_in_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Days until expiration (null = never expires)",
    )


class APIKeyResponse(BaseModel):
    """Schema for API key response (without the key itself)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    usage_count: int
    created_at: datetime


class APIKeyCreatedResponse(BaseModel):
    """
    Schema for newly created API key response.

    This includes the plain key which is only shown once.
    """

    id: UUID
    name: str
    prefix: str
    key: str = Field(
        ...,
        description="The API key. Store this securely - it cannot be retrieved again.",
    )
    scopes: list[str]
    expires_at: datetime | None = None
    created_at: datetime

    # Warning message
    warning: str = Field(
        default="Store this key securely. It will not be shown again.",
    )


class APIKeyListResponse(BaseModel):
    """Schema for paginated API key list."""

    items: list[APIKeyResponse]
    total: int
