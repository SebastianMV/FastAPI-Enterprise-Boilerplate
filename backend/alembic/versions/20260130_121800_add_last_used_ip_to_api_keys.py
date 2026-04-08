"""Add last_used_ip and usage_count to api_keys

Revision ID: 5e72375b1f12
Revises: 012_security_features
Create Date: 2026-01-30 12:18:00.722877

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e72375b1f12"
down_revision: str | None = "012_security_features"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add last_used_ip and usage_count columns to api_keys table."""
    # last_used_ip may already exist from partial migration
    from sqlalchemy.exc import OperationalError, ProgrammingError

    try:
        op.add_column(
            "api_keys",
            sa.Column(
                "last_used_ip",
                sa.String(length=45),
                nullable=True,
                comment="IP address of last API key usage",
            ),
        )
    except (OperationalError, ProgrammingError) as e:
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            pass  # Column already exists from a partial migration run
        else:
            raise  # Re-raise unexpected errors

    # Add usage_count column
    op.add_column(
        "api_keys",
        sa.Column(
            "usage_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of times the API key has been used",
        ),
    )


def downgrade() -> None:
    """Remove last_used_ip and usage_count columns from api_keys table."""
    op.drop_column("api_keys", "usage_count")
    op.drop_column("api_keys", "last_used_ip")
