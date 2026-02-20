# Project Status & Roadmap

**Version:** v0.9.5
**Date:** February 20, 2026
**Status:** Beta feature-complete, 43 security audit cycles passed

---

## Executive Summary

**FastAPI Enterprise Boilerplate** is a full-stack enterprise boilerplate with
JWT authentication, granular ACL, multi-tenant RLS, and hexagonal architecture.
The backend has 99% test coverage and has undergone **41 security audit cycles**
covering 700+ individual hardening items. The React frontend is fully functional
with 568 tests passing (statement coverage ~32%, CI threshold 30%, v1.0.0 target 50%).

### Quality Metrics

| Metric                    | Value                                | Status  |
| ------------------------- | ------------------------------------ | ------- |
| Backend Unit Tests        | ~3,500 passing                       | OK      |
| Backend Integration Tests | ~247 passing                         | OK      |
| Backend E2E Tests         | 20/84 passing (63 skipped)           | Partial |
| Frontend Unit Tests       | 568/568 passing                      | OK      |
| Backend Coverage          | 99% (smoke gate)                     | OK      |
| Frontend Coverage         | ~32% statements (threshold 30%, target 50%) | Partial |
| Type Check (Python/MyPy)  | 282 errores en 56 archivos (baseline en repo, gate anti-regresión activo) | Partial |
| Type Errors (TypeScript)  | 0                                    | OK      |
| Docker Services           | 4/4 healthy                          | OK      |
| Alembic Migrations        | 12 applied                           | OK      |
| Security Audits Passed    | 43 cycles (0 open critical/high issues) | OK  |

---

## What's Implemented

### Core Features

| Feature                     | Notes                                                                |
| --------------------------- | -------------------------------------------------------------------- |
| JWT Auth (access + refresh) | HttpOnly cookies + Bearer fallback + audience validation             |
| MFA/2FA (TOTP + Email OTP)  | Fernet-encrypted secrets, SHA-256 hashed OTPs                        |
| API Keys                    | CRUD + scoped permissions + ACL                                      |
| Password Recovery           | Redis-backed tokens (SHA-256 hashed) + rate limiting                 |
| Multi-tenant RLS            | PostgreSQL Row-Level Security + cross-tenant isolation               |
| OAuth2 SSO                  | Google, GitHub, Microsoft, Discord (encrypted client secrets)        |
| WebSocket + Notifications   | Real-time push via Redis pub/sub, cookie-based auth                  |
| Full-Text Search            | PostgreSQL tsvector with parameterized queries                       |
| Pluggable Storage           | Local / S3 / MinIO (async I/O, path traversal protection)            |
| Pluggable Email             | SMTP / Console / SendGrid                                            |
| i18n                        | EN 100%, ES ~96%, PT 100% cobertura de claves (3 locales)            |
| Data Exchange               | Import / Export / PDF & Excel reports (formula injection protection) |
| Bulk Operations API         | Batch CRUD with tenant isolation                                     |
| CSRF Protection             | Double-submit cookie with per-request rotation                       |
| ErrorBoundary               | React class component catch-all                                      |
| Global Exception Handlers   | Domain exceptions mapped to HTTP responses                           |

### Security Hardening (38 Audit Cycles)

| Category          | Items Resolved             |
| ----------------- | -------------------------- |
| Backend security  | ~200 issues (sev 6-10)     |
| Frontend security | ~120 issues (sev 6-10)     |
| Infrastructure    | ~100 issues (sev 6-10)     |
| i18n hardcoding   | ~150 strings to i18n calls |
| Tests updated     | ~40 test files             |

Key areas: tenant isolation, timing-safe comparisons, generic error messages,
CSV/Excel formula injection, HTML/XSS escaping, PII redaction in logs, encrypted
secrets, container hardening, supply chain pinning, Semgrep rules, WCAG accessibility.

### Backend Endpoints (15 groups)

auth, users, roles, tenants, api-keys, mfa, health, ws, notifications,
oauth, search, dashboard, data, bulk, report-templates

### Frontend (18 pages, all lazy-loaded)

Auth (Login, Register, Forgot/Reset Password, OAuth callback, Email verify),
Dashboard, Users, Profile + Avatar, Settings, API Keys, MFA, Sessions,
Audit Log, Notifications, Search, Roles (admin), Tenants (admin),
Data Exchange (admin)

---

## What's NOT Implemented

