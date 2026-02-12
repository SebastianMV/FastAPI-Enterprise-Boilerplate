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
--
-- IMPORTANT: Superuser operations are handled at the APPLICATION layer
-- (e.g. temporarily resetting RLS context), NOT via a session variable.
-- Using a session variable like app.is_superuser would be insecure
-- because any DB user can SET arbitrary session variables.

-- Enable RLS on tenant-scoped tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;

-- Force RLS for table owners (prevents bypass even by table owner)
ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE roles FORCE ROW LEVEL SECURITY;

-- =============================================================================
-- USERS TABLE POLICIES
-- =============================================================================

-- Policy: Users can only see users in their tenant.
-- Uses COALESCE to return '' when the variable is unset, which will
-- never match any UUID — this is the SAFE fallback (zero rows returned).
CREATE POLICY users_tenant_isolation ON users
    FOR ALL
    USING (
        tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), '')
    )
    WITH CHECK (
        tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), '')
    );

-- =============================================================================
-- ROLES TABLE POLICIES
-- =============================================================================

-- Policy: Roles are tenant-scoped
CREATE POLICY roles_tenant_isolation ON roles
    FOR ALL
    USING (
        tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), '')
    )
    WITH CHECK (
        tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), '')
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

-- =============================================================================
-- API_KEYS TABLE POLICIES
-- =============================================================================

-- Enable RLS on api_keys table
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;

-- Policy: API keys are scoped to their owner user (which is tenant-scoped)
CREATE POLICY api_keys_user_isolation ON api_keys
    FOR ALL
    USING (
        user_id IN (
            SELECT id FROM users
            WHERE tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), '')
        )
    )
    WITH CHECK (
        user_id IN (
            SELECT id FROM users
            WHERE tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), '')
        )
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

COMMENT ON POLICY roles_tenant_isolation ON roles IS
    'Ensures roles are scoped to tenant';

COMMENT ON POLICY api_keys_user_isolation ON api_keys IS
    'Ensures API keys are scoped to users within the current tenant';

COMMENT ON FUNCTION get_current_tenant_id() IS
    'Returns the current tenant UUID from session variable';
