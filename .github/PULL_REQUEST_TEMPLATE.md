# Pull Request

## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Security hardening

## General Checklist

- [ ] Tests pass locally (`make test` or `Invoke-AllTests`)
- [ ] Code follows style guidelines (Ruff + ESLint pass)
- [ ] Self-reviewed my code
- [ ] Added tests for new features
- [ ] Updated documentation

## Security Checklist

> From Audit 24 retrospective: these checks prevent the top 10 recurring issue patterns.

### Backend (if applicable)
- [ ] **Input validation:** All new Pydantic fields have `max_length` / `Field()` constraints (use `ShortStr`, `NameStr`, `TextStr` from `schemas/common.py`)
- [ ] **Tenant isolation:** Endpoints that query data include `CurrentTenantId` and filter by `tenant_id`
- [ ] **Error messages:** No `str(e)` in HTTP responses — use generic messages, log the real error
- [ ] **Logging:** Logger calls use lazy `%s` formatting, not f-strings. No PII (emails, IPs) in log messages
- [ ] **Permissions:** Endpoints have appropriate `require_permission()` or `SuperuserId` guards
- [ ] **XSS:** Any user-controlled text rendered in HTML/PDF uses `html.escape()`

### Frontend (if applicable)
- [ ] **i18n:** No hardcoded user-visible strings — use `t()` calls (ESLint `i18next/no-literal-string` should catch most)
- [ ] **Error display:** No `error.message` or `detail.message` rendered to user — use generic i18n keys
- [ ] **Console:** No `console.error`/`console.log` without `import.meta.env.DEV` guard
- [ ] **URL params:** Path parameters use `encodeURIComponent()`, URL validation uses allowlists

### Infrastructure (if applicable)
- [ ] **Docker images:** Pinned to specific versions (no `:latest` tags)
- [ ] **Secrets:** No hardcoded secrets — use `${VAR:?must be set}` pattern
- [ ] **Containers:** Include `security_opt: no-new-privileges` + `cap_drop: ALL`

## Related Issues

Closes #(issue number)
