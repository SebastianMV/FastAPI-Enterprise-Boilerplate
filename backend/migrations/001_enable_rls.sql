-- Row Level Security (RLS) Policies for Multi-Tenant Isolation
-- ============================================================
--
-- This migration sets up PostgreSQL RLS to automatically filter
-- all queries by tenant_id based on the session variable.
--
-- How it works:
-- 1. Application sets: SET LOCAL app.current_tenant_id = '<uuid>'
-- 2. RLS policies automatically filter: WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
--
-- Security guarantee: Even if application code forgets to filter,
-- PostgreSQL will enforce tenant isolation at the database level.

-- Enable RLS on tenant-scoped tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;

-- Force RLS for table owners (prevents bypass by superuser in app)
ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE roles FORCE ROW LEVEL SECURITY;

-- =============================================================================
-- USERS TABLE POLICIES
-- =============================================================================

-- Policy: Users can only see users in their tenant
CREATE POLICY users_tenant_isolation ON users
    FOR ALL
    USING (
        tenant_id::text = current_setting('app.current_tenant_id', true)
        OR current_setting('app.current_tenant_id', true) IS NULL
        OR current_setting('app.current_tenant_id', true) = ''
    )
    WITH CHECK (
        tenant_id::text = current_setting('app.current_tenant_id', true)
    );

-- Policy: Allow superusers to bypass RLS (for admin operations)
-- This uses a separate session variable
CREATE POLICY users_superuser_bypass ON users
    FOR ALL
    USING (
        current_setting('app.is_superuser', true) = 'true'
    )
    WITH CHECK (
        current_setting('app.is_superuser', true) = 'true'
    );

-- =============================================================================
-- ROLES TABLE POLICIES
-- =============================================================================

-- Policy: Roles are tenant-scoped
CREATE POLICY roles_tenant_isolation ON roles
    FOR ALL
    USING (
        tenant_id::text = current_setting('app.current_tenant_id', true)
        OR current_setting('app.current_tenant_id', true) IS NULL
        OR current_setting('app.current_tenant_id', true) = ''
    )
    WITH CHECK (
        tenant_id::text = current_setting('app.current_tenant_id', true)
    );

-- Policy: Allow superusers to bypass RLS
CREATE POLICY roles_superuser_bypass ON roles
    FOR ALL
    USING (
        current_setting('app.is_superuser', true) = 'true'
    )
    WITH CHECK (
        current_setting('app.is_superuser', true) = 'true'
    );

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to get current tenant ID
CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_tenant_id', true), '')::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to check if current session is superuser
CREATE OR REPLACE FUNCTION is_superuser_session()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN COALESCE(current_setting('app.is_superuser', true) = 'true', false);
EXCEPTION
    WHEN OTHERS THEN
        RETURN false;
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- API_KEYS TABLE POLICIES
-- =============================================================================

-- Enable RLS on api_keys table
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;

-- Policy: API keys are scoped to their owner user (which is tenant-scoped)
-- Users can only see their own API keys
CREATE POLICY api_keys_user_isolation ON api_keys
    FOR ALL
    USING (
        user_id IN (
            SELECT id FROM users 
            WHERE tenant_id::text = current_setting('app.current_tenant_id', true)
        )
        OR current_setting('app.current_tenant_id', true) IS NULL
        OR current_setting('app.current_tenant_id', true) = ''
    )
    WITH CHECK (
        user_id IN (
            SELECT id FROM users 
            WHERE tenant_id::text = current_setting('app.current_tenant_id', true)
        )
    );

-- Policy: Allow superusers to bypass RLS
CREATE POLICY api_keys_superuser_bypass ON api_keys
    FOR ALL
    USING (
        current_setting('app.is_superuser', true) = 'true'
    )
    WITH CHECK (
        current_setting('app.is_superuser', true) = 'true'
    );

-- =============================================================================
-- TENANTS TABLE (No RLS - root entity)
-- =============================================================================

-- Tenants table does NOT have RLS as it's the root of the hierarchy
-- Access control is handled at the application level (superuser only)

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON POLICY users_tenant_isolation ON users IS 
    'Ensures users can only access records within their tenant';

COMMENT ON POLICY users_superuser_bypass ON users IS 
    'Allows superusers to bypass RLS for administrative operations';

COMMENT ON POLICY roles_tenant_isolation ON roles IS 
    'Ensures roles are scoped to tenant';

COMMENT ON POLICY roles_superuser_bypass ON roles IS 
    'Allows superusers to bypass RLS for administrative operations';

COMMENT ON POLICY api_keys_user_isolation ON api_keys IS 
    'Ensures API keys are scoped to users within the current tenant';

COMMENT ON POLICY api_keys_superuser_bypass ON api_keys IS 
    'Allows superusers to bypass RLS for administrative operations';

COMMENT ON FUNCTION get_current_tenant_id() IS 
    'Returns the current tenant UUID from session variable';

COMMENT ON FUNCTION is_superuser_session() IS 
    'Returns true if current session has superuser privileges';
