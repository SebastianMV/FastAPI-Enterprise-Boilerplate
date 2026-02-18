# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- Audit cycles N°36, N°37 and N°38 completed (backend + frontend scope, excluding infrastructure)
- Resolved tenant isolation gaps in search admin endpoints by enforcing `CurrentTenantId` in `create_index` and `delete_index`
- Hardened OAuth callback redirect validation to require valid `http/https` scheme plus exact allowlisted origin match
- Updated static audit scanner rules to reduce false positives (superuser dependency recognition, context-aware redirect checks, DEV-guarded console detection)

### Changed

- Kept reusable audit tooling and machine-readable outputs under `audit36_static/`, `audit37_static/`, and `audit38_static/`
- Removed obsolete markdown report artifacts from Audit36 to reduce repository noise while preserving executable scanners

### Maintenance

- Cleaned temporary local debugging artifacts generated during Python/SQLAlchemy diagnostics
- Added `.gitignore` rules for backend diagnostic scripts/logs to keep future commits clean

## [0.9.5] - 2026-02-11

### Security (22 Audit Cycles 700+ items resolved)

This release represents a comprehensive security hardening effort across 22
audit cycles, resolving 700+ individual issues (severity 610).

**Authentication & Authorization:**

- JWT audience claim validation (prevents token confusion between apps)
- Superuser DB check on every request (not just JWT claims)
- Inactive user rejection (is_active=False returns 403)
- Login timing enumeration prevention (dummy bcrypt on unknown users)
- Forgot-password constant-time delay (prevents email enumeration)
- MFA secrets encrypted with Fernet before Redis storage
- OTP codes stored as SHA-256 hashes in Redis
- JTI hashing changed from bcrypt to SHA-256 (~10,000x faster)
- Backup codes use timing-safe comparison (hmac.compare_digest)
- Refresh token blacklist check before issuing new tokens
- Logout blacklists both access and refresh tokens
- Session revocation on password change and reset (fail-closed in prod)
- Token issuance gated on EMAIL_VERIFICATION_REQUIRED
- Email verification tokens stored as SHA-256 hashes
- Verification moved from GET query param to POST body
- CSRF per-request rotation on state-changing requests
- CSRF exempt paths use exact set membership (not prefix matching)
- OAuth access tokens include extra_claims (is_superuser, roles)
- OAuth client_secret encrypted at rest (encrypt_value/decrypt_value)
- OAuth domain allowlist enforcement per SSO provider
- OAuth email_verified check before auto-linking accounts
- OAuth TOCTOU race condition handled with retry-as-lookup
- OAuth callback uses generic error messages (no provider detail leak)
- OAuth redirect URL validated against HTTPS in prod/staging
- OAuth open redirect prevention (netloc comparison, not startswith)
- Rate limits on forgot-password (3/60) and reset-password (5/60)

**Tenant Isolation:**

- Cross-tenant checks in users, roles, bulk, dashboard, notifications,
  audit logs, report templates, search, OAuth identity linking
- list_users filtered by CurrentTenantId at repository level
- Bulk operations verify tenant ownership before mutations
- Role assignment validates user/role belong to same tenant
- Audit log resource history filtered by tenant_id at DB level
- Report templates strictly filtered by tenant (no cross-tenant public)
- Notifications CRUD filtered by tenant_id

**Input Validation & Error Messages:**

- Reflected input eliminated from ~50 error messages (UUIDs, emails, roles,
  slugs, domains, action types, file paths, content types)
- max_length constraints added to all schema string fields
- pids_limit, LIKE wildcard escaping, FTS language whitelist
- SQL bind params for LIMIT/OFFSET in FTS queries
- Path traversal blocked in report storage_path
- Avatar upload: extension allowlist + magic byte validation
- Data exchange: server-side 50MB file size check
- Request-ID validation (regex, invalid IDs replaced by UUID)
- Format string injection prevention in i18n interpolation
- CSV/Excel formula injection protection (\_sanitize_formula)
- HTML escaping in PDF/report generation (prevents stored XSS)
- CSS injection prevention in WeasyPrint (\_escape_css_string)
- Generic error messages in all user-facing responses (no str(e) leaks)

