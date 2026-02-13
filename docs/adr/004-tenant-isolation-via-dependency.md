# ADR-004: Tenant Isolation via CurrentTenantId Dependency

- **Date:** 2025-08-10
- **Status:** Accepted
- **Author:** Sebastián Muñoz

## Context

The application is multi-tenant with PostgreSQL Row-Level Security (RLS). Every data query
must be scoped to the current tenant to prevent cross-tenant data leakage.

Across audits, **missing tenant isolation** was the #5 root cause (~30 issues):
- Endpoints querying data without filtering by tenant_id
- Bulk operations bypassing tenant context
- Admin endpoints accidentally exposing cross-tenant data

Simply relying on middleware to set `SET app.current_tenant_id` for RLS is insufficient —
it's invisible at the endpoint level and easy to forget when writing new queries.

## Decision

Every data-accessing endpoint MUST declare `tenant_id: CurrentTenantId` as a dependency:

```python
from app.api.v1.deps import CurrentTenantId

@router.get("/items")
async def list_items(
    tenant_id: CurrentTenantId,  # ← MANDATORY
    # ... other params
):
    items = await item_service.list_by_tenant(tenant_id)
```

`CurrentTenantId` is a FastAPI `Depends()` that:
1. Extracts tenant from the authenticated user's JWT claims
2. Sets the PostgreSQL session variable for RLS: `SET app.current_tenant_id = '{id}'`
3. Returns the UUID for explicit use in application queries
4. Raises 403 if tenant context is missing or invalid

## Consequences

### Positive

- **Explicit contract** — every endpoint visibly declares tenant scope
- **Double protection** — RLS at DB level + explicit filtering at app level
- **Reviewable** — code reviews can verify tenant_id presence in endpoint signatures
- **Enforceable** — Semgrep rule `endpoint-missing-tenant-id` catches omissions

### Negative

- **Verbosity** — every data endpoint has an extra parameter
- **Not needed for global endpoints** — health check, auth, etc. must be explicitly excluded
- **Dependency injection depth** — adds one more layer to the DI chain

### Neutral

- Admin/superuser endpoints still receive tenant_id but may query cross-tenant with explicit
  permission checks

## Alternatives Considered

### Middleware-Only RLS

Set `app.current_tenant_id` in middleware and rely entirely on PostgreSQL RLS. Rejected because:
- Invisible at endpoint level — no way to verify in code review
- If middleware fails silently, all data is exposed
- Application-level queries (joins, aggregations) may bypass RLS

### Tenant in URL Path (`/tenants/{tenant_id}/items`)

Explicit tenant in URL. Rejected because:
- Adds complexity to every route
- Users shouldn't choose their tenant — it comes from their JWT
- URL-based tenant can be tampered with (IDOR risk)

### Global Context Variable (contextvars)

Store tenant in `contextvars.ContextVar`. Rejected because:
- Invisible in endpoint signatures (same problem as middleware-only)
- Harder to test — requires manual context setup
- No IDE autocompletion or type checking

## References

- Audits 4, 7, 12, 16: Tenant isolation issues
- `backend/app/api/v1/deps.py`: `CurrentTenantId` implementation
- `docs/RLS_SETUP.md`: PostgreSQL RLS configuration
- Semgrep rule: `.semgrep/backend-security.yml` → `endpoint-missing-tenant-id`
- Skill: `.agents/skills/multi-tenant-security/SKILL.md`
