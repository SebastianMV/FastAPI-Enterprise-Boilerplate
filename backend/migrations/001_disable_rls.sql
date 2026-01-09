-- Disable Row Level Security (Rollback)
-- =====================================
-- Run this to disable RLS if needed

-- Drop policies
DROP POLICY IF EXISTS users_tenant_isolation ON users;
DROP POLICY IF EXISTS users_superuser_bypass ON users;
DROP POLICY IF EXISTS roles_tenant_isolation ON roles;
DROP POLICY IF EXISTS roles_superuser_bypass ON roles;

-- Disable RLS
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE roles DISABLE ROW LEVEL SECURITY;

-- Remove FORCE
ALTER TABLE users NO FORCE ROW LEVEL SECURITY;
ALTER TABLE roles NO FORCE ROW LEVEL SECURITY;

-- Drop functions
DROP FUNCTION IF EXISTS get_current_tenant_id();
DROP FUNCTION IF EXISTS is_superuser_session();
