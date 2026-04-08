"""add audit_logs and mfa_configs tables

Revision ID: 002_add_audit_mfa
Revises: 001
Create Date: 2026-01-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_audit_mfa"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### Audit Logs Table ###
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("actor_ip", sa.String(45), nullable=True),
        sa.Column("actor_user_agent", sa.String(500), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("resource_name", sa.String(255), nullable=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("old_value", postgresql.JSONB, nullable=True),
        sa.Column("new_value", postgresql.JSONB, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
    )

    # Indexes for audit_logs
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index(
        "ix_audit_logs_resource",
        "audit_logs",
        ["resource_type", "resource_id", "timestamp"],
    )
    op.create_index(
        "ix_audit_logs_tenant_activity", "audit_logs", ["tenant_id", "timestamp"]
    )
    op.create_index("ix_audit_logs_security", "audit_logs", ["action", "timestamp"])
    op.create_index(
        "ix_audit_logs_actor_activity", "audit_logs", ["actor_id", "timestamp"]
    )

    # ### MFA Configs Table ###
    op.create_table(
        "mfa_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("secret", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, default=False),
        sa.Column(
            "backup_codes",
            postgresql.ARRAY(sa.String(64)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Index for mfa_configs
    op.create_index("ix_mfa_configs_user_id", "mfa_configs", ["user_id"])


def downgrade() -> None:
    # Drop MFA configs table
    op.drop_index("ix_mfa_configs_user_id")
    op.drop_table("mfa_configs")

    # Drop Audit logs table
    op.drop_index("ix_audit_logs_actor_activity")
    op.drop_index("ix_audit_logs_security")
    op.drop_index("ix_audit_logs_tenant_activity")
    op.drop_index("ix_audit_logs_resource")
    op.drop_index("ix_audit_logs_tenant_id")
    op.drop_index("ix_audit_logs_resource_type")
    op.drop_index("ix_audit_logs_action")
    op.drop_index("ix_audit_logs_actor_id")
    op.drop_index("ix_audit_logs_timestamp")
    op.drop_table("audit_logs")
