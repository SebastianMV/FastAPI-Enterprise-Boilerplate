"""Add Full-Text Search support (PostgreSQL FTS)

Revision ID: 005_full_text_search
Revises: 004_oauth_sso
Create Date: 2025-01-20

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_full_text_search"
down_revision = "004_oauth_sso"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pg_trgm extension for fuzzy matching (if not already enabled)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Add tsvector column to users table for full-text search
    op.add_column(
        "users", sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True)
    )

    # Create GIN index on users search_vector
    op.create_index(
        "ix_users_search_vector", "users", ["search_vector"], postgresql_using="gin"
    )

    # Create trigram index for fuzzy matching on user emails
    op.create_index(
        "ix_users_email_trgm",
        "users",
        ["email"],
        postgresql_using="gin",
        postgresql_ops={"email": "gin_trgm_ops"},
    )

    # Create function to update user search vector
    op.execute("""
        CREATE OR REPLACE FUNCTION users_search_vector_update() RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.email, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.first_name, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.last_name, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger to auto-update search vector
    op.execute("""
        CREATE TRIGGER users_search_vector_trigger
        BEFORE INSERT OR UPDATE OF email, first_name, last_name
        ON users
        FOR EACH ROW
        EXECUTE FUNCTION users_search_vector_update();
    """)

    # Update existing users to populate search vector
    op.execute("""
        UPDATE users SET
            search_vector = 
                setweight(to_tsvector('english', COALESCE(email, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(first_name, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(last_name, '')), 'B');
    """)

    # --- Add search capabilities to other tables ---

    # Add tsvector column to roles table
    op.add_column(
        "roles", sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True)
    )

    # Create GIN index on roles search_vector
    op.create_index(
        "ix_roles_search_vector", "roles", ["search_vector"], postgresql_using="gin"
    )

    # Create function to update role search vector
    op.execute("""
        CREATE OR REPLACE FUNCTION roles_search_vector_update() RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger for roles
    op.execute("""
        CREATE TRIGGER roles_search_vector_trigger
        BEFORE INSERT OR UPDATE OF name, description
        ON roles
        FOR EACH ROW
        EXECUTE FUNCTION roles_search_vector_update();
    """)

    # Update existing roles
    op.execute("""
        UPDATE roles SET
            search_vector = 
                setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(description, '')), 'B');
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS users_search_vector_trigger ON users")
    op.execute("DROP TRIGGER IF EXISTS roles_search_vector_trigger ON roles")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS users_search_vector_update()")
    op.execute("DROP FUNCTION IF EXISTS roles_search_vector_update()")

    # Drop indexes
    op.drop_index("ix_users_email_trgm", table_name="users")
    op.drop_index("ix_users_search_vector", table_name="users")
    op.drop_index("ix_roles_search_vector", table_name="roles")

    # Drop columns
    op.drop_column("users", "search_vector")
    op.drop_column("roles", "search_vector")

    # Note: Not dropping pg_trgm extension as it might be used elsewhere
