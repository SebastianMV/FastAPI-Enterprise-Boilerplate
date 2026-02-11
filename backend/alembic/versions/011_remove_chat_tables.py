"""Remove chat tables (conversations, conversation_participants, chat_messages)

Chat functionality has been removed from the boilerplate.
External tools like Slack, Teams, or WhatsApp are better suited for messaging.
WebSocket is retained for real-time notifications only.

Revision ID: 011_remove_chat_tables
Revises: 010_add_avatar_url
Create Date: 2026-01-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011_remove_chat_tables"
down_revision: str | None = "010_add_avatar_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove chat-related tables."""

    # Drop RLS policies first (if they exist)
    op.execute("DROP POLICY IF EXISTS chat_messages_tenant_isolation ON chat_messages")
    op.execute("DROP POLICY IF EXISTS conversations_tenant_isolation ON conversations")
    op.execute(
        "DROP POLICY IF EXISTS conversation_participants_tenant_isolation ON conversation_participants"
    )

    # Drop indexes
    op.drop_index(
        "ix_chat_messages_tenant_id", table_name="chat_messages", if_exists=True
    )
    op.drop_index(
        "ix_chat_messages_conversation_id", table_name="chat_messages", if_exists=True
    )
    op.drop_index(
        "ix_chat_messages_sender_id", table_name="chat_messages", if_exists=True
    )
    op.drop_index(
        "ix_chat_messages_created_at", table_name="chat_messages", if_exists=True
    )
    op.drop_index(
        "ix_chat_messages_conv_created", table_name="chat_messages", if_exists=True
    )
    op.drop_index(
        "ix_chat_messages_is_deleted", table_name="chat_messages", if_exists=True
    )

    op.drop_index(
        "ix_conv_participants_user_id",
        table_name="conversation_participants",
        if_exists=True,
    )
    op.drop_index(
        "ix_conv_participants_conv_user",
        table_name="conversation_participants",
        if_exists=True,
    )

    op.drop_index(
        "ix_conversations_tenant_id", table_name="conversations", if_exists=True
    )
    op.drop_index("ix_conversations_type", table_name="conversations", if_exists=True)
    op.drop_index(
        "ix_conversations_last_message_at", table_name="conversations", if_exists=True
    )
    op.drop_index(
        "ix_conversations_is_deleted", table_name="conversations", if_exists=True
    )

    # Drop tables in correct order (respecting foreign keys)
    op.drop_table("chat_messages")
    op.drop_table("conversation_participants")
    op.drop_table("conversations")


def downgrade() -> None:
    """Recreate chat tables if needed."""

    # ===========================================
    # CONVERSATIONS TABLE
    # ===========================================
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, default="direct"),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("last_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_preview", sa.String(100), nullable=True),
        sa.Column("message_count", sa.Integer, nullable=False, default=0),
        sa.Column("is_archived", sa.Boolean, nullable=False, default=False),
        sa.Column("send_permission", sa.String(20), nullable=False, default="all"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("is_deleted", sa.Boolean, nullable=False, default=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
    op.create_index("ix_conversations_type", "conversations", ["type"])
    op.create_index(
        "ix_conversations_last_message_at", "conversations", ["last_message_at"]
    )
    op.create_index("ix_conversations_is_deleted", "conversations", ["is_deleted"])

    # ===========================================
    # CONVERSATION PARTICIPANTS TABLE
    # ===========================================
    op.create_table(
        "conversation_participants",
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("is_muted", sa.Boolean, nullable=False, default=False),
        sa.Column("muted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_read_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, default="member"),
        sa.Column("nickname", sa.String(50), nullable=True),
    )

    op.create_index(
        "ix_conv_participants_user_id", "conversation_participants", ["user_id"]
    )
    op.create_index(
        "ix_conv_participants_conv_user",
        "conversation_participants",
        ["conversation_id", "user_id"],
    )

    # ===========================================
    # CHAT MESSAGES TABLE
    # ===========================================
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_type", sa.String(20), nullable=False, default="text"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, default="sent"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reply_to_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reactions", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_edited", sa.Boolean, nullable=False, default=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("is_deleted", sa.Boolean, nullable=False, default=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_chat_messages_tenant_id", "chat_messages", ["tenant_id"])
    op.create_index(
        "ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"]
    )
    op.create_index("ix_chat_messages_sender_id", "chat_messages", ["sender_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])
    op.create_index(
        "ix_chat_messages_conv_created",
        "chat_messages",
        ["conversation_id", "created_at"],
    )
    op.create_index("ix_chat_messages_is_deleted", "chat_messages", ["is_deleted"])
