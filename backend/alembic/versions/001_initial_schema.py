"""initial schema - tenants, users, roles, api_keys tables

Revision ID: 001
Revises: None
Create Date: 2026-01-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ===========================================
    # TENANTS TABLE
    # ===========================================
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("domain", sa.String(255), nullable=True, unique=True),
        sa.Column("settings", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
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

    # Indexes for tenants
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_index("ix_tenants_domain", "tenants", ["domain"], unique=True)
    op.create_index("ix_tenants_is_active", "tenants", ["is_active"])
    op.create_index("ix_tenants_is_deleted", "tenants", ["is_deleted"])

    # ===========================================
    # ROLES TABLE
    # ===========================================
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, default=""),
        sa.Column(
            "permissions",
            postgresql.ARRAY(sa.String(100)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("is_system", sa.Boolean, nullable=False, default=False),
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

    # Indexes for roles
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"])
    op.create_index("ix_roles_name", "roles", ["name"])
    op.create_index("ix_roles_is_system", "roles", ["is_system"])
    op.create_index("ix_roles_is_deleted", "roles", ["is_deleted"])
    op.create_index("ix_roles_tenant_name", "roles", ["tenant_id", "name"], unique=True)

    # ===========================================
    # USERS TABLE
    # ===========================================
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean, nullable=False, default=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "roles",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
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

    # Indexes for users
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index("ix_users_is_superuser", "users", ["is_superuser"])
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"])
    op.create_index(
        "ix_users_tenant_email", "users", ["tenant_id", "email"], unique=True
    )

    # ===========================================
    # API_KEYS TABLE
    # ===========================================
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(10), nullable=False),
        sa.Column(
            "permissions",
            postgresql.ARRAY(sa.String(100)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
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

    # Indexes for api_keys
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_keys_is_active", "api_keys", ["is_active"])
    op.create_index("ix_api_keys_is_deleted", "api_keys", ["is_deleted"])
    op.create_index("ix_api_keys_expires_at", "api_keys", ["expires_at"])

    # ===========================================
    # INSERT DEFAULT TENANT
    # ===========================================
    op.execute("""
        INSERT INTO tenants (id, name, slug, is_active, settings, is_deleted)
        VALUES (
            '00000000-0000-0000-0000-000000000001'::uuid,
            'Default Organization',
            'default',
            true,
            '{"features": {"mfa_required": false, "api_keys_enabled": true}}'::jsonb,
            false
        )
    """)

    # ===========================================
    # INSERT DEFAULT ROLES
    # ===========================================
    op.execute("""
        INSERT INTO roles (id, tenant_id, name, description, permissions, is_system, is_deleted)
        VALUES 
        (
            '00000000-0000-0000-0000-000000000010'::uuid,
            '00000000-0000-0000-0000-000000000001'::uuid,
            'superadmin',
            'Super Administrator with full access',
            ARRAY['*:*'],
            true,
            false
        ),
        (
            '00000000-0000-0000-0000-000000000011'::uuid,
            '00000000-0000-0000-0000-000000000001'::uuid,
            'admin',
            'Administrator with user and tenant management',
            ARRAY['users:read', 'users:create', 'users:update', 'tenants:read', 'reports:*'],
            true,
            false
        ),
        (
            '00000000-0000-0000-0000-000000000012'::uuid,
            '00000000-0000-0000-0000-000000000001'::uuid,
            'user',
            'Standard user with basic access',
            ARRAY['users:read', 'profile:*'],
            false,
            false
        )
    """)

    # ===========================================
    # INSERT DEFAULT USERS (DEVELOPMENT ONLY)
    # ===========================================
    # Password hashes generated with bcrypt (12 rounds)
    # Admin123! -> $2b$12$mwnzt7mR35Fnd7nLeRWmXuTMnqEWEdxQQXB/9LmKQu0d0lDs07RGy
    # Manager123! -> $2b$12$IrHs82W4NW4SGMkeaKwZUerxwxmqSSScVerbfy.GkXehrOhPL1/Wa
    # User123! -> $2b$12$tqAWefh2mkROg0vDHRiWEOoVZqmocGN.dpqLUmBo7gRukFxPtd5gi
    #
    # ⚠️ WARNING: These users are for DEVELOPMENT/TESTING only!
    # DELETE these users before deploying to production!
    op.execute("""
        INSERT INTO users (id, tenant_id, email, password_hash, first_name, last_name, is_active, is_superuser, roles, is_deleted)
        VALUES 
        (
            '00000000-0000-0000-0000-000000000100'::uuid,
            '00000000-0000-0000-0000-000000000001'::uuid,
            'admin@example.com',
            '$2b$12$mwnzt7mR35Fnd7nLeRWmXuTMnqEWEdxQQXB/9LmKQu0d0lDs07RGy',
            'System',
            'Administrator',
            true,
            true,
            ARRAY['00000000-0000-0000-0000-000000000010'::uuid],
            false
        ),
        (
            '00000000-0000-0000-0000-000000000101'::uuid,
            '00000000-0000-0000-0000-000000000001'::uuid,
            'manager@example.com',
            '$2b$12$IrHs82W4NW4SGMkeaKwZUerxwxmqSSScVerbfy.GkXehrOhPL1/Wa',
            'Tenant',
            'Manager',
            true,
            false,
            ARRAY['00000000-0000-0000-0000-000000000011'::uuid],
            false
        ),
        (
            '00000000-0000-0000-0000-000000000102'::uuid,
            '00000000-0000-0000-0000-000000000001'::uuid,
            'user@example.com',
            '$2b$12$tqAWefh2mkROg0vDHRiWEOoVZqmocGN.dpqLUmBo7gRukFxPtd5gi',
            'Demo',
            'User',
            true,
            false,
            ARRAY['00000000-0000-0000-0000-000000000012'::uuid],
            false
        )
    """)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("tenants")
