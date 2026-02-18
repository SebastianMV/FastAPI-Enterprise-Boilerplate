# 🤖 Agentes de Copilot — FastAPI-Enterprise-Boilerplate

> Agentes especializados para VS Code Copilot Chat, alineados a 38 auditorías,
> 992+ fixes históricos y las 19 reglas críticas del proyecto.

---

## Agentes disponibles

| Agente                 | Archivo                       | Propósito principal                                                   |
| ---------------------- | ----------------------------- | --------------------------------------------------------------------- |
| **SebAgent**           | `SebAgent.agent.md`           | Orquestador full-stack: implementa y coordina handoffs especializados |
| **quality-guardian**   | `quality-guardian.agent.md`   | Gate de calidad: convenciones, arquitectura, i18n y reglas críticas   |
| **security-auditor**   | `security-auditor.agent.md`   | AppSec profundo: vulnerabilidades nuevas y regresiones                |
| **dependency-auditor** | `dependency-auditor.agent.md` | Supply chain: CVEs, licencias, pinning y estrategia de upgrades       |

---

## Estructura estándar de los agentes

Todos los `.agent.md` usan una plantilla homogénea:

1. **Metadata**: `name`, `description`, `model`, `tools`, `handoffs`, `user-invokable`
2. **Prompt estructurado**:
   - `IDENTITY`
   - `ROLE`
   - `SCOPE`
   - `CAPABILITIES`
   - `CRITICAL RULES`
   - `CHECKLIST OPERATIVO`
   - `OUTPUT CONTRACT`
   - `HANDOFF POLICY`
   - `COMMUNICATION STYLE`

Objetivo: evitar agentes “genéricos” y forzar respuestas auditables, consistentes y accionables.

---

## Cómo invocar (VS Code)

Abre Copilot Chat (`Ctrl+Alt+I`) y usa `@`:

```text
@SebAgent implementa endpoint de exportación y coordina validación
@quality-guardian revisa este cambio contra las 19 reglas
@security-auditor audita riesgo AppSec en auth y multi-tenant
@dependency-auditor evalúa CVEs y plan de upgrade seguro
```

Con scope reducido:

```text
@security-auditor revisa solo backend/app/api/v1/endpoints/
@quality-guardian valida i18n y hooks en frontend/src/pages/
@dependency-auditor analiza impacto de actualizar FastAPI a 0.116
```

---

## Flujo recomendado (handoffs)

```text
Cambio de código
      │
      ▼
@quality-guardian   ← Gate rápido: convenciones + 19 reglas
      │
      ▼ (si hay riesgo de seguridad)
@security-auditor   ← Profundiza AppSec / OWASP / multi-tenant
      │
      ▼ (si hay cambios de deps/infra)
@dependency-auditor ← CVEs + licencias + pinning + upgrades
```

`SebAgent` puede iniciar o coordinar todo el flujo end-to-end.

---

## Contrato de salida por agente

Cada agente responde con una estructura fija para facilitar revisión en PR:

- **quality-guardian**
  - `QUALITY STATUS: PASS | FAIL`
  - `FINDINGS`, `REQUIRED FIXES`, `OPTIONAL IMPROVEMENTS`, `NEXT ACTION`

- **security-auditor**
  - `SECURITY STATUS: PASS | FAIL`
  - `RISK SUMMARY`, `FINDINGS`, `REQUIRED FIXES`, `VERIFICATION STEPS`

- **dependency-auditor**
  - `SUPPLY-CHAIN STATUS: PASS | FAIL`
  - `VULNERABILITY SUMMARY`, `AFFECTED ARTIFACTS`, `REQUIRED UPGRADES`, `SAFE UPGRADE PLAN`

- **SebAgent**
  - `EXECUTION STATUS: DONE | BLOCKED`
  - `CHANGE SUMMARY`, `SECURITY STATUS`, `VALIDATION`, `NEXT ACTION`

---

## Cuándo usar cada agente

| Situación                                     | Agente recomendado                          |
| --------------------------------------------- | ------------------------------------------- |
| Antes de push a `main`/`develop`              | `@quality-guardian`                         |
| Feature nueva con auth/datos sensibles        | `@security-auditor`                         |
| Actualización de librerías/imágenes/workflows | `@dependency-auditor`                       |
| Release readiness end-to-end                  | `@SebAgent`                                 |
| CI falla en calidad                           | `@quality-guardian` para diagnóstico        |
| CVE crítico reportado                         | `@dependency-auditor` + `@security-auditor` |

---

## Relación con CI

Los agentes **complementan** CI; no lo reemplazan:

- CI ejecuta checks determinísticos (tests, semgrep, grep de reglas, pins, secrets).
- Agentes aportan análisis semántico y priorización contextual de riesgo.

---

## Contexto base compartido

Todos los agentes están pensados para operar con:

- `AGENTS_HISTORY.md`
- `.github/copilot-instructions.md`
- `docs/analisis_interno/RECURRING_AUDIT_PATTERNS.md`
- `docs/analisis_interno/AUDIT_RETROSPECTIVE.md`
- `.semgrep/*.yml`
- `docs/adr/`

---

## Nota de mantenimiento

Si se modifica la plantilla de un agente, replicar el cambio en los demás para mantener
simetría de comportamiento y evitar regresiones de calidad en los handoffs.
