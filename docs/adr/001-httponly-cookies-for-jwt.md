# ADR-001: HttpOnly Cookies for JWT Storage

- **Date:** 2025-06-15
- **Status:** Accepted
- **Author:** Sebastián Muñoz

## Context

The application needs to store JWT access and refresh tokens on the client side for
authenticated API requests. The two main options are browser `localStorage` and HttpOnly
cookies.

Multiple security audits (Audits 1, 3, 5, 8) found that `localStorage` is accessible from
any JavaScript running on the page, making tokens vulnerable to XSS attacks. A single XSS
vulnerability would allow full account takeover.

## Decision

Store JWT tokens exclusively in **HttpOnly, Secure, SameSite=Lax** cookies.

- Access token: short-lived (15 min), HttpOnly cookie
- Refresh token: long-lived (7 days), HttpOnly cookie, restricted path `/api/v1/auth/refresh`
- Tokens are **never** exposed to JavaScript — no `Authorization: Bearer` header from the client

## Consequences

### Positive

- **XSS-proof token storage** — JavaScript cannot read HttpOnly cookies, eliminating the most
  common token theft vector
- **Automatic transmission** — browser sends cookies with every request, no client-side token
  management code needed
- **Refresh token isolation** — restricted cookie path prevents refresh tokens from being sent
  to non-auth endpoints

### Negative

- **CSRF vulnerability** — cookies are sent automatically, so we MUST implement CSRF protection
  (see [ADR-002](002-csrf-double-submit-pattern.md))
- **Cross-origin complexity** — CORS configuration must be precise; credentials mode required
- **Mobile/API clients** — non-browser clients need a separate Bearer token flow (API keys)

### Neutral

- Slightly more complex auth middleware (read from cookie instead of header)

## Alternatives Considered

### localStorage + Bearer Header

The "standard" SPA approach. Rejected because:
- Any XSS vulnerability = full token theft
- 7 of our 24 audits found XSS-adjacent issues — the attack surface is real
- Requires manual `Authorization` header attachment on every request

### sessionStorage

Marginally better than localStorage (cleared on tab close) but still XSS-vulnerable.
Also breaks multi-tab usage.

## References

- OWASP: [Token Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html#token-storage-on-client-side)
- Audit 1 (Issues #1-#15): Initial localStorage findings
- Audit 8 (Issues #201-#215): Token exposure in error logs
