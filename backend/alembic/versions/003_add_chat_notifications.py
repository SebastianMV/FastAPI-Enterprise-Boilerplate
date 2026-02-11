"""add conversations, chat_messages, notifications tables

Revision ID: 003_add_chat_notifications
Revises: 002_add_audit_mfa
Create Date: 2026-01-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_add_chat_notifications"
down_revision: str | None = "002_add_audit_mfa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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

    # ===========================================
    # NOTIFICATIONS TABLE
    # ===========================================
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(50), nullable=False, default="info"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("priority", sa.String(20), nullable=False, default="normal"),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column(
            "channels",
            postgresql.ARRAY(sa.String(20)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "delivery_status", postgresql.JSONB, nullable=False, server_default="{}"
        ),
        sa.Column("is_read", sa.Boolean, nullable=False, default=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("group_key", sa.String(100), nullable=True),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("action_clicked", sa.Boolean, nullable=False, default=False),
        sa.Column("action_clicked_at", sa.DateTime(timezone=True), nullable=True),
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

    op.create_index("ix_notifications_tenant_id", "notifications", ["tenant_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_category", "notifications", ["category"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "is_read", "created_at"],
    )
    op.create_index("ix_notifications_group_key", "notifications", ["group_key"])
    op.create_index("ix_notifications_is_deleted", "notifications", ["is_deleted"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("notifications")
    op.drop_table("chat_messages")
    op.drop_table("conversation_participants")
    op.drop_table("conversations")
