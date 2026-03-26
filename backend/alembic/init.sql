-- ===========================================
-- FastAPI-Enterprise-Boilerplate - Database Init
-- ===========================================
-- This script runs on first container startup
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
-- Grant privileges (for RLS support)
ALTER DATABASE boilerplate
SET row_security = on;
-- Create initial migration tracking table (Alembic will manage this)
-- This is just for documentation; Alembic creates its own table
-- Log initialization
DO $$ BEGIN RAISE NOTICE 'Database initialized for FastAPI-Enterprise-Boilerplate';
END $$;
