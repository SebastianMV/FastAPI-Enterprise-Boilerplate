"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade database schema.
    
    NOTE: If adding a new table with a tenant_id column, remember to:
    1. ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
    2. CREATE POLICY <table>_tenant_isolation ON <table>
       USING (tenant_id::text = current_setting('app.current_tenant', TRUE));
    See migration 006_rls_policies.py for reference.
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade database schema."""
    ${downgrades if downgrades else "pass"}
