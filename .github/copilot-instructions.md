<!-- Derived from AGENTS.md — keep in sync -->

# Copilot Instructions — FastAPI-Enterprise-Boilerplate

## Project Context

Full-stack enterprise boilerplate: FastAPI + React 19 + PostgreSQL 17 + Redis.
Architecture: Hexagonal (Ports & Adapters). Auth: JWT via HttpOnly cookies + CSRF.
Multi-tenant with PostgreSQL RLS. See AGENTS.md for full context.

## Critical Rules (from 994 security fixes)

### Backend (Python)

1. **Logger**: `from app.infrastructure.observability.logging import get_logger` — NEVER `import logging`
2. **Error responses**: Generic messages only — NEVER `str(e)` or `f"Error: {e}"` in HTTP responses
3. **Logging format**: `logger.info("action", key=val)` — NEVER `logger.info(f"...")`
4. **Tenant isolation**: Every data endpoint MUST have `tenant_id: CurrentTenantId` parameter
5. **Permissions**: Use `require_permission("resource", "action")` — not just `CurrentUser`
6. **Input validation**: Use `NameStr`, `ShortStr`, `TextStr` from `schemas/common.py` — NEVER bare `str`
7. **Async**: All I/O must be `await`ed. No `subprocess.run()`, no sync Redis
8. **Timing-safe**: `hmac.compare_digest()` for token/secret comparisons — NEVER `==`
9. **HTML**: `html.escape(user_input)` before interpolation into HTML strings
10. **Datetime**: `datetime.now(UTC)` — NEVER `datetime.utcnow()`

### Frontend (TypeScript/React)

11. **i18n**: ALL user-visible strings MUST use `t('key')` — zero hardcoded English
12. **Error display**: `t('resource.genericError')` — NEVER `error.message` or `response.detail`
13. **Console**: Only inside `if (import.meta.env.DEV)` blocks
14. **URL params**: `encodeURIComponent(id)` in all API URL interpolations
15. **Hooks**: useEffect MUST have cleanup (AbortController). Wrap callbacks in useCallback

### Infrastructure

16. **Docker images**: Pin to minor version (e.g., `postgres:17.2-alpine`)
17. **Secrets**: `${VAR:?must be set}` in staging/prod — NEVER `${VAR:-default}`
18. **Containers**: Always `security_opt: no-new-privileges` + `cap_drop: ALL`
19. **GitHub Actions**: Pin to commit SHA, not version tag

## Pydantic Types (use instead of bare `str`)

```python
from app.api.v1.schemas.common import ShortStr, NameStr, TextStr, UrlStr, TokenStr, ScopeStr
```

## Architecture Decisions (DO NOT revert)

- HttpOnly cookies for JWT (not localStorage) — [ADR-001](../docs/adr/001-httponly-cookies-for-jwt.md)
- CSRF double-submit with X-CSRF-Token header — [ADR-002](../docs/adr/002-csrf-double-submit-pattern.md)
- `get_logger()` centralized (structured logging with request_id, tenant_id) — [ADR-003](../docs/adr/003-centralized-structured-logging.md)
- `CurrentTenantId` dependency for tenant isolation — [ADR-004](../docs/adr/004-tenant-isolation-via-dependency.md)
- Hexagonal architecture (no business logic in endpoints) — [ADR-005](../docs/adr/005-hexagonal-architecture.md)

## File Conventions

- Backend endpoints: `backend/app/api/v1/endpoints/`
- Schemas: `backend/app/api/v1/schemas/`
- Use cases: `backend/app/application/use_cases/`
- Domain entities: `backend/app/domain/entities/`
- Frontend pages: `frontend/src/pages/`
- i18n files: `frontend/src/i18n/locales/` and `frontend/public/locales/`

## Dev Credentials

- admin@example.com / Admin123! (Superadmin)
- manager@example.com / Manager123! (Manager)
- user@example.com / User123! (User)
