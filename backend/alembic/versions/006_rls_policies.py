"""add_rls_policies_complete

Revision ID: 006_rls_policies
Revises: 005_full_text_search
Create Date: 2026-01-07 19:45:00.000000

Complete RLS (Row Level Security) setup:
- Enable RLS on all tenant tables
- Create SELECT policies for tenant isolation
- Create INSERT/UPDATE/DELETE policies with WITH CHECK
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_rls_policies"
down_revision: str | None = "005_full_text_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add INSERT/UPDATE/DELETE policies for RLS."""

    # Drop existing SELECT-only policies and recreate with full CRUD support
    tables_with_tenant = [
        ("users", "tenant_id::text"),
        ("roles", "tenant_id::text"),
        ("api_keys", "tenant_id::text"),
        ("conversations", "tenant_id::text"),
        ("notifications", "tenant_id::text"),
        ("audit_logs", "tenant_id::text"),
    ]

    for table, tenant_column in tables_with_tenant:
        # Drop existing policy
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")

        # Create new policy for ALL operations with WITH CHECK
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            FOR ALL
            USING ({tenant_column} = COALESCE(current_setting('app.current_tenant_id', true), ''))
            WITH CHECK ({tenant_column} = COALESCE(current_setting('app.current_tenant_id', true), ''))
        """)

    # Chat Messages (uses conversation FK)
    op.execute("DROP POLICY IF EXISTS chat_messages_tenant_isolation ON chat_messages")
    op.execute("""
        CREATE POLICY chat_messages_tenant_isolation ON chat_messages
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM conversations c
                WHERE c.id = chat_messages.conversation_id
                AND c.tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), '')
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM conversations c
                WHERE c.id = chat_messages.conversation_id
                AND c.tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), '')
            )
        )
    """)


def downgrade() -> None:
    """Revert to SELECT-only policies."""

    tables_with_tenant = [
        ("users", "tenant_id::text"),
        ("roles", "tenant_id::text"),
        ("api_keys", "tenant_id::text"),
        ("conversations", "tenant_id::text"),
        ("notifications", "tenant_id::text"),
        ("audit_logs", "tenant_id::text"),
    ]

    for table, tenant_column in tables_with_tenant:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING ({tenant_column} = COALESCE(current_setting('app.current_tenant_id', true), ''))
        """)

    # Chat Messages
    op.execute("DROP POLICY IF EXISTS chat_messages_tenant_isolation ON chat_messages")
    op.execute("""
        CREATE POLICY chat_messages_tenant_isolation ON chat_messages
        USING (
            EXISTS (
                SELECT 1 FROM conversations c
                WHERE c.id = chat_messages.conversation_id
                AND c.tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), '')
            )
        )
    """)