**Infrastructure Hardening:**

- All Docker images pinned to specific versions (postgres:17.2-alpine,
  redis:7.4-alpine, nginx:1.27-alpine, python:3.13-slim, node:22-alpine)
- All containers: security_opt no-new-privileges, cap_drop ALL
- pids_limit on all containers (100-200)
- tmpfs mounts with noexec,nosuid,nodev and size limits
- stop_grace_period on backend/db/frontend/redis
- Network segmentation (frontend/backend networks, internal: true)
- Log rotation (json-file, 50m, max-file 5) on all containers
- Prod backend: ports replaced by expose (nginx proxy only)
- All env vars with :?must be set (fail-safe, no defaults in prod/staging)
- init_prod.sh with heredoc quoting (no shell expansion)
- nginx: rate limiting zones (api 30r/s, auth 5r/s, ws 10r/s)
- nginx: security headers on all locations (including /health, /, /assets/)
- nginx: CSP connect-src scoped (removed bare wss:)
- nginx: proxy_hide_header X-Powered-By on all locations
- nginx: WebSocket headers only on /ws (removed from /api/)
- nginx: Cache-Control no-store on SPA fallback
- nginx: /api/v1/data-exchange/ with client_max_body_size 50m
- GitHub Actions pinned to commit SHAs
- CI: concurrency group with cancel-in-progress
- CI: build job gated on all check jobs
- CI: pip-audit + npm audit + bandit + semgrep in security job
- CI: ENCRYPTION_KEY + ENVIRONMENT=testing in backend-test
- CI: frontend tests with coverage upload to Codecov
- Semgrep custom rules (backend, frontend, infrastructure)
- Dependabot: pip + npm + github-actions + docker ecosystems
- Trivy pinned to SHA for supply chain security
- pre-commit semgrep org updated (returntocorp -> semgrep)

**Frontend Hardening:**

- All token read/write removed from localStorage
- Auth state restored from cookies via fetchUser() on mount
- isInitializing state prevents flash redirect during rehydration
- Shared refreshPromise mutex prevents concurrent 401 refresh calls
- 401/403 responses skip React Query retry
- WebSocket payload runtime validation before cast
- Notification dedup by ID (prevents WebSocket replay duplicates)
- isSafeActionUrl() validates notification action URLs
- OAuth provider allowlist prevents path traversal
- encodeURIComponent on all dynamic URL path segments (~30 sites)
- OAuth redirect URL validated as https://
- QR code src validated as data:image/ URI
- AbortController on SearchBar and SearchPage (cancel stale requests)
- Focus trap in Modal (Tab/Shift+Tab confined, WCAG 2.4.3)
- LanguageSelector: hover dropdown changed to click-based with aria
- console.error gated behind import.meta.env.DEV in production
- sessionStorage for recent searches (was localStorage)
- URL.revokeObjectURL deferred with setTimeout for download completion

**i18n Completeness:**

- ~150 hardcoded strings migrated to t() calls across 20+ components
- All error messages use i18n keys (no raw backend messages rendered)
- Aria labels, placeholders, alt text fully internationalized
- EN/ES/PT coverage: ~50 new key groups added

**Logging & Observability:**

- All files migrated from import logging to get_logger()
- ~80 f-string logger calls converted to lazy %s formatting
- PII removed from logs (emails hashed, user_ids redacted from activity)
- hashlib.md5 calls use usedforsecurity=False
- Exception details use type(e).**name** instead of str(e)
- Silent except blocks now log warnings

### Added

