-- ===========================================
-- FastAPI Enterprise Boilerplate - Test Database Init
-- ===========================================
-- This script runs on first test container startup

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Test database initialized for FastAPI Enterprise Boilerplate';
END $$;
