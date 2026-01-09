"""add avatar_url to users table

Revision ID: 010_add_avatar_url
Revises: 009_tenant_columns
Create Date: 2026-01-09

Adds avatar_url column to users table for profile pictures.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_add_avatar_url'
down_revision: Union[str, None] = '009_tenant_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add avatar_url column to users table."""
    op.add_column(
        'users',
        sa.Column('avatar_url', sa.String(500), nullable=True)
    )


def downgrade() -> None:
    """Remove avatar_url column from users table."""
    op.drop_column('users', 'avatar_url')
