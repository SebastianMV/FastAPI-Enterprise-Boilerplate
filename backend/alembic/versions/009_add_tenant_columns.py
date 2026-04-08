"""add missing audit columns to all tables

Revision ID: 009_tenant_columns
Revises: 006_rls_policies
Create Date: 2026-01-08

Adds missing columns to multiple tables:

Tenants:
- email, phone (contact)
- is_verified, plan, plan_expires_at (subscription)
- timezone, locale (localization)
- created_by, updated_by, deleted_by (audit)

Users:
- created_by, updated_by, deleted_by (audit)

Roles:
- created_by, updated_by, deleted_by (audit)

API Keys:
- created_by (audit)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_tenant_columns"
down_revision: str | None = "006_rls_policies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add missing columns to all tables."""

    # ===========================================
    # TENANTS TABLE
    # ===========================================

    # Contact columns
    op.add_column("tenants", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("phone", sa.String(50), nullable=True))

    # Subscription columns
    op.add_column(
        "tenants",
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "tenants",
        sa.Column("plan", sa.String(50), nullable=False, server_default="'free'"),
    )
    op.add_column(
        "tenants",
        sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Localization columns
    op.add_column(
        "tenants",
        sa.Column("timezone", sa.String(50), nullable=False, server_default="'UTC'"),
    )
    op.add_column(
        "tenants",
        sa.Column("locale", sa.String(10), nullable=False, server_default="'en'"),
    )

    # Audit columns
    op.add_column("tenants", sa.Column("created_by", UUID(as_uuid=True), nullable=True))
    op.add_column("tenants", sa.Column("updated_by", UUID(as_uuid=True), nullable=True))
    op.add_column("tenants", sa.Column("deleted_by", UUID(as_uuid=True), nullable=True))

    # Update column sizes
    op.alter_column("tenants", "name", type_=sa.String(255))
    op.alter_column("tenants", "slug", type_=sa.String(100))

    # ===========================================
    # USERS TABLE
    # ===========================================

    # Audit columns
    op.add_column("users", sa.Column("created_by", UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("updated_by", UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("deleted_by", UUID(as_uuid=True), nullable=True))

    # ===========================================
    # ROLES TABLE
    # ===========================================

    # Audit columns
    op.add_column("roles", sa.Column("created_by", UUID(as_uuid=True), nullable=True))
    op.add_column("roles", sa.Column("updated_by", UUID(as_uuid=True), nullable=True))
    op.add_column("roles", sa.Column("deleted_by", UUID(as_uuid=True), nullable=True))

    # ===========================================
    # API_KEYS TABLE
    # ===========================================

    # Audit column
    op.add_column(
        "api_keys", sa.Column("created_by", UUID(as_uuid=True), nullable=True)
    )


def downgrade() -> None:
    """Remove added columns from all tables."""

    # Tenants
    op.drop_column("tenants", "email")
    op.drop_column("tenants", "phone")
    op.drop_column("tenants", "is_verified")
    op.drop_column("tenants", "plan")
    op.drop_column("tenants", "plan_expires_at")
    op.drop_column("tenants", "timezone")
    op.drop_column("tenants", "locale")
    op.drop_column("tenants", "created_by")
    op.drop_column("tenants", "updated_by")
    op.drop_column("tenants", "deleted_by")
    op.alter_column("tenants", "name", type_=sa.String(100))
    op.alter_column("tenants", "slug", type_=sa.String(50))

    # Users
    op.drop_column("users", "created_by")
    op.drop_column("users", "updated_by")
    op.drop_column("users", "deleted_by")

    # Roles
    op.drop_column("roles", "created_by")
    op.drop_column("roles", "updated_by")
    op.drop_column("roles", "deleted_by")

    # API Keys
    op.drop_column("api_keys", "created_by")
