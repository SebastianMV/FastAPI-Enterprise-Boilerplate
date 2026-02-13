# ADR-003: Centralized Structured Logging via get_logger()

- **Date:** 2025-07-20
- **Status:** Accepted
- **Author:** Sebastián Muñoz

## Context

Across 24 security audits, **logging issues** were the #1 root cause category (~95 issues):
- `import logging` → no request context (request_id, tenant_id, user_id)
- `logger.info(f"User {user_id} did {action}")` → PII in logs, not machine-parseable
- `logger.error(f"Error: {e}")` → stack traces and internal details leaked

We needed a single, opinionated entry point that makes the right thing easy and the wrong
thing hard.

## Decision

All application code MUST use:

```python
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)
logger.info("user_action", user_id=user_id, action="login")
```

**NEVER:**

```python
import logging  # ← FORBIDDEN
logger.info(f"User {user_id} logged in")  # ← FORBIDDEN
```

The `get_logger()` function:
1. Returns a `structlog`-compatible logger with bound context
2. Automatically includes `request_id`, `tenant_id`, `timestamp` from middleware context
3. Outputs JSON in production, human-readable in development
4. Filters sensitive fields (password, token, secret) from log output

## Consequences

### Positive

- **Structured logs** — every log entry is JSON with consistent fields, queryable in ELK/Loki
- **Automatic context** — request_id and tenant_id injected by middleware, not by developers
- **Security by default** — sensitive field filtering prevents accidental PII leaks
- **Enforceable** — Semgrep rule `no-stdlib-logging` + meta-test catches `import logging`

### Negative

- **Learning curve** — contributors must learn `get_logger()` instead of stdlib `logging`
- **Import path dependency** — all code depends on `app.infrastructure.observability.logging`
- **Structured syntax** — `logger.info("action", key=val)` is less intuitive than f-strings

### Neutral

- Dev mode still shows human-readable output (no DX regression)
- Performance is equivalent to stdlib logging

## Alternatives Considered

### stdlib logging + Custom Formatter

Use `import logging` with a custom JSON formatter. Rejected because:
- No way to enforce structured kwargs (`f"..."` still works)
- Context injection (request_id) requires manual `extra={}` on every call
- 95 audit issues proved developers default to f-strings

### loguru

Feature-rich logging library. Rejected because:
- Adds external dependency for something we can control with structlog
- Less integration with OpenTelemetry trace context
- Harder to enforce structured-only output

## References

- Audits 1-24: ~95 logging-related issues across all audits
- `backend/app/infrastructure/observability/logging.py`: Implementation
- Semgrep rule: `.semgrep/backend-security.yml` → `no-stdlib-logging`
- Meta-test: `backend/tests/security/test_security_meta.py::TestNoStdlibLogging`
