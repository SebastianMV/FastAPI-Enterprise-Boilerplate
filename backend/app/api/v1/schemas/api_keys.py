# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Pydantic schemas for API Key endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import (
    DescriptionStr,
    LongNameStr,
    ScopeStr,
    ShortStr,
    TokenStr,
)


class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""

    name: LongNameStr = Field(..., min_length=1)
    scopes: list[ScopeStr] = Field(
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
    name: LongNameStr
    prefix: ShortStr = Field(max_length=20)
    scopes: list[ScopeStr]
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
    name: LongNameStr
    prefix: ShortStr = Field(max_length=20)
    key: TokenStr = Field(
        ...,
        description="The API key. Store this securely - it cannot be retrieved again.",
    )
    scopes: list[ScopeStr]
    expires_at: datetime | None = None
    created_at: datetime

    # Warning message
    warning: DescriptionStr = Field(
        default="Store this key securely. It will not be shown again.",
        max_length=200,
    )


class APIKeyListResponse(BaseModel):
    """Schema for paginated API key list."""

    items: list[APIKeyResponse]
    total: int
