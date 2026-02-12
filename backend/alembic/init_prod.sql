-- ===========================================
-- FastAPI Enterprise Boilerplate - Production Database Init
-- ===========================================
--
-- !! DEPRECATED: DO NOT USE THIS FILE DIRECTLY !!
-- Use init_prod.sh instead, which reads APP_USER_PASSWORD from the environment.
--
-- docker-compose.prod.yml already mounts init_prod.sh correctly.
-- This .sql file is kept only as documentation reference.
--
-- If this file is accidentally mounted, it will REFUSE to create
-- the app_user role with a hardcoded password.
-- ===========================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enable Row-Level Security globally
ALTER DATABASE boilerplate SET row_security = on;

-- SECURITY: Refuse to create app_user with a hardcoded password.
-- Use init_prod.sh which reads APP_USER_PASSWORD from the environment.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        RAISE EXCEPTION 'FATAL: Do not use init_prod.sql directly. '
            'Use init_prod.sh instead, which reads APP_USER_PASSWORD '
            'from the environment. See docker-compose.prod.yml.';
    END IF;
END $$;

DO $$
BEGIN
    RAISE NOTICE 'Production database initialized for FastAPI Enterprise Boilerplate';
END $$;
