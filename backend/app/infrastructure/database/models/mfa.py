# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
SQLAlchemy model for MFA configuration.

Stores TOTP secrets and backup codes for two-factor authentication.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from app.infrastructure.database.models.custom_types import JSONEncodedList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base


class MFAConfigModel(Base):
    """
    MFA Configuration database model.
    
    Table: mfa_configs
    
    Stores the TOTP secret and backup codes for user MFA.
    The secret should be encrypted using application-level encryption
    before storage for additional security.
    """
    
    __tablename__ = "mfa_configs"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # User relationship (one-to-one)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # One MFA config per user
        nullable=False,
        index=True,
    )
    
    # TOTP secret (base32 encoded, should be encrypted at rest)
    secret: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    
    # Status
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    # Backup codes (array of hashed codes)
    backup_codes: Mapped[list[str]] = mapped_column(
        JSONEncodedList,
        nullable=False,
        default=list,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    enabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    def __repr__(self) -> str:
        return (
            f"<MFAConfig(id={self.id}, user_id={self.user_id}, "
            f"enabled={self.is_enabled})>"
        )