- **encryption.py:** Fernet encryption utility (encrypt_value/decrypt_value)
- **close_cache():** Graceful Redis shutdown in lifespan
- **close_database():** Graceful DB shutdown in lifespan
- **hash_jti():** SHA-256 based JTI hashing
- **emitLogout():** Custom event-based 401 redirect for SPA
- **formatRelativeTime.ts:** Shared utility (deduplicated from 3 components)
- **init_prod.sh:** Shell script for prod DB user creation (replaces SQL)
- **Semgrep rules:** backend-security.yml, frontend-security.yml, infrastructure-security.yml
- **alembic migration 012:** security_features
- **WebSocket limits:** MAX_CONNECTIONS_PER_USER=5, MAX_TOTAL_CONNECTIONS=500, 64KB message limit

### Changed

- **Version:** 0.9.0 -> 0.9.5
- **Frontend tests:** 111 -> 568 passing (54 test files)
- **Backend **init**.py:** **version** = "0.9.5"
- **deps.py:** get_current_user includes all entity fields + is_active check
- **Nginx:** pinned to 1.27-alpine, comprehensive security headers
- **Docker images:** all pinned to specific patch versions
- **config.py:** validation rejects insecure defaults in prod/staging
- **connection.py:** pool_recycle=3600, DB_ECHO setting, async subprocess for init
- **Alembic env.py:** imports all 10 models
- **pyproject.toml:** dependency versions synced, S603/S607 scoped to cli/
- **pyrightconfig.json:** typeCheckingMode "standard"
- **package.json:** engines node >=22
- **vite.config.ts:** sourcemaps disabled, coverage thresholds added

### Removed

- **SAML/LDAP:** All source files, config, tests, and doc references
- **passlib[bcrypt]:** Dead dependency with zero usage
- **zod:** Unused frontend dependency
- **structlog:** Replaced by built-in get_logger()
- **Dead auth use cases:** login.py, register.py, refresh.py
- **FR/DE i18n references:** Removed from all docs and configs
- **Aspirational docs:** 6 docs for unimplemented features

### Fixed

- **LoginPage:** Duplicate divider removed
- **Vite proxy:** Removed routes colliding with SPA
- **MFA await:** Coroutine was always truthy (bypassed MFA check)
- **Rate limiter:** InMemoryRateLimiter.is_allowed() was sync (always truthy)
- **Health readiness:** Fixed broken import (async_session_factory -> async_session_maker)
- **TenantsPage:** Hooks moved before early return (React rules violation)
- **ResetPasswordPage:** Fail-closed in catch block
- **authStore:** refreshAccessToken calls refresh without arguments
- **api.ts:** getCookie uses substring instead of split for = in values

## [0.9.0] - 2026-02-06

### BREAKING SemVer Reset

Re-versioned from inflated 1.x to honest SemVer 0.9.0 to reflect beta status.

### Security

- HttpOnly cookies for JWT tokens (access + refresh)
- CSRF double-submit cookie pattern
- JWT fail-fast rejects default secret in production/staging
- Security headers middleware (HSTS, CSP, X-Frame-Options)
- Redis-based rate limiting middleware
- Nginx hardening (server_tokens off, CSP, client_max_body_size)
- Docker non-root containers
- Password reset tokens migrated to Redis with TTL
- WebSocket auth via HttpOnly cookies (removed query string tokens)
- MFA migrated from sync redis to async get_cache()

### Added

- React ErrorBoundary wrapping entire app tree
- Global exception handlers (8 domain exception mappers)
- AdminRoute frontend guard
- Request-ID middleware
- User use cases (GetUser, CreateUser, UpdateUser, DeleteUser)
- Dependabot configuration
- Health endpoint with DB probe (SELECT 1)
- ~50 i18n keys across EN/ES/PT

### Changed

- api.ts monolith split into 14 domain services
- i18n: removed FR/DE, completed PT to ~96%
- CI: Node 20 -> 22 LTS
- Vite build sourcemaps disabled

### Removed

- SAML/LDAP source files, config, and tests
- 6 aspirational docs (GraphQL, Webhooks, SMS 2FA, Payments, SAML SSO, LDAP AD)

## [1.4.0] - 2026-02-03

> Pre-SemVer-reset release. Version numbering was inflated.

### Added

- Email OTP 2FA system (6-digit codes, Redis-backed, rate limited)
- DataExchange frontend page (export/import/reports tabs)

