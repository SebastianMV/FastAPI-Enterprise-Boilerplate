"""add avatar_url to users table

Revision ID: 010_add_avatar_url
Revises: 009_tenant_columns
Create Date: 2026-01-09

Adds avatar_url column to users table for profile pictures.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_add_avatar_url"
down_revision: str | None = "009_tenant_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add avatar_url column to users table."""
    op.add_column("users", sa.Column("avatar_url", sa.String(500), nullable=True))


def downgrade() -> None:
    """Remove avatar_url column from users table."""
    op.drop_column("users", "avatar_url")