| Feature                 | Reality                                |
| ----------------------- | -------------------------------------- |
| SAML 2.0 SSO            | Fully deleted in v0.9.0                |
| LDAP / Active Directory | Fully deleted in v0.9.0                |
| SMS 2FA                 | Not implemented (extension point only) |
| Webhooks                | Not implemented                        |
| GraphQL                 | Not implemented                        |
| Payments                | Not implemented                        |

---

## Docker Stack

| Service                 | Port (dev)     | Port (prod)               |
| ----------------------- | -------------- | ------------------------- |
| backend                 | 127.0.0.1:8000 | expose only (nginx proxy) |
| frontend (Vite / Nginx) | 3000           | 80                        |
| PostgreSQL 17.2         | 127.0.0.1:5432 | 127.0.0.1:5432            |
| Redis 7.4               | 127.0.0.1:6379 | 127.0.0.1:6379            |
| Test DB                 | 127.0.0.1:5433 | --                        |
| Test Redis              | 127.0.0.1:6380 | --                        |

All containers run with security_opt: no-new-privileges, cap_drop: ALL,
pids_limit, and pinned image tags.

---

## Roadmap to v1.0.0

### Completed Milestones

| Milestone                                    | Status                      |
| -------------------------------------------- | --------------------------- |
| v0.9.1 -- Security Hardening                 | Done                        |
| v0.9.2 -- Frontend Quality                   | Done (568 tests, i18n ~96%) |
| v0.9.3 -- Backend Hardening                  | Done                        |
| v0.9.4 -- DevOps & CI                        | Done                        |
| v0.9.5 -- Security Audit Cycle (22 audits)              | Done        |
| Post-v0.9.5 -- Security Audit Cycles N°36-41 (backend, frontend, infra) | Done |
| Post-v0.9.5 -- Security Audit N°42 (Semgrep + AST scan)                | Done |
| Post-v0.9.5 -- Security Audit N°43 (manual, 2 issues fixed)            | Done |

### v1.0.0 -- Production Release

| Prerequisite                               | Status         |
| ------------------------------------------ | -------------- |
| All severity >= 5 items resolved           | Done           |
| 43 security audit cycles passed (0 open critical/high since N°39) | Done |
| Frontend tests >= 50% coverage             | Pending (~32%) |
| All i18n locales >= 95%                    | Done           |
| Container hardening (non-root, caps, pids) | Done           |
| Supply chain pinning (images, CI actions)  | Done           |
| Semgrep automated rules                    | Done           |

**Remaining blockers:** Frontend statement coverage target (~32% to 50%) and
backend MyPy debt before re-enabling strict blocking gate.

---

## Pre-Production Security Checklist

- Set a strong, unique JWT_SECRET_KEY (>= 32 chars)
- Set a strong, unique ENCRYPTION_KEY
- Set a strong REDIS_PASSWORD
- Set POSTGRES_PASSWORD (no defaults)
- Set APP_USER_PASSWORD for RLS enforcement
- Disable /docs and /redoc (ENVIRONMENT=production)
- Configure CORS_ORIGINS to exact frontend domain
- Set AUTH_COOKIE_SECURE=true + AUTH_COOKIE_SAMESITE=strict
- Set CSRF_ENABLED=true
- Enable HTTPS (TLS termination at Nginx or LB)
- Change seed user passwords
- Run alembic upgrade head post-deploy
- Review and tune rate limits
- Enable OpenTelemetry + Prometheus monitoring

---

## Development Credentials

| Email               | Password    | Role       |
| ------------------- | ----------- | ---------- |
| admin@example.com   | Admin123!   | Superadmin |
| manager@example.com | Manager123! | Manager    |
| user@example.com    | User123!    | User       |

Change these in production.

---

## Documentation

Documentation is consolidated in [docs/README.md](docs/README.md) as the canonical index.

Primary project documents:

- [README.md](README.md) — Quick start and overview
- [CHANGELOG.md](CHANGELOG.md) — Version history
- [CONTRIBUTING.md](CONTRIBUTING.md) — Contribution guidelines
- [MAKEFILE.md](MAKEFILE.md) — Make/PowerShell command reference
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md) — Latest security audit report (N°43)
- [docs/ROADMAP_1_0_OPERATIONAL_PLAN.md](docs/ROADMAP_1_0_OPERATIONAL_PLAN.md) — v1.0.0 release plan

Audit tools (static AST + Semgrep scan):

- `backend/scripts/audit_scan.py` — canonical AST-based scanner
- `backend/scripts/build_audit_tables.py` — Markdown report generator
- `.semgrep/` — custom Semgrep YAML rules

---

**Maintained by:** Sebastian Munoz
**License:** MIT
