-- ===========================================
-- FastAPI-Enterprise-Boilerplate - Test Database Init
-- ===========================================
-- This script runs on first test container startup
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
-- Grant privileges (for RLS support)
ALTER DATABASE test_boilerplate
SET row_security = on;
-- Create non-owner application user for RLS validation in tests.
-- This mirrors production where `app_user` is used to enforce RLS.
-- Tests should connect as app_user to verify tenant isolation at DB level.
DO $$ BEGIN IF NOT EXISTS (
    SELECT
    FROM pg_catalog.pg_roles
    WHERE rolname = 'app_user'
) THEN CREATE ROLE app_user WITH LOGIN PASSWORD 'test_app_user_password';
END IF;
END $$;
GRANT CONNECT ON DATABASE test_boilerplate TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT,
    INSERT,
    UPDATE,
    DELETE ON TABLES TO app_user;
GRANT SELECT,
    INSERT,
    UPDATE,
    DELETE ON ALL TABLES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE,
    SELECT ON SEQUENCES TO app_user;
GRANT USAGE,
    SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
-- Log initialization
DO $$ BEGIN RAISE NOTICE 'Test database initialized for FastAPI-Enterprise-Boilerplate';
END $$;
