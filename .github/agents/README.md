# Copilot Agents — FastAPI-Enterprise-Boilerplate

> Specialized agents for VS Code Copilot Chat, aligned with 43 audits,
> 994+ historical fixes, and the project's 19 critical rules.

---

## Available Agents

| Agent                  | File                          | Primary Purpose                                                |
| ---------------------- | ----------------------------- | -------------------------------------------------------------- |
| **quality-guardian**   | `quality-guardian.agent.md`   | Quality gate: conventions, architecture, i18n & critical rules |
| **security-auditor**   | `security-auditor.agent.md`   | Deep AppSec: new vulnerabilities and regressions               |
| **dependency-auditor** | `dependency-auditor.agent.md` | Supply chain: CVEs, licenses, pinning & upgrade strategy       |

---

## Standard Agent Structure

All `.agent.md` files use a uniform template:

1. **Metadata**: `name`, `description`, `model`, `tools`, `handoffs`, `user-invokable`
2. **Structured prompt**:
   - `IDENTITY`
   - `ROLE`
   - `SCOPE`
   - `CAPABILITIES`
   - `CRITICAL RULES`
   - `OPERATIONAL CHECKLIST`
   - `OUTPUT CONTRACT`
   - `HANDOFF POLICY`
   - `COMMUNICATION STYLE`

Goal: avoid generic agents and enforce auditable, consistent, and actionable responses.

---

## How to Invoke (VS Code)

Open Copilot Chat (`Ctrl+Alt+I`) and use `@`:

```text
@quality-guardian review this change against the 19 rules
@security-auditor audit AppSec risk in auth and multi-tenant
@dependency-auditor evaluate CVEs and safe upgrade plan
```

With reduced scope:

```text
@security-auditor review only backend/app/api/v1/endpoints/
@quality-guardian validate i18n and hooks in frontend/src/pages/
@dependency-auditor analyze impact of upgrading FastAPI to 0.116
```

---

## Recommended Flow (handoffs)

```text
Code change
      │
      ▼
@quality-guardian   ← Quick gate: conventions + 19 rules
      │
      ▼ (if security risk detected)
@security-auditor   ← Deep AppSec / OWASP / multi-tenant
      │
      ▼ (if deps/infra changes)
@dependency-auditor ← CVEs + licenses + pinning + upgrades
```

Any agent can initiate or coordinate the full end-to-end flow.

---

## Output Contract per Agent

Each agent responds with a fixed structure to facilitate PR review:

- **quality-guardian**
  - `QUALITY STATUS: PASS | FAIL`
  - `FINDINGS`, `REQUIRED FIXES`, `OPTIONAL IMPROVEMENTS`, `NEXT ACTION`

- **security-auditor**
  - `SECURITY STATUS: PASS | FAIL`
  - `RISK SUMMARY`, `FINDINGS`, `REQUIRED FIXES`, `VERIFICATION STEPS`

- **dependency-auditor**
  - `SUPPLY-CHAIN STATUS: PASS | FAIL`
  - `VULNERABILITY SUMMARY`, `AFFECTED ARTIFACTS`, `REQUIRED UPGRADES`, `SAFE UPGRADE PLAN`

---

## When to Use Each Agent

| Situation                              | Recommended Agent                           |
| -------------------------------------- | ------------------------------------------- |
| Before push to `main`/`develop`        | `@quality-guardian`                         |
| New feature with auth/sensitive data   | `@security-auditor`                         |
| Library/image/workflow updates         | `@dependency-auditor`                       |
| End-to-end release readiness           | `@quality-guardian` + `@security-auditor`   |
| CI quality failure                     | `@quality-guardian` for diagnosis            |
| Critical CVE reported                  | `@dependency-auditor` + `@security-auditor` |

---

## Relationship with CI

Agents **complement** CI; they do not replace it:

- CI runs deterministic checks (tests, semgrep, rule grep, pins, secrets).
- Agents provide semantic analysis and contextual risk prioritization.

---

## Shared Base Context

All agents are designed to operate with:

- `.github/copilot-instructions.md`
- `.semgrep/*.yml`
- `docs/adr/`

---

## Maintenance Note

If an agent template is modified, replicate the change across all agents to maintain
behavioral symmetry and prevent quality regressions in handoffs.
