# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
OAuth2 database models.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base
from app.infrastructure.database.models.custom_types import JSONEncodedList, JSONBCompat


class OAuthConnectionModel(Base):
    """OAuth connection model for storing user OAuth links."""
    
    __tablename__ = "oauth_connections"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_user_id",
            name="uq_oauth_provider_user"
        ),
        {"schema": None},  # Use default schema
    )
    
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Provider info
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Tokens (should be encrypted)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Scopes
    scopes: Mapped[list[str]] = mapped_column(JSONEncodedList, default=list)
    
    # Raw provider data
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONBCompat, default=dict)
    
    # Status
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    # Relationships
    user = relationship("UserModel", back_populates="oauth_connections")


class SSOConfigurationModel(Base):
    """SSO configuration model for tenant SSO settings."""
    
    __tablename__ = "sso_configurations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "provider",
            name="uq_sso_tenant_provider"
        ),
        {"schema": None},
    )
    
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # OAuth2 Config
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted
    authorization_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    userinfo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # SAML Config
    saml_metadata_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    saml_entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    saml_sso_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    saml_slo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    saml_certificate: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Scopes
    scopes: Mapped[list[str]] = mapped_column(JSONEncodedList, default=list)
    
    # Attribute mapping
    attribute_mapping: Mapped[dict[str, str]] = mapped_column(JSONBCompat, default=dict)
    
    # Auto-provisioning
    auto_create_users: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_update_users: Mapped[bool] = mapped_column(Boolean, default=True)
    default_role_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Domain restrictions
    allowed_domains: Mapped[list[str]] = mapped_column(JSONEncodedList, default=list)
    
    # Status
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
