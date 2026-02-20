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

**Estado inicial:** 282 errores totales en 56 archivos — baseline formal generado el 19 Feb 2026.
**Decisión de semana 1:** estrategia de salida controlada implementada.

### Baseline por módulo (generado 19 Feb 2026)

| Módulo | Errores actuales |
|---|---|
| app/infrastructure | 194 |
| app/api | 30 |
| app/cli | 19 |
| app/domain | 16 |
| app/middleware | 12 |
| app/application | 10 |
| app/config.py | 1 |
| **Total** | **282** |

### Gate anti-regresión
CI compara el reporte actual vs `backend/mypy-baseline.json`. Un PR que *aumenta* el total de errores rompe el CI bloqueante.

### Estrategia propuesta

1. Definir baseline por módulo (archivo de referencia versionado).
2. No permitir aumento de deuda total (budget <= 0 neto por PR).
3. Reducir deuda semanal con objetivo de reactivar gate bloqueante total.
4. Activar gate estricto completo antes de tag v1.0.0.

### Criterio temporal

- Semana 2: ~~baseline consolidado + budget de reducción~~ **baseline creado (282 errores, `mypy-baseline.json` en repo)**.
- Semana 3: reducción priorizada en dominios críticos (app/infrastructure: 194 errores es el mayor foco).
- Semana 4: retorno a modo bloqueante total o No-Go de release.

---

## 5) Tablero operativo semanal (P0/P1)

| Prioridad | Trabajo                                            | Dueño      | Estado      | Fecha objetivo |
| --------- | -------------------------------------------------- | ---------- | ----------- | -------------- |
| P0        | Subir cobertura frontend a >=42% (hito intermedio) | Frontend   | Pending     | Semana 2       |
| P0        | Definir y aplicar baseline MyPy por módulo         | Backend    | **Done** (282 errores baseline, gate activo) | Semana 1 |
| P0        | Estabilizar suite E2E crítica mínima               | Full-stack | Pending     | Semana 3       |
| P1        | Publicar reporte semanal único de métricas         | Platform   | In Progress | Semana 1       |
| P1        | Endurecer criterios de merge para release branch   | Platform   | Pending     | Semana 4       |

---

## 6) Entregables completados en Semana 1 (hasta hoy)

- Alineación documental de versión/auditorías/métricas en AGENTS.md y PROJECT_STATUS.md.
- Creación del roadmap operativo de 30 días.
- Ajuste del gate i18n PT en CI a umbral de calidad (>=95%).
- Registro de decisiones y matriz de checks en este documento.
- **Baseline MyPy formalizado:** `backend/mypy-baseline.json` generado y publicado (282 errores, 56 archivos, 7 módulos). Gate anti-regresión en CI ahora operativo.
- **`.gitignore` actualizado:** `backend/mypy-report.txt` y `backend/.venv/` excluidos correctamente.

---

## 7) Próximo paso inmediato (Semana 2)

1. Seleccionar 6-8 áreas frontend de mayor riesgo para elevar cobertura (target: ~42%).
2. Priorizar reducción de errores MyPy en `app/infrastructure` (194 errores = 69% del total).
3. Definir lista cerrada de E2E críticos bloqueantes para release.
