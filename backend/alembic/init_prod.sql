-- ===========================================
-- FastAPI Enterprise Boilerplate - Production Database Init
-- ===========================================
-- This script runs on first container startup (production).
-- It creates the app_user role used for RLS enforcement.

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enable Row-Level Security globally
ALTER DATABASE boilerplate SET row_security = on;

-- Create non-owner application user for RLS enforcement.
-- The owner (boilerplate) bypasses RLS, so the backend must connect as app_user.
-- SECURITY: Set APP_USER_PASSWORD environment variable before deploying.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'CHANGE_ME_BEFORE_DEPLOY';
        RAISE WARNING 'Created role app_user with default password – change it immediately via: ALTER ROLE app_user WITH PASSWORD ''<strong-password>'';';
    END IF;
END $$;

-- Grant connect and usage
GRANT CONNECT ON DATABASE boilerplate TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;

-- Grant DML privileges on all current and future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;

-- Grant sequence usage (for serial/bigserial columns)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

DO $$
BEGIN
    RAISE NOTICE 'Production database initialized for FastAPI Enterprise Boilerplate';
END $$;
