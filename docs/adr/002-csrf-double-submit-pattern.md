# ADR-002: CSRF Double-Submit Pattern

- **Date:** 2025-06-15
- **Status:** Accepted
- **Author:** Sebastián Muñoz

## Context

Since [ADR-001](001-httponly-cookies-for-jwt.md) stores JWT tokens in cookies, the application
is vulnerable to Cross-Site Request Forgery (CSRF) attacks. An attacker could craft a malicious
page that submits requests to our API, and the browser would automatically include the auth
cookies.

We need a CSRF protection mechanism that works with our SPA architecture.

## Decision

Implement the **double-submit cookie** pattern:

1. On login, the backend sets a `csrf_token` cookie (NOT HttpOnly — readable by JS)
2. The frontend reads this cookie and sends it as the `X-CSRF-Token` header on every
   state-changing request (POST, PUT, PATCH, DELETE)
3. The backend middleware compares the cookie value with the header value using
   `hmac.compare_digest()` (timing-safe)
4. If they don't match → 403 Forbidden

```
Browser cookie: csrf_token=abc123
Request header: X-CSRF-Token: abc123
Backend: hmac.compare_digest(cookie_value, header_value) → ✓
```

## Consequences

### Positive

- **Stateless** — no server-side CSRF token storage needed
- **SPA-compatible** — works naturally with axios interceptors
- **Timing-safe** — `hmac.compare_digest()` prevents timing attacks on token comparison
- **Origin-validated** — combined with `SameSite=Lax` cookies, provides defense in depth

### Negative

- **Every state-changing request** must include `X-CSRF-Token` header — omission = 403
- **Token rotation** adds complexity on refresh flows
- **Cookie parsing** in frontend adds a small dependency

### Neutral

- GET/HEAD/OPTIONS requests are exempt (safe methods)

## Alternatives Considered

### Synchronizer Token Pattern (server-side)

Server generates and stores a unique token per session. Rejected because:
- Requires server-side state (conflicts with stateless JWT goal)
- Doesn't scale well with Redis session storage overhead

### SameSite=Strict Cookies Only

Relying solely on `SameSite=Strict`. Rejected because:
- Breaks top-level navigation with cookies (e.g., following a link from email)
- `SameSite=Lax` is more usable but doesn't protect POST requests from subdomain attacks
- Defense-in-depth requires multiple layers

### Custom Header Check (Origin/Referer)

Check `Origin` or `Referer` headers instead. Rejected because:
- Some browsers/proxies strip these headers
- Not reliable as sole defense

## References

- OWASP: [CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie)
- Audit 2 (Issues #16-#30): CSRF protection implementation
- `backend/app/middleware/csrf.py`: Implementation
