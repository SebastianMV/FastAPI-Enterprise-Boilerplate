# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Add security features: account lockout, email verification, sessions

Revision ID: 012_security_features
Revises: 011_remove_chat_tables
Create Date: 2026-01-12

This migration adds:
1. Account lockout fields to users table (failed_login_attempts, locked_until)
2. Email verification fields to users table (email_verified, email_verification_token, email_verification_sent_at)
3. User sessions table for session management
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "012_security_features"
down_revision = "011_remove_chat_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add security features."""

    # Add account lockout fields to users table
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Add email verification fields to users table
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verification_token",
            sa.String(255),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verification_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Create user_sessions table
    op.create_table(
        "user_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("device_name", sa.String(255), nullable=False, server_default=""),
        sa.Column(
            "device_type", sa.String(50), nullable=False, server_default="desktop"
        ),
        sa.Column("browser", sa.String(100), nullable=False, server_default=""),
        sa.Column("os", sa.String(100), nullable=False, server_default=""),
        sa.Column("ip_address", sa.String(45), nullable=False, server_default=""),
        sa.Column("location", sa.String(255), nullable=False, server_default=""),
        sa.Column(
            "last_activity",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # Create indexes
    op.create_index("ix_user_sessions_tenant_id", "user_sessions", ["tenant_id"])
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index(
        "ix_user_sessions_refresh_token_hash", "user_sessions", ["refresh_token_hash"]
    )

    # Mark existing users as email verified (for backwards compatibility)
    op.execute("UPDATE users SET email_verified = true WHERE email_verified = false")


def downgrade() -> None:
    """Remove security features."""

    # Drop user_sessions table
    op.drop_index("ix_user_sessions_refresh_token_hash", "user_sessions")
    op.drop_index("ix_user_sessions_user_id", "user_sessions")
    op.drop_index("ix_user_sessions_tenant_id", "user_sessions")
    op.drop_table("user_sessions")

    # Remove email verification fields
    op.drop_column("users", "email_verification_sent_at")
    op.drop_column("users", "email_verification_token")
    op.drop_column("users", "email_verified")

    # Remove account lockout fields
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
