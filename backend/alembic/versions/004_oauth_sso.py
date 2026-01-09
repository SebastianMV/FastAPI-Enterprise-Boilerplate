"""Add OAuth2 and SSO tables

Revision ID: 004_oauth_sso
Revises: 003_add_chat_notifications
Create Date: 2025-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_oauth_sso'
down_revision = '003_add_chat_notifications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create oauth_connections table
    op.create_table(
        'oauth_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('provider_email', sa.String(255), nullable=True),
        sa.Column('provider_username', sa.String(255), nullable=True),
        sa.Column('provider_display_name', sa.String(255), nullable=True),
        sa.Column('provider_avatar_url', sa.String(1024), nullable=True),
        sa.Column('access_token', sa.Text, nullable=True),
        sa.Column('refresh_token', sa.Text, nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scopes', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('raw_data', postgresql.JSONB, nullable=True),
        sa.Column('is_primary', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    
    # Unique constraint: one connection per provider per user
    op.create_index(
        'ix_oauth_connections_user_provider',
        'oauth_connections',
        ['user_id', 'provider'],
        unique=True,
        postgresql_where=sa.text('is_active = true'),
    )
    
    # Unique constraint: provider_user_id per provider
    op.create_index(
        'ix_oauth_connections_provider_user',
        'oauth_connections',
        ['provider', 'provider_user_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true'),
    )
    
    # Index for faster lookups
    op.create_index(
        'ix_oauth_connections_tenant',
        'oauth_connections',
        ['tenant_id'],
    )
    
    # Create sso_configurations table
    op.create_table(
        'sso_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('client_id', sa.String(255), nullable=False),
        sa.Column('client_secret', sa.Text, nullable=False),  # Should be encrypted
        sa.Column('authorization_url', sa.String(1024), nullable=True),
        sa.Column('token_url', sa.String(1024), nullable=True),
        sa.Column('userinfo_url', sa.String(1024), nullable=True),
        sa.Column('saml_metadata_url', sa.String(1024), nullable=True),
        sa.Column('saml_entity_id', sa.String(255), nullable=True),
        sa.Column('saml_sso_url', sa.String(1024), nullable=True),
        sa.Column('saml_slo_url', sa.String(1024), nullable=True),
        sa.Column('saml_certificate', sa.Text, nullable=True),
        sa.Column('scopes', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('attribute_mapping', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('auto_create_users', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('auto_update_users', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('default_role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('allowed_domains', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('is_required', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['default_role_id'], ['roles.id'], ondelete='SET NULL'),
    )
    
    # Unique constraint: one config per provider per tenant
    op.create_index(
        'ix_sso_configurations_tenant_provider',
        'sso_configurations',
        ['tenant_id', 'provider'],
        unique=True,
    )
    
    # Enable pg_trgm extension for fuzzy search suggestions
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    # Create RLS policies - Separated for asyncpg compatibility
    op.execute("ALTER TABLE oauth_connections ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY oauth_connections_tenant_isolation ON oauth_connections
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    op.execute("ALTER TABLE sso_configurations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY sso_configurations_tenant_isolation ON sso_configurations
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS sso_configurations_tenant_isolation ON sso_configurations')
    op.execute('DROP POLICY IF EXISTS oauth_connections_tenant_isolation ON oauth_connections')
    
    # Drop tables
    op.drop_table('sso_configurations')
    op.drop_table('oauth_connections')
