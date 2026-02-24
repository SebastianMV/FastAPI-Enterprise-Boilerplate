# Security Documentation

**FastAPI Enterprise Boilerplate v0.9.0**
**Last Updated:** February 2026

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Security Features](#security-features)
3. [Security Audit](#security-audit)
4. [Best Practices](#best-practices)

---

## Security Overview

This document provides comprehensive security documentation for the FastAPI Enterprise Boilerplate, including implemented security features, audit results, and best practices.

### Security Status Summary

| Category           | Status         | Notes                  |
| ------------------ | -------------- | ---------------------- |
| Authentication     | ✅ Secure      | JWT + Refresh tokens   |
| Authorization      | ✅ Secure      | RBAC + Scopes          |
| Data Validation    | ✅ Secure      | Pydantic v2            |
| SQL Injection      | ✅ Protected   | SQLAlchemy ORM         |
| XSS Prevention     | ✅ Protected   | Input validation       |
| CSRF Protection    | ✅ Protected   | SameSite cookies       |
| Rate Limiting      | ✅ Implemented | Redis-based            |
| Multi-Tenant       | ✅ Isolated    | RLS policies           |
| Secrets Management | ✅ Secure      | Environment variables  |
| Dependencies       | ⚠️ Monitor     | Regular updates needed |

---

## Security Features

### 1. Account Lockout

Protects against brute-force attacks by temporarily locking accounts after multiple failed login attempts.

#### Configuration

Configure in `.env` or environment variables:

```env
# Enable/disable account lockout (default: true)
ACCOUNT_LOCKOUT_ENABLED=true

# Number of failed attempts before lockout (default: 5, range: 3-10)
ACCOUNT_LOCKOUT_THRESHOLD=5

# Lockout duration in minutes (default: 30, range: 5-1440)
ACCOUNT_LOCKOUT_DURATION_MINUTES=30
```

#### Behavior

1. **Failed Login Tracking**: Each failed login attempt increments `failed_login_attempts`
2. **Automatic Lockout**: After `ACCOUNT_LOCKOUT_THRESHOLD` failures, the account is locked
3. **Lock Duration**: Account remains locked for `ACCOUNT_LOCKOUT_DURATION_MINUTES` minutes
4. **Automatic Unlock**: Lock expires automatically after the duration
5. **Reset on Success**: Successful login resets the failed attempts counter

#### API Responses

When an account is locked:

```json
{
  "status_code": 423,
  "detail": {
    "code": "ACCOUNT_LOCKED",
    "message": "Account is locked. Try again in 25 minute(s)."
  }
}
```

#### Admin Unlock

Administrators can manually unlock accounts:

```python
# In code
user.unlock()
await user_repository.update(user)
```

---

### 2. Session Management

Track and manage active login sessions across devices.

#### Features

- **View Active Sessions**: See all devices where you're logged in
- **Session Details**: Device name, browser, OS, IP address, location, last activity
- **Revoke Sessions**: Log out from specific devices or all other devices
- **Current Session Badge**: Clearly identifies which session you're currently using

#### API Endpoints

| Method | Endpoint                | Description                        |
| ------ | ----------------------- | ---------------------------------- |
| GET    | `/api/v1/sessions`      | List all active sessions           |
| DELETE | `/api/v1/sessions/{id}` | Revoke a specific session          |
| DELETE | `/api/v1/sessions`      | Revoke all sessions except current |

#### Example Response

```json
{
  "sessions": [
    {
      "id": "uuid-here",
      "device_name": "Chrome on Windows",
      "device_type": "desktop",
      "browser": "Chrome",
      "os": "Windows",
      "ip_address": "192.168.1.100",
      "location": "Santiago, Chile",
      "last_activity": "2026-01-12T10:30:00Z",
      "is_current": true,
      "created_at": "2026-01-10T08:00:00Z"
    }
  ],
  "total": 1
}
```

#### UI Access

Navigate to **Settings > Security > Active Sessions** to manage sessions.

---

### 3. Email Verification

Ensure users have valid email addresses.

#### Configuration

```env
# Require email verification for new users (default: true)
EMAIL_VERIFICATION_REQUIRED=true

# Token expiration in hours (default: 24, range: 1-72)
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=24
```

#### Flow

1. **Registration**: New users receive verification email automatically
2. **Verification Link**: Email contains a unique token link
3. **Verification Page**: User clicks link and is verified
4. **Resend Option**: Users can request new verification email

#### API Endpoints

| Method | Endpoint                              | Description                    |
| ------ | ------------------------------------- | ------------------------------ |
| POST   | `/api/v1/auth/send-verification`      | Send/resend verification email |
| POST   | `/api/v1/auth/verify-email?token=xxx` | Verify email with token        |
| GET    | `/api/v1/auth/verification-status`    | Check verification status      |

#### UI Components

- **Banner**: Yellow warning banner appears when email is not verified
- **Resend Button**: Users can resend verification from the banner
- **Verification Page**: `/verify-email?token=xxx` handles the verification

#### Behavior Options

When `EMAIL_VERIFICATION_REQUIRED=true`:

- Users can still log in without verification
- Some features may be restricted (configurable)
- Banner reminds user to verify

When `EMAIL_VERIFICATION_REQUIRED=false`:

- Users are marked as verified by default
- No verification emails are sent

---

### 4. Multi-Factor Authentication (MFA)

See [GETTING_STARTED.md](./GETTING_STARTED.md#mfa-setup) for TOTP-based two-factor authentication.

---

### 5. API Keys

See [GETTING_STARTED.md](./GETTING_STARTED.md#api-keys) for machine-to-machine authentication.

---

## Security Audit

### 1. Authentication Security

#### 1.1 Password Handling

**Implementation:**

- Passwords hashed using bcrypt (12 rounds)
- Password strength validation enforced
- No plaintext passwords stored or logged

**Code Location:** `app/infrastructure/auth/password_handler.py`

```python
# Secure password hashing
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
```

**Verification Tests:** `tests/integration/test_security.py::TestPasswordSecurity`

#### 1.2 JWT Tokens

**Implementation:**

- Access tokens: Short-lived (15 minutes default)
- Refresh tokens: Longer-lived (7 days default)
- Tokens signed with HS256 algorithm
- Token blacklisting on logout (optional)

**Security Measures:**

- [x] Tokens include expiration (`exp` claim)
- [x] Tokens include issued-at (`iat` claim)
- [x] Token type included to prevent misuse
- [x] Secret key from environment variable

**Code Location:** `app/infrastructure/auth/jwt_handler.py`

#### 1.3 API Key Authentication

**Implementation:**

- Keys hashed before storage (SHA-256)
- Only prefix shown in responses
- Scope-based access control
- Expiration support

**Code Location:** `app/infrastructure/auth/api_key_handler.py`

---

### 2. Authorization Security

#### 2.1 Role-Based Access Control (RBAC)

**Implementation:**

- Roles assigned at tenant level
- Permissions granular (resource:action)
- Role hierarchy supported

**Default Roles:**

| Role      | Permissions       |
| --------- | ----------------- |
| superuser | All permissions   |
| admin     | Tenant management |
| user      | Read own data     |

#### 2.2 Resource Ownership

**Implementation:**

- Users can only access their own resources
- Admin override for tenant admins
- Superuser bypass for platform admins

---

### 3. Input Validation

#### 3.1 Pydantic Validation

All inputs validated using Pydantic v2:

```python
class UserCreate(BaseModel):
    email: EmailStr  # Validates email format
    password: str = Field(min_length=8)  # Minimum length
    full_name: str = Field(max_length=100)  # Maximum length
```

#### 3.2 SQL Injection Prevention

- All database queries use SQLAlchemy ORM
- No raw SQL with user input
- Parameterized queries enforced

**Tested Payloads:**

```text
'; DROP TABLE users; --
1 OR 1=1
' UNION SELECT * FROM users --
```

All payloads neutralized by ORM.

---

### 4. API Security

#### 4.1 Rate Limiting

**Implementation:**

- Redis-based sliding window
- Per-user and per-IP limits
- Configurable thresholds
- Graceful degradation without Redis

**Default Limits:**

- Anonymous: 60 requests/minute
- Authenticated: 120 requests/minute
- API Keys: Configurable per key

**Code Location:** `app/api/middleware/rate_limit.py`

#### 4.2 Security Headers

**Headers Applied:**

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

#### 4.3 CORS Configuration

**Implementation:**

- Origins restricted by environment
- Credentials allowed only for specific origins
- Methods and headers explicitly allowed

---

### 5. Multi-Tenant Security

#### 5.1 Data Isolation

**Implementation:**

- Row-Level Security (RLS) at database level
- Tenant ID in JWT claims
- Automatic query filtering

**PostgreSQL Policy:**

```sql
CREATE POLICY tenant_isolation ON users
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

#### 5.2 Cross-Tenant Access Prevention

- Tested in: `tests/integration/test_security.py::TestMultiTenantSecurity`
- Verified: Users cannot access other tenants' data

---

### 6. Dependency Security

#### 6.1 Known Vulnerabilities

Run `pip-audit` or `safety check` regularly:

```bash
pip install pip-audit
pip-audit
```

#### 6.2 Pinned Dependencies

All dependencies pinned with minimum versions in `requirements.txt`.

**Regular Update Schedule:**

- Security patches: Immediate
- Minor updates: Weekly
- Major updates: Monthly (with testing)

---

### 7. Infrastructure Security

#### 7.1 Docker Security

**Measures:**

- Non-root user in production images
- Multi-stage builds (minimal attack surface)
- Health checks enabled
- Resource limits defined

#### 7.2 Secrets Management

**DO:**

- Use environment variables
- Use secrets management (Vault, AWS Secrets Manager)
- Rotate secrets regularly

**DON'T:**

- Commit secrets to version control
- Log sensitive data
- Use default secrets

---

### 8. Security Testing

#### 8.1 Test Coverage

| Test Category        | Tests | Status |
| -------------------- | ----- | ------ |
| Authentication       | 8     | ✅     |
| Authorization        | 6     | ✅     |
| Password Security    | 4     | ✅     |
| Injection Prevention | 4     | ✅     |
| Rate Limiting        | 3     | ✅     |
| Multi-Tenant         | 4     | ✅     |
| API Keys             | 5     | ✅     |

#### 8.2 Running Security Tests

```bash
# Run all security tests
pytest tests/integration/test_security.py -v

# Run with coverage
pytest tests/integration/test_security.py --cov=app -v
```

---

## Best Practices

### Production Security Settings

```env
# Account Lockout
ACCOUNT_LOCKOUT_ENABLED=true
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_LOCKOUT_DURATION_MINUTES=30

# Email Verification
EMAIL_VERIFICATION_REQUIRED=true
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=24

# JWT Tokens
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
```

### Security Checklist

#### Before Production

- [ ] Change all default secrets
- [ ] Enable HTTPS only
- [ ] Configure proper CORS origins
- [ ] Set up monitoring and alerting
- [ ] Enable audit logging
- [ ] Review rate limits for your use case
- [ ] Enable account lockout
- [ ] Require email verification
- [ ] Set strong JWT secret key (min 32 characters)
- [ ] Enable MFA for admin accounts

#### Ongoing Maintenance

- [ ] Regular dependency updates
- [ ] Periodic security audits
- [ ] Monitor for CVEs
- [ ] Review access logs
- [ ] Rotate secrets quarterly

### OWASP Top 10 (2021) Compliance

| Risk                           | Status                 | Implementation     |
| ------------------------------ | ---------------------- | ------------------ |
| A01: Broken Access Control     | ✅ Mitigated           | RBAC, RLS          |
| A02: Cryptographic Failures    | ✅ Mitigated           | bcrypt, TLS        |
| A03: Injection                 | ✅ Mitigated           | ORM, validation    |
| A04: Insecure Design           | ✅ Mitigated           | Secure defaults    |
| A05: Security Misconfiguration | ⚠️ User responsibility | Docs provided      |
| A06: Vulnerable Components     | ⚠️ Monitor             | Update regularly   |
| A07: Auth Failures             | ✅ Mitigated           | JWT, rate limiting |
| A08: Data Integrity            | ✅ Mitigated           | Signed tokens      |
| A09: Logging Failures          | ✅ Mitigated           | Structured logging |
| A10: SSRF                      | ✅ Mitigated           | No external fetch  |

---

## Per-PR Security Checklist

> **Codified from 43+ security audits (992+ issues resolved).**
> Use this checklist when adding new features, endpoints, or pages.
> Expanded examples: see [Quality Gates](./analisis_interno/QUALITY_GATES.md).

### Backend — New API Endpoint

- [ ] **Authorization**: Uses `require_permission("resource", "action")`, not just `CurrentUser`
- [ ] **Tenant isolation**: Queries filter by `CurrentTenantId` (multi-tenant RLS)
- [ ] **Error responses**: Generic messages only — never `str(e)` or f-strings with exceptions
- [ ] **Logging**: Uses `get_logger()` from `app.infrastructure.logging`, not `import logging`
- [ ] **Log format**: Structured kwargs `logger.info("event", key=val)` — never f-strings
- [ ] **Input validation**: Pydantic schemas with `NameStr`, `ShortStr`, `TextStr` (never bare `str`)
- [ ] **SQL safety**: Parameterized queries only — no f-strings in `text()` or `.execute()`
- [ ] **LIKE wildcards**: `%`, `_`, `\` escaped with `ESCAPE '\\'` when using user input
- [ ] **Rate limiting**: Sensitive endpoints (auth, password) have rate limits
- [ ] **Pagination limits**: `Query(ge=1, le=100)` on limit parameters

### Backend — Auth & Tokens

- [ ] **Tokens in cookies**: Never return tokens in JSON response body
- [ ] **Cookie flags**: `httponly=True, secure=True, samesite="lax"`
- [ ] **Token comparison**: Uses `hmac.compare_digest()` for all token/CSRF/OTP comparisons
- [ ] **Password changes**: Invalidate all sessions via `session_repo.revoke_all()`
- [ ] **Refresh token**: Check JTI blacklist before issuing new tokens
- [ ] **CSRF exempt**: Only specific callback URLs, never broad prefixes

### Backend — Cryptographic & Async Safety

- [ ] **hashlib.md5/sha1**: Always include `usedforsecurity=False` for non-security uses
- [ ] **datetime**: Uses `datetime.now(UTC)`, never `datetime.utcnow()`
- [ ] **Secrets encryption**: OAuth client_secret, MFA secret encrypted with `encrypt_value()`
- [ ] **No blocking calls**: No `subprocess.run()`, `redis.Redis()` (sync), or `time.sleep()` in async code

### Frontend — New Page/Component

- [ ] **No `error.message`**: Never render `error.message` or `err.response.data.detail` to users
- [ ] **i18n only**: All user-facing strings use `t('key')` — no hardcoded English
- [ ] **Console gating**: `console.error/log/warn` gated behind `import.meta.env.DEV`
- [ ] **Use axios**: Never use raw `fetch()` — use centralized `api.ts`
- [ ] **No tokens in localStorage**: Auth tokens handled via HttpOnly cookies only
- [ ] **AbortController**: `useEffect` with fetch calls uses `AbortController` for cleanup
- [ ] **useCallback**: Wrap handlers passed as deps to `useEffect`
- [ ] **URL params**: `encodeURIComponent(id)` in all API URL interpolations

### Frontend — Accessibility

- [ ] **aria-labels**: Uses `t()` i18n keys, not hardcoded English
- [ ] **Interactive elements**: Clickable `<div>` has `role="button"`, `tabIndex={0}`, `onKeyDown`
- [ ] **Password inputs**: Have `autoComplete` attribute
- [ ] **Icon-only buttons**: Have `aria-label` with i18n key

### Infrastructure — Docker & CI

- [ ] **No hardcoded secrets**: Use `${VAR:?must be set}` in compose files
- [ ] **Pinned images**: Specific version tags (e.g., `postgres:17.2-alpine`)
- [ ] **Container hardening**: `security_opt: [no-new-privileges:true]`, `cap_drop: [ALL]`
- [ ] **Ports**: Bind to `127.0.0.1` in dev, use `expose` instead of `ports` in prod
- [ ] **CI actions**: Pinned to commit SHA with version comment
- [ ] **Network segmentation**: Separate frontend/backend networks in prod/staging

### Automated Enforcement

| Pattern                    | Tool                          | Blocks PR? |
| -------------------------- | ----------------------------- | ---------- |
| `eval()`, `exec()`         | Semgrep + Bandit + Ruff S     | Yes        |
| `str(e)` in HTTP response  | Semgrep                       | Yes        |
| f-string in logger         | Semgrep + Ruff G              | Yes        |
| `import logging` (direct)  | Semgrep                       | Warning    |
| `datetime.utcnow()`        | Ruff DTZ                      | Yes        |
| `console.error()` ungated  | ESLint no-console             | Warning    |
| `error.message` in UI      | Semgrep                       | Yes        |
| `localStorage` with tokens | Semgrep                       | Yes        |
| Docker `:latest` tags      | Semgrep                       | Warning    |
| Known CVEs                 | pip-audit + npm audit + Trivy | Yes        |

---

## Related Documentation

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Production deployment guide
- [GETTING_STARTED.md](./GETTING_STARTED.md) - Setup and configuration
- [API_REFERENCE.md](./API_REFERENCE.md) - API endpoints documentation
- [Quality Gates](./analisis_interno/QUALITY_GATES.md) - Expanded ❌/✅ examples for each rule
- [ADRs](./adr/) - Architecture Decision Records
