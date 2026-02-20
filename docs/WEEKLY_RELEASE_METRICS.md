# Weekly Release Metrics — v1.0.0

**Primera captura:** 2026-02-18
**Frecuencia:** semanal (actualizar cada cierre de sprint/semana)
**Objetivo:** concentrar en un único reporte el estado de calidad para decisión Go/No-Go.

---

## 1) Snapshot actual

| Métrica                           |                 Valor actual |                         Objetivo v1.0.0 | Estado     | Fuente                                           |
| --------------------------------- | ---------------------------: | --------------------------------------: | ---------- | ------------------------------------------------ |
| Frontend coverage (statements)    |                       72.43% |                                   >=50% | ✅ Done    | `npm run test:coverage` (2026-02-18)             |
| Frontend coverage (branches)      |                       65.06% |                   +3 puntos en Semana 2 | ✅ Done    | `npm run test:coverage` (2026-02-18)             |
| Frontend coverage (functions)     |                       69.01% |                        mejora sostenida | ✅ OK      | `npm run test:coverage` (2026-02-18)             |
| Frontend coverage (lines)         |                       74.11% |                        mejora sostenida | ✅ OK      | `npm run test:coverage` (2026-02-18)             |
| Frontend total tests              |        598 passed (55 files) |                                 estable | ✅ OK      | `npm run test:coverage` (2026-02-18)             |
| MyPy total errors (backend)       |                          225 |  0 (o baseline transitorio decreciente) | ⚠️ Partial | `backend/mypy-report-week3-tranche2.txt`         |
| Módulo con mayor deuda MyPy       |     app/infrastructure = 138 |             reducción semanal sostenida | ⚠️ Partial | `backend/mypy-report-week3-tranche2.txt`         |
| E2E críticos definidos            |                    8 nodeids | >=8 estables (sin skip/xfail en subset) | ✅ Done    | `backend/tests/e2e/release_critical_nodeids.txt` |
| E2E críticos (run local Semana 3) |                   8/8 passed |                          estabilidad CI | ✅ OK      | `pytest -v <nodeids>` (2026-02-19)               |
| E2E críticos en CI Linux          |                   habilitado |                              bloqueante | ✅ Done    | `.github/workflows/ci.yml`                       |
| Staging rehearsal (Week 4)        |     ejecutado, no exitoso    |        deploy+migración+smoke+rollback | ❌ Blocked | `docs/WEEK4_RELEASE_HARDENING.md`                |
| TypeScript type errors            |                            0 |                                       0 | ✅ OK      | `PROJECT_STATUS.md`                              |
| i18n PT key coverage              |                  100% claves |                         >=95% sostenido | ✅ OK      | gate `quality-guardian`                          |
| CI total duration (main/develop)  | Pendiente de captura semanal |         tendencia estable o decreciente | ⏳ Pending | GitHub Actions                                   |

Notas de calidad detectadas en la corrida:

- Warnings de React Router future flags (informativos, no bloqueantes).
- Sin regresiones en suites frontend tras expansión de tests en Bloques A/B/C/D.
- Warnings `act(...)` eliminados en archivos priorizados de Semana 2.
- Semana 3 backend: tranche 2 aplicada con mejora MyPy **-57** vs baseline (`282 -> 225`).
- Semana 4 iniciada: hardening de release en progreso (ver `docs/WEEK4_RELEASE_HARDENING.md`).
- Semana 4: gate final MyPy definido en CI (`no-regression` + `max-total=225`).
- Semana 4: rehearsal staging ejecutado con rollback validado, bloqueado por conflicto runtime en `db/redis`.

---

## 2) MyPy debt breakdown (baseline)

Referencia: `backend/mypy-baseline.json`

| Módulo             | Errores |
| ------------------ | ------: |
| app/infrastructure |     194 |
| app/api            |      30 |
| app/cli            |      19 |
| app/domain         |      15 |
| app/middleware     |      12 |
| app/application    |      10 |
| app/root           |       1 |
| other              |       1 |
| **Total**          | **282** |

---

## 3) Política de control por PR

- **MyPy:** no se permite aumento de deuda vs baseline por módulo ni total.
- **E2E críticos:** el subset definido debe pasar en CI Linux.
- **Cobertura frontend:** objetivo de subida progresiva semanal hasta >=50%.

---

## 4) Plantilla de actualización semanal

## Semana YYYY-WW

- Frontend coverage: `x%` (Δ `+/-y`)
- MyPy total: `x` (Δ `+/-y`)
- Top 3 módulos MyPy: `...`
- E2E críticos (8): `passed/failed`
- CI duration promedio: `x min`
- Riesgos abiertos: `...`
- Decisión parcial: `On track / At risk / Off track`

---

## 5) Criterio de semáforo

- **Verde:** tendencia mejora o se mantiene en métricas críticas.
- **Amarillo:** una métrica crítica sin mejora por 2 semanas.
- **Rojo:** regresión en cobertura, E2E críticos o aumento de deuda MyPy.