### Fixed

- Integration test deadlock (shared DB session in fixtures)
- EntityNotFoundError default message
- Silent exception logging in 4 modules

## [1.3.9] - 2026-02-02

> Pre-SemVer-reset release.

### Added

- Data Exchange system (import/export/reports with entity configuration)
- CSV, Excel, JSON handlers for generic import/export
- Report generation (PDF, Excel, CSV, HTML)

## [1.3.8] - 2026-02-02

> Pre-SemVer-reset release.

### Fixed

- Middleware ASGI migration for Python 3.13+

## [1.3.5] - 2026-01-27

> Pre-SemVer-reset release.

### Changed

- Backend coverage: 94% -> 98% (critical modules at 95%+)
- Total tests: 3,615 -> 3,838 passing

## [1.3.4] - 2026-01-26

> Pre-SemVer-reset release.

### Changed

- Backend coverage: 97% -> 98%
- Critical modules (auth, users, roles, tenants, mfa) at high coverage

## [1.3.3] - 2026-01-15

> Pre-SemVer-reset release.

### Changed

- Backend coverage: 87% -> 94%
- WebSocket Redis Manager: 72% -> 87% coverage
- Local Storage Adapter: 77% -> 99% coverage

## [1.3.2] - 2026-01-15

> Pre-SemVer-reset release.

### Added

- 50 new tests (session repo, OAuth providers, CLI commands)

## [1.3.1] - 2026-01-13

> Pre-SemVer-reset release.

### Added

- Complete i18n implementation (EN, ES, PT)
- Audit Log Viewer, Tenant Management, Roles Management, Search Page
- 17 email templates
- All frontend dependencies updated

### Changed

- Language selection reduced to 3 active (EN, ES, PT)
- Bundle size: -18% (850KB -> 700KB)

## [1.2.1] - 2025-01-15

> Pre-SemVer-reset release.

### Added

- French (FR) and German (DE) translations (later removed in v0.9.0)
- JWT library migration from python-jose to PyJWT

## [1.2.0] - 2025-01-09

> Pre-SemVer-reset release.

### Added

- OAuth2/SSO UI (Google, GitHub, Microsoft, Discord buttons)
- Real-time chat interface (later simplified)
- Notifications dropdown and page
- Full-text search page
- WebSocket hooks (useWebSocket, useChat)

## [1.1.1] - 2026-01-08

> Pre-SemVer-reset release.

### Fixed

- Database migration fixes (duplicate migration, password hashes)
- Type safety fixes (datetime, cached repositories)
- PowerShell function naming (approved verbs)
- Markdown linting (32 warnings)

## [1.1.0] - 2026-01-08

> Pre-SemVer-reset release.

### Added

- User registration page
- Password recovery flow (forgot/reset)
- Profile settings, API keys management, MFA configuration pages
- Password recovery backend endpoints

## [1.0.1] - 2026-01-07

> Pre-SemVer-reset release.

### Security

- React 19 -> 18.3.1 LTS (CVE in Server Components)
- Node 20 -> 22 LTS (EOL)
- All frontend dependencies audited (0 vulnerabilities)

## [1.0.0] - 2026-01-07

> Pre-SemVer-reset release. Initial public release.

### Added

- Hexagonal architecture (domain, application, infrastructure layers)
- JWT authentication with access/refresh tokens
- MFA/2FA with TOTP and backup codes
- API keys with scoped permissions
- Granular ACL (resource:action permissions)
- Multi-tenant RLS (PostgreSQL Row Level Security)
- OAuth2 SSO (Google, GitHub, Microsoft, Discord)
- PostgreSQL Full-Text Search
- Pluggable storage (Local, S3, MinIO)
- Pluggable email (SMTP, Console, SendGrid)
- OpenTelemetry observability
- WebSocket support with notifications
- Docker Compose environments (dev, test, staging, prod)
- CLI tools (user management, database, API keys)
- React 18 + TypeScript frontend
- 508 backend tests passing
