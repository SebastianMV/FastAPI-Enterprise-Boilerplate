-- Disable Row Level Security (Rollback)
-- =====================================
-- Run this to disable RLS if needed

-- Drop policies (including legacy superuser_bypass if they exist)
DROP POLICY IF EXISTS users_tenant_isolation ON users;
DROP POLICY IF EXISTS users_superuser_bypass ON users;
DROP POLICY IF EXISTS roles_tenant_isolation ON roles;
DROP POLICY IF EXISTS roles_superuser_bypass ON roles;
DROP POLICY IF EXISTS api_keys_user_isolation ON api_keys;
DROP POLICY IF EXISTS api_keys_superuser_bypass ON api_keys;
DROP POLICY IF EXISTS user_sessions_tenant_isolation ON user_sessions;
DROP POLICY IF EXISTS mfa_configs_user_isolation ON mfa_configs;

-- Disable RLS
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE roles DISABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE mfa_configs DISABLE ROW LEVEL SECURITY;

-- Remove FORCE
ALTER TABLE users NO FORCE ROW LEVEL SECURITY;
ALTER TABLE roles NO FORCE ROW LEVEL SECURITY;
ALTER TABLE api_keys NO FORCE ROW LEVEL SECURITY;
ALTER TABLE user_sessions NO FORCE ROW LEVEL SECURITY;
ALTER TABLE mfa_configs NO FORCE ROW LEVEL SECURITY;

-- Drop functions
DROP FUNCTION IF EXISTS get_current_tenant_id();
DROP FUNCTION IF EXISTS is_superuser_session();
DROP FUNCTION IF EXISTS set_updated_at();
