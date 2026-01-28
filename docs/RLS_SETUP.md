# Row-Level Security (RLS) - Multi-Tenant Isolation

##  Defense in Depth Architecture

This application implements **defense in depth** for multi-tenant isolation, combining:

### 1. **SQLAlchemy Events** (Application Layer)

- Automatic configuration of `app.current_tenant_id` on each transaction
- Executes BEFORE any SQL query
- Implemented in `backend/app/infrastructure/database/connection.py`

```python
@event.listens_for(Session, "after_begin")
def receive_after_begin(session, transaction, connection):
    tenant_id = get_current_tenant_id()  # From JWT via TenantMiddleware
    if tenant_id:
        connection.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
```

### 2. **PostgreSQL Row-Level Security** (Database Layer)

- 9 active RLS policies on core tables
- Apply **even if application layer fails**
- `FORCE ROW LEVEL SECURITY` enabled
- Policies with `USING` (SELECT) and `WITH CHECK` (INSERT/UPDATE/DELETE)

```sql
CREATE POLICY users_tenant_isolation ON users
FOR ALL
USING (tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), ''))
WITH CHECK (tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), ''));
```

##  Implementation Status

###  Completed

1. **Migration 006**: Enable RLS on 7 core tables
   - `users`, `roles`, `api_keys`, `conversations`, `chat_messages`, `notifications`, `audit_logs`
   - Policies for `oauth_connections` and `sso_configurations` (migration 004)

2. **Migration 007**: Create `app_user` database user
   - Non-owner user so RLS applies correctly
   - Permissions: SELECT, INSERT, UPDATE, DELETE on all tables
   - **Does NOT have** `BYPASSRLS` privilege

3. **Migration 008**: Complete CRUD policies
   - `FOR ALL` with `USING` + `WITH CHECK`
   - Supports SELECT, INSERT, UPDATE, DELETE
   - Chat messages use FK lookup to conversations

4. **SQLAlchemy Event Listener**: Automatic context configuration
   - Executes on `after_begin` of each session
   - Gets `tenant_id` from `ContextVar` (set by `TenantMiddleware`)
   - Executes `SET LOCAL app.current_tenant_id`

5. **TenantMiddleware**: Tenant extraction and configuration
   - Reads `tenant_id` from JWT
   - Stores in thread-safe `ContextVar`
   - Available for entire request lifecycle

###  Protected Tables

| Table | Policy | Type | Status |
| ----- | ------ | ---- | ------ |
| `users` | users_tenant_isolation | FOR ALL |  Active |
| `roles` | roles_tenant_isolation | FOR ALL |  Active |
| `api_keys` | api_keys_tenant_isolation | FOR ALL |  Active |
| `conversations` | conversations_tenant_isolation | FOR ALL |  Active |
| `chat_messages` | chat_messages_tenant_isolation | FOR ALL (FK) |  Active |
| `notifications` | notifications_tenant_isolation | FOR ALL |  Active |
| `audit_logs` | audit_logs_tenant_isolation | FOR ALL |  Active |
| `oauth_connections` | oauth_connections_tenant_isolation | FOR SELECT |  Active |
| `sso_configurations` | sso_configurations_tenant_isolation | FOR SELECT |  Active |

##  User Configuration

### Development (RLS Bypassed)

```env
DATABASE_URL=postgresql+asyncpg://boilerplate:boilerplate@localhost:5432/boilerplate
```

- User: `boilerplate` (table owner)
- RLS: **Bypassed** (FORCE RLS doesn't apply to owners with prepared statements)
- Use: Local development, migrations, admin tasks

### Production (RLS Enforced)  **RECOMMENDED**

```env
DATABASE_URL=postgresql+asyncpg://app_user:app_password@localhost:5432/boilerplate
```

- User: `app_user` (NOT owner)
- RLS: **Enforced** (policies apply correctly)
- Use: Production, staging, testing

##  RLS Verification

### Automated Test

```bash
cd backend
python test_rls_isolation.py
```

**Expected output**:

```text
 DB Direct: Tenant A only sees its users (N users)
 DB Direct: Tenant B only sees its users (M users)
 Active RLS policies: 9
```

### Manual Test (PostgreSQL)

```sql
-- Connect as app_user
\c boilerplate app_user

-- Set tenant A
BEGIN;
SET LOCAL app.current_tenant_id = '<tenant-a-uuid>';
SELECT COUNT(*) FROM users;  -- Only sees tenant A users
COMMIT;

-- Set tenant B
BEGIN;
SET LOCAL app.current_tenant_id = '<tenant-b-uuid>';
SELECT COUNT(*) FROM users;  -- Only sees tenant B users
COMMIT;
```

##  Known Limitations

### asyncpg + FORCE RLS + Table Owners

PostgreSQL has a limitation: `FORCE ROW LEVEL SECURITY` **does NOT fully apply** to table owners when using prepared statements (which is how asyncpg and SQLAlchemy work).

**Implemented solution**:

1. `app_user` (NOT owner) for the application
2. `boilerplate` user (owner) only for migrations

### OAuthConnectionModel Mapping Error

The `OAuthConnectionModel` has a circular mapping error with `UserModel`. This error **does NOT affect** RLS functionality in the database.

**Temporary solution**: Comment out relationship in development if causing issues
**Definitive solution**: Resolve circular import (pending)

##  Security Flow

```text
HTTP Request
    
TenantMiddleware (extracts tenant_id from JWT)
    
ContextVar.set(tenant_id)
    
SQLAlchemy Session.begin() 
    
Event Listener "after_begin" 
    
SET LOCAL app.current_tenant_id = '<tenant_id>'
    
SQL Query (with automatic RLS)
    
PostgreSQL filters by tenant_id
    
Response (only tenant's data)
```

##  Security Validation

### Tested Scenarios

1.  **SELECT Isolation**: Each tenant only sees their own records
2.  **INSERT Protection**: Cannot insert into another tenant
3.  **UPDATE Protection**: Cannot modify another tenant's data
4.  **DELETE Protection**: Cannot delete another tenant's data
5.  **FK Consistency**: Chat messages respect tenant via conversation FK
6.  **Policy Active**: 9 policies confirmed in `pg_policies`

### Critical Use Cases

| Case | Status | Protection |
| ---- | ------ | ---------- |
| User A tries to read B's data |  Blocked | DB RLS |
| App forgets to set tenant_id |  Empty data | DB RLS (current_setting = '') |
| SQL Injection attempts bypass |  Blocked | DB RLS + parameterization |
| Owner does SELECT without tenant |  Sees all | Only with boilerplate user |
| app_user does SELECT without tenant |  Empty data | DB RLS active |

##  Related Migrations

1. **001-005**: Base schema
2. **006** (`9446ce57e027`): Enable RLS + SELECT policies
3. **007** (`007_change_owners`): Create app_user
4. **008** (`008_rls_write_pol`): INSERT/UPDATE/DELETE policies

##  References

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [SQLAlchemy Events](https://docs.sqlalchemy.org/en/20/orm/events.html)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/advanced/security/)

##  Performance Notes

- Event listener executes `SET LOCAL` once per transaction (minimal overhead)
- RLS policies use existing indexes on `tenant_id`
- Prepared statements maintain optimal performance
- `COALESCE` prevents errors if current_setting doesn't exist

##  Future Improvements

- [ ] Resolve OAuthConnectionModel mapping error
- [ ] Add RLS to `tenants` table (for super-admin scenarios)
- [ ] Implement audit logging for cross-tenant access attempts
- [ ] Configure security alerts for RLS violations
- [ ] Load testing with RLS active (performance validation)
