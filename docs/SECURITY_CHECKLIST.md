# 🛡️ Security Development Checklist

> **Codified from 13 consecutive security audits (300+ issues resolved).**
> Use this checklist when adding new features, endpoints, or pages.

---

## 📋 Before Every Pull Request

### Backend — New API Endpoint

- [ ] **Authorization**: Uses `require_permission("resource", "action")`, not just `CurrentUser`
- [ ] **Tenant isolation**: Queries filter by `CurrentTenantId` (multi-tenant RLS)
- [ ] **Error responses**: Generic messages only — never `str(e)` or f-strings with exceptions
- [ ] **Logging**: Uses `get_logger()` from `app.infrastructure.logging`, not `import logging`
- [ ] **Log format**: Lazy `%s` formatting — never f-strings in `logger.info/warning/error()`
- [ ] **Input validation**: All user input validated (Pydantic schemas, length limits, regex)
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

### Backend — Cryptographic Safety

- [ ] **hashlib.md5/sha1**: Always include `usedforsecurity=False` for non-security uses
- [ ] **datetime**: Uses `datetime.now(UTC)`, never `datetime.utcnow()`
- [ ] **Secrets encryption**: OAuth client_secret, MFA secret encrypted with `encrypt_value()`

### Backend — Async Safety

- [ ] **No blocking calls**: No `subprocess.run()`, `redis.Redis()` (sync), or `time.sleep()` in async code
- [ ] **Use**: `asyncio.create_subprocess_exec()`, `redis.asyncio`, `asyncio.sleep()`

---

### Frontend — New Page/Component

- [ ] **No `error.message`**: Never render `error.message` or `err.response.data.detail` to users
- [ ] **i18n only**: All user-facing strings use `t('key')` — no hardcoded English
- [ ] **Console gating**: `console.error/log/warn` gated behind `import.meta.env.DEV`
- [ ] **Use axios**: Never use raw `fetch()` — use centralized `api.ts` (includes CSRF, cookies, interceptors)
- [ ] **No tokens in localStorage**: Auth tokens handled via HttpOnly cookies only
- [ ] **No PII in localStorage**: Only UI preferences (theme, language, timezone)
- [ ] **sessionStorage for sensitive**: Search history uses `sessionStorage`, not `localStorage`

### Frontend — URL & Navigation Safety

- [ ] **Redirect validation**: URLs from server/params validated (starts with `/`, no `//`, no protocol)
- [ ] **OAuth URLs**: Validate `https://` before redirect
- [ ] **URL params**: Never render query params directly in UI (reflected XSS)
- [ ] **AbortController**: `useEffect` with fetch calls uses `AbortController` for cleanup

### Frontend — Accessibility

- [ ] **aria-labels**: Uses `t()` i18n keys, not hardcoded English
- [ ] **Interactive elements**: Clickable `<div>` has `role="button"`, `tabIndex={0}`, `onKeyDown`
- [ ] **Password inputs**: Have `autoComplete` attribute (`current-password` or `new-password`)
- [ ] **Icon-only buttons**: Have `aria-label` with i18n key

---

### Infrastructure — Docker & CI

- [ ] **No hardcoded secrets**: Use `${VAR:?must be set}` in compose files
- [ ] **Pinned images**: Specific version tags (e.g., `postgres:17.7-alpine`), never `:latest`
- [ ] **Container hardening**: `security_opt: [no-new-privileges:true]`, `cap_drop: [ALL]`
- [ ] **Ports**: Bind to `127.0.0.1` in dev, use `expose` instead of `ports` in prod
- [ ] **Log rotation**: `json-file` driver with `max-size: 50m`, `max-file: 5`
- [ ] **Resource limits**: `pids_limit` on all containers
- [ ] **CI actions**: Pinned to commit SHA with version comment
- [ ] **Network segmentation**: Separate frontend/backend networks in prod/staging

---

## 🔧 Automated Enforcement

These checks are enforced **automatically** — you don't need to remember them:

| Pattern | Tool | Where | Blocks PR? |
|---|---|---|---|
| `eval()`, `exec()` | Semgrep + Bandit + Ruff S | pre-commit + CI | ✅ Yes |
| `str(e)` in HTTP response | Semgrep | pre-commit + CI | ✅ Yes |
| f-string in logger | Semgrep + Ruff G | pre-commit + CI | ✅ Yes |
| `import logging` (direct) | Semgrep | pre-commit + CI | ⚠️ Warning |
| `datetime.utcnow()` | Ruff DTZ | pre-commit + CI | ✅ Yes |
| `print()` in app code | Ruff T20 | pre-commit + CI | ✅ Yes |
| `console.error()` ungated | ESLint no-console | CI lint step | ⚠️ Warning |
| `error.message` in UI | Semgrep | pre-commit + CI | ✅ Yes |
| `localStorage` with tokens | Semgrep | pre-commit + CI | ✅ Yes |
| `dangerouslySetInnerHTML` | Semgrep | pre-commit + CI | ✅ Yes |
| Raw `fetch()` | Semgrep | pre-commit + CI | ⚠️ Warning |
| SQL f-strings | Semgrep + Bandit B608 | pre-commit + CI | ✅ Yes |
| Hardcoded passwords in Docker | Semgrep | pre-commit + CI | ✅ Yes |
| Docker `:latest` tags | Semgrep | pre-commit + CI | ⚠️ Warning |
| Hardcoded secrets | pre-commit detect-private-key | pre-commit | ✅ Yes |
| Known CVEs (Python) | pip-audit + Trivy | CI | ✅ Yes |
| Known CVEs (npm) | npm audit + Trivy | CI | ✅ Yes |

---

## 📖 Related Documentation

- [SECURITY.md](SECURITY.md) — Security architecture overview
- [.semgrep/](../.semgrep/) — Custom Semgrep rules with audit references
- [backend/pyproject.toml](../backend/pyproject.toml) — Ruff S rules + Bandit config
- [frontend/eslint.config.js](../frontend/eslint.config.js) — ESLint security rules
- [.pre-commit-config.yaml](../.pre-commit-config.yaml) — Pre-commit hooks
- [.github/workflows/ci.yml](../.github/workflows/ci.yml) — CI SAST pipeline
