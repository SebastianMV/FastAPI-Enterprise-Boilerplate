# 🤖 Agentes de Copilot — FastAPI-Enterprise-Boilerplate

> Agentes especializados para VS Code Copilot Chat, construidos sobre 37 auditorías
> y 992+ fixes aplicados a este proyecto.

---

## Agentes disponibles

| Agente                 | Archivo                       | Propósito                                                          |
| ---------------------- | ----------------------------- | ------------------------------------------------------------------ |
| **security-auditor**   | `security-auditor.agent.md`   | Detecta vulnerabilidades nuevas y regresiones de seguridad         |
| **quality-guardian**   | `quality-guardian.agent.md`   | Verifica cumplimiento de las 19 reglas del proyecto y convenciones |
| **dependency-auditor** | `dependency-auditor.agent.md` | Audita supply chain: CVEs, licencias, pins de Docker/Actions       |

---

## Cómo invocar (VS Code)

Abre Copilot Chat (`Ctrl+Alt+I`) y escribe el nombre del agente con `@`:

```
@security-auditor audita el proyecto completo
@quality-guardian verifica el estado del proyecto
@dependency-auditor audita las dependencias
```

O con scope reducido:

```
@security-auditor revisa solo los cambios en backend/app/api/v1/endpoints/
@quality-guardian verifica que este nuevo endpoint cumple las 19 reglas
@dependency-auditor analiza el impacto de actualizar FastAPI a 0.116
```

---

## Cuándo usar cada agente

### Flujo recomendado

```
 Cambio de código
       │
       ▼
 @quality-guardian   ← ¿Cumple las 19 reglas y convenciones?
  (2–5 min, local)        Semgrep + meta-tests + i18n check
       │
       ▼ (si hay feature nueva considerable)
 @security-auditor   ← ¿Hay vulnerabilidades nuevas?
 (10–30 min, local)       OWASP checklist + análisis profundo
       │
       ▼ (si cambiaron dependencias)
@dependency-auditor  ← ¿Hay CVEs o pines desactualizados?
  (5–10 min, local)       pip-audit + npm audit + licencias
```

### Tabla de triggers

| Situación                                     | Agente recomendado                       |
| --------------------------------------------- | ---------------------------------------- |
| Antes de hacer push a `main`/`develop`        | `@quality-guardian`                      |
| Terminas una feature nueva (endpoint, página) | `@security-auditor`                      |
| Agregás o actualizás una dependencia          | `@dependency-auditor`                    |
| Después de cada sprint                        | `@security-auditor` (auditoría completa) |
| Recibís PR de Dependabot                      | `@dependency-auditor`                    |
| Pre-release (antes de v1.0.0)                 | Los 3 en secuencia                       |
| El CI falla en el job `quality-guardian`      | `@quality-guardian` para diagnóstico     |
| Hay un CVE reportado en el ecosistema         | `@dependency-auditor` inmediatamente     |

---

## División de responsabilidades

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CI / GitHub Actions                          │
│                                                                     │
│  ┌────────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  backend-  │  │  frontend-  │  │ security │  │    sast      │  │
│  │   test     │  │    test     │  │  (trivy) │  │  (semgrep)   │  │
│  └────────────┘  └─────────────┘  └──────────┘  └──────────────┘  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │          quality-guardian (nuevo job automatizado)          │   │
│  │  19 reglas grep · meta-tests · docker pins · secret check   │   │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     Local / VS Code Copilot                         │
│                                                                     │
│  @quality-guardian   → análisis profundo + diagnóstico manual       │
│  @security-auditor   → vulnerabilidades nuevas (juicio humano)      │
│  @dependency-auditor → CVEs + licencias + upgrades seguros          │
└─────────────────────────────────────────────────────────────────────┘
```

**Regla clave:** Los checks determinísticos (grep, Semgrep, tests) viven en CI.
El análisis semántico (¿este código es verdaderamente inseguro?) vive en los agentes locales.

---

## Qué automatiza CI vs qué hacen los agentes

| Check                            | CI automático             | Agente local             |
| -------------------------------- | ------------------------- | ------------------------ |
| 48 reglas Semgrep custom         | ✅ job `sast`             | ✅ `@quality-guardian`   |
| 8 security meta-tests            | ✅ job `backend-test`     | ✅ `@quality-guardian`   |
| `import logging` grep            | ✅ job `quality-guardian` | ✅ `@quality-guardian`   |
| Docker image pins                | ✅ job `quality-guardian` | ✅ `@quality-guardian`   |
| Secrets failsafe (`:?`)          | ✅ job `quality-guardian` | ✅ `@quality-guardian`   |
| i18n coverage diff               | ✅ job `quality-guardian` | ✅ `@quality-guardian`   |
| CVEs en dependencias             | ✅ job `security`         | ✅ `@dependency-auditor` |
| Análisis de vulnerabilidad nueva | ❌ requiere juicio        | ✅ `@security-auditor`   |
| Fix de código seguro             | ❌ requiere contexto      | ✅ `@security-auditor`   |
| Upgrade seguro de deps           | ❌ requiere análisis      | ✅ `@dependency-auditor` |

---

## Contexto cargado automáticamente

Todos los agentes leen estos archivos al iniciar:

| Recurso                                             | Propósito                                               |
| --------------------------------------------------- | ------------------------------------------------------- |
| `AGENTS_HISTORY.md`                                 | 992+ fixes previos — evita reportar issues ya resueltos |
| `.github/copilot-instructions.md`                   | Las 19 reglas críticas del proyecto                     |
| `docs/analisis_interno/RECURRING_AUDIT_PATTERNS.md` | 18 patrones multi-stack                                 |
| `docs/analisis_interno/AUDIT_RETROSPECTIVE.md`      | Top 10 causas raíz                                      |
| `.semgrep/*.yml`                                    | 48 reglas Semgrep custom                                |
| `docs/adr/`                                         | 6 ADRs — decisiones arquitectónicas que no se revierten |

---

## Historial de auditorías

Ver [AGENTS_HISTORY.md](../../AGENTS_HISTORY.md) para el historial completo de las 37
auditorías anteriores, organizadas por sesión con todos los fixes aplicados.

Ver [docs/analisis_interno/AUDIT_RETROSPECTIVE.md](../../docs/analisis_interno/AUDIT_RETROSPECTIVE.md)
para el análisis de las 24 primeras auditorías (top 10 causas raíz, distribución por categoría).
