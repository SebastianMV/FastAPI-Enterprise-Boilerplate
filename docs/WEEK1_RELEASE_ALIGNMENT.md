# Semana 1 — Release Alignment (v1.0.0)

**Fecha de inicio:** 2026-02-18
**Objetivo de semana:** alinear criterios de salida, estado real de CI y baseline de deuda técnica.

---

## 1) Decisiones de Semana 1

1. **Fuente de verdad de release:**
   - PROJECT_STATUS.md (estado y blockers)
   - ROADMAP_1_0_OPERATIONAL_PLAN.md (plan operativo)
   - Este documento (acta de ejecución de Semana 1)

2. **Política de checks en CI:**
   - Checks críticos de calidad y seguridad deben tender a modo bloqueante para v1.0.0.
   - Excepciones temporales deben quedar explícitas y con plan de salida.

3. **Estado de i18n PT:**
   - Cobertura de claves verificada en 100% (src y public).
   - Gate de i18n en CI ajustado a mínimo 95% para evitar regresiones.

---

## 2) Matriz de checks CI (actual)

| Job              | Check                               | Estado actual | Tipo        | Nota de release               |
| ---------------- | ----------------------------------- | ------------- | ----------- | ----------------------------- |
| backend-test     | Ruff check + format                 | Bloqueante    | Calidad     | OK para v1.0.0                |
| backend-test     | MyPy                                | No bloqueante | Calidad     | Deuda activa, requiere cierre |
| backend-test     | Pytest + coverage                   | Bloqueante    | Calidad     | OK, mantener estabilidad      |
| frontend-test    | ESLint                              | Bloqueante    | Calidad     | OK                            |
| frontend-test    | TypeScript type-check               | Bloqueante    | Calidad     | OK                            |
| frontend-test    | Vitest + coverage                   | Bloqueante    | Calidad     | Cobertura aún bajo meta 50%   |
| security         | Trivy + pip-audit + npm audit       | Bloqueante    | Seguridad   | OK                            |
| sast             | Semgrep + Bandit                    | Bloqueante    | Seguridad   | OK                            |
| quality-guardian | 19 reglas + meta-tests + i18n       | Bloqueante    | Calidad/Sec | OK, actualizado               |
| build            | Docker build gated by previous jobs | Bloqueante    | Entrega     | OK                            |

---

## 3) Gap analysis de Semana 1

### P0 (bloquea release 1.0)

- **MyPy backend no bloqueante** en CI.
- **Cobertura frontend** por debajo del objetivo >=50%.
- **E2E críticos** aún parciales para escenarios de release.

### P1 (alta prioridad)

- Consolidar reporte semanal único de métricas (coverage, mypy, e2e, tiempo CI).
- Definir política de baseline formal para MyPy si no se puede llegar a 0 en corto plazo.

---

## 4) Baseline MyPy (formalización inicial)

**Estado inicial:** deuda de tipado significativa en backend (referencia operativa del último diagnóstico local).
**Decisión de semana 1:** usar estrategia de salida controlada.

### Estrategia propuesta

1. Definir baseline por módulo (archivo de referencia versionado).
2. No permitir aumento de deuda total (budget <= 0 neto por PR).
3. Reducir deuda semanal con objetivo de reactivar gate bloqueante total.
4. Activar gate estricto completo antes de tag v1.0.0.

### Criterio temporal

- Semana 2: baseline consolidado + budget de reducción.
- Semana 3: reducción priorizada en dominios críticos.
- Semana 4: retorno a modo bloqueante total o No-Go de release.

---

## 5) Tablero operativo semanal (P0/P1)

| Prioridad | Trabajo                                            | Dueño      | Estado      | Fecha objetivo |
| --------- | -------------------------------------------------- | ---------- | ----------- | -------------- |
| P0        | Subir cobertura frontend a >=42% (hito intermedio) | Frontend   | Pending     | Semana 2       |
| P0        | Definir y aplicar baseline MyPy por módulo         | Backend    | Pending     | Semana 2       |
| P0        | Estabilizar suite E2E crítica mínima               | Full-stack | Pending     | Semana 3       |
| P1        | Publicar reporte semanal único de métricas         | Platform   | In Progress | Semana 1       |
| P1        | Endurecer criterios de merge para release branch   | Platform   | Pending     | Semana 4       |

---

## 6) Entregables completados en Semana 1 (hasta hoy)

- Alineación documental de versión/auditorías/métricas en AGENTS.md y PROJECT_STATUS.md.
- Creación del roadmap operativo de 30 días.
- Ajuste del gate i18n PT en CI a umbral de calidad (>=95%).
- Registro de decisiones y matriz de checks en este documento.

---

## 7) Próximo paso inmediato (Semana 1 → Semana 2)

1. Seleccionar 6-8 áreas frontend de mayor riesgo para elevar cobertura.
2. Producir snapshot MyPy por módulo y objetivo de reducción por semana.
3. Definir lista cerrada de E2E críticos bloqueantes para release.
