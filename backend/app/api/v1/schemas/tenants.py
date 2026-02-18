# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Pydantic schemas for Tenant endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.api.v1.schemas.common import LongNameStr, ShortStr, UrlStr


class TenantSettingsSchema(BaseModel):
    """Schema for tenant settings."""

    enable_2fa: bool = False
    enable_api_keys: bool = True
    enable_webhooks: bool = False
    max_users: int = Field(default=100, ge=1, le=10000)
    max_api_keys_per_user: int = Field(default=5, ge=1, le=100)
    max_storage_mb: int = Field(default=1024, ge=100, le=1000000)
    primary_color: ShortStr = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: UrlStr | None = None
    password_min_length: int = Field(default=8, ge=6, le=128)
    session_timeout_minutes: int = Field(default=60, ge=5, le=10080)
    require_email_verification: bool = True


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""

    name: LongNameStr = Field(..., min_length=2, max_length=255)
    slug: LongNameStr = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-friendly identifier (lowercase, hyphens allowed)",
    )
    email: EmailStr | None = None
    phone: ShortStr | None = None
    domain: LongNameStr | None = None
    timezone: ShortStr = Field(default="UTC")
    locale: ShortStr = Field(default="en", max_length=10)
    plan: ShortStr = Field(
        default="free", pattern=r"^(free|starter|professional|enterprise)$"
    )
    settings: TenantSettingsSchema | None = None


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: LongNameStr | None = Field(default=None, min_length=2, max_length=255)
    slug: LongNameStr | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    email: EmailStr | None = None
    phone: ShortStr | None = None
    domain: LongNameStr | None = None
    timezone: ShortStr | None = None
    locale: ShortStr | None = Field(default=None, max_length=10)
    plan: ShortStr | None = Field(
        default=None,
        pattern=r"^(free|starter|professional|enterprise)$",
    )
    settings: TenantSettingsSchema | None = None


class TenantResponse(BaseModel):
    """Schema for tenant response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: LongNameStr
    slug: LongNameStr = Field(max_length=100)
    email: EmailStr | None = None
    phone: ShortStr | None = None
    is_active: bool
    is_verified: bool
    plan: ShortStr
    plan_expires_at: datetime | None = None
    settings: TenantSettingsSchema
    domain: LongNameStr | None = None
    timezone: ShortStr
    locale: ShortStr = Field(max_length=10)
    created_at: datetime
    updated_at: datetime


class TenantListResponse(BaseModel):
    """Schema for paginated tenant list."""

    items: list[TenantResponse]
    total: int
    skip: int
    limit: int


class TenantActivateRequest(BaseModel):
    """Schema for activating/deactivating tenant."""

    is_active: bool


class TenantVerifyRequest(BaseModel):
    """Schema for verifying tenant."""

    is_verified: bool


class TenantPlanUpdate(BaseModel):
    """Schema for updating tenant plan."""

    plan: ShortStr = Field(..., pattern=r"^(free|starter|professional|enterprise)$")
    expires_at: datetime | None = None
