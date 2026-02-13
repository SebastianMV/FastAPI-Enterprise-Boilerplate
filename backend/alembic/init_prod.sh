#!/bin/bash
# ===========================================
# FastAPI Enterprise Boilerplate - Production Database Init
# ===========================================
# This script runs on first container startup (production).
# It creates the app_user role used for RLS enforcement.
# SECURITY: APP_USER_PASSWORD must be set before deploying.

set -euo pipefail

: "${APP_USER_PASSWORD:?APP_USER_PASSWORD environment variable must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v app_pass="$APP_USER_PASSWORD" \
     -v db_name="$POSTGRES_DB" <<-'EOSQL'
    -- Create extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";

    -- Enable Row-Level Security globally
    ALTER DATABASE :db_name SET row_security = on;

    -- Create non-owner application user for RLS enforcement
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
            CREATE ROLE app_user WITH LOGIN PASSWORD :'app_pass';
        END IF;
    END $$;

    -- Grant connect and usage
    GRANT CONNECT ON DATABASE :db_name TO app_user;
    GRANT USAGE ON SCHEMA public TO app_user;

    -- Grant DML privileges on all current and future tables
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;

    -- Grant sequence usage
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
EOSQL

echo "Production database initialized for FastAPI Enterprise Boilerplate"
