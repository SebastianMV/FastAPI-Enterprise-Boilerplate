# ADR-006: Custom Semgrep Rules from 24 Security Audits

- **Date:** 2025-12-01
- **Status:** Accepted
- **Author:** Sebastián Muñoz

## Context

Over 24 consecutive security audits, 788 issues were identified and fixed. Analysis revealed
that the same categories of issues recurred across audits:

| Root Cause               | Issues | %   |
| ------------------------ | ------ | --- |
| Logging violations       | ~95    | 12% |
| Hardcoded strings (i18n) | ~157   | 20% |
| Missing tenant isolation | ~30    | 4%  |
| Error message leaks      | ~42    | 5%  |
| Docker hardening gaps    | ~55    | 7%  |

Standard linting tools (Ruff, ESLint, Bandit) catch general code quality issues but NOT
project-specific patterns like "don't use `import logging`" or "every endpoint needs
`CurrentTenantId`".

## Decision

Maintain a growing set of **custom Semgrep rules** in `.semgrep/` that codify every
recurring pattern from audits:

```
.semgrep/
├── backend-security.yml   # 27 rules (Python)
├── frontend-security.yml  # 19 rules (TypeScript/React)
└── infra-security.yml     # 2 rules (Dockerfiles)
```

These rules run as a **pre-commit hook** (blocking) and in **CI** (GitHub Actions).

Current rule categories:

- **Backend:** `import logging`, `str(e)` in responses, f-string logging, `datetime.utcnow()`,
  bare `str` in Pydantic, missing password min_length, HTML interpolation, CSV formula injection,
  token in URL params, missing tenant_id in endpoints
- **Frontend:** localStorage token storage, raw error display, ungated console, unencoded URL
  params, missing useEffect cleanup, hardcoded English strings, inline event handlers
- **Infra:** Dockerfile `latest` tag, unpinned base images

## Consequences

### Positive

- **Zero-cost enforcement** — violations caught before commit, not during review
- **Institutional knowledge** — audit lessons codified as executable rules, not just docs
- **Scales with audits** — each new audit adds 2-5 rules, building a permanent safety net
- **Works for AI agents** — Copilot and other agents respect pre-commit failures

### Negative

- **Maintenance burden** — rules need updating when patterns evolve
- **False positives** — some patterns have legitimate exceptions (mitigated with `# nosemgrep`)
- **Build dependency** — Semgrep must be installed (handled via pre-commit)

### Neutral

- Complementary to (not replacing) Ruff, ESLint, Bandit, MyPy
- Rules are project-specific — not general security advice

## Alternatives Considered

### Rely on Standard Linters Only

Use Ruff + ESLint + Bandit without custom rules. Rejected because:

- They don't catch project-specific patterns (`get_logger()` vs `import logging`)
- 788 issues proved standard tools are insufficient for this codebase
- No way to encode "every endpoint needs tenant_id" in standard linters

### Custom ESLint/Ruff Plugins

Write custom plugins for each linter. Rejected because:

- Requires different plugin formats for each tool
- Higher development and maintenance cost
- Semgrep's YAML DSL is simpler and covers both Python and TypeScript

### Code Review Checklists Only

Document patterns in a checklist for human reviewers. Rejected because:

- Humans forget, skip, or inconsistently apply checklists
- AI agents don't read markdown checklists during code generation
- Pre-commit hooks are deterministic — they never "miss" a violation

## References

- `.semgrep/backend-security.yml`: 27 backend rules
- `.semgrep/frontend-security.yml`: 19 frontend rules
- `.semgrep/infra-security.yml`: 2 infrastructure rules
- `.pre-commit-config.yaml`: Semgrep hook configuration
- `backend/tests/security/test_security_meta.py`: Meta-tests (complementary to Semgrep)
