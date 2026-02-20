# Test Suite Rationalization Plan

**Fecha:** 2026-02-18
**Objetivo:** reducir deuda histórica de tests sin perder cobertura efectiva.

---

## Baseline actual

- Backend tests collectados: 4,800+
- Distribución de archivos:
  - `backend/tests/unit`: 215
  - `backend/tests/integration`: 17
  - `backend/tests/e2e`: 10
- Señales de duplicación:
  - `*coverage*`: 37 archivos
  - `*extended*`: 34 archivos
  - `*real*`: 11 archivos
- Señales de inestabilidad:
  - `skip` markers: 8
  - `xfail` markers: 1

---

## Estrategia por fases

### Fase 1 (inmediata): Observabilidad sin bloquear

- Mantener `backend-test` como gate estable (smoke suite).
- Ejecutar `backend-full-suite-report` no bloqueante con artefactos JUnit.
- Publicar resumen de fallos por run para priorización semanal.

### Fase 2 (corto plazo): Deduplicación por dominio

Eliminar redundancias funcionales en dominios con mayor deuda:

1. Auth
2. OAuth
3. Notifications
4. Search
5. Bulk operations

Regla de consolidación:

- Mantener una prueba canónica por comportamiento.
- Fusionar variantes `coverage/extended/real` cuando validan el mismo contrato.
- Si una variante aporta valor único, convertirlo en caso parametrizado.

### Fase 3 (mediano plazo): Gobernanza de suite

- Etiquetar pruebas con markers (`unit`, `integration`, `e2e`, `smoke`, `security`, `flaky`).
- Definir ownership por dominio de pruebas.
- Establecer SLA de estabilización:
  - `flaky`: resolver o deshabilitar con ticket en <= 2 sprints.
- Rehabilitar gating más estricto cuando los dominios P0 estén estables.

---

## Criterios de éxito

1. Reducción de archivos duplicados `coverage/extended/real` >= 40%.
2. Full suite no bloqueante con artefactos en 100% de runs.
3. Tendencia descendente semanal de `failed + error` en full suite.
4. Suite smoke bloqueante estable por 2 semanas consecutivas.

---

## Backlog inicial sugerido

- [x] Inventario de duplicaciones Auth (`test_auth_*`, `*_coverage`, `*_extended`).
- [x] Inventario de duplicaciones OAuth (`test_oauth_*` en unit/integration/e2e).
- [x] Unificar notificaciones (`test_notification_*` vs `test_notifications_*`).
- [x] Consolidar Search tests con enfoque por contratos.
- [ ] Definir y aplicar marker `flaky` a tests inestables conocidos.

---

## Progreso ejecutado (2026-02-18)

Primera y segunda ola de deduplicación aplicadas en `backend/tests/unit/api`:

- Eliminadas suites redundantes en Auth: `test_auth_endpoints_additional.py`, `test_auth_extended.py`.
- Eliminadas suites redundantes en Notifications: `test_notifications_endpoints.py`, `test_notifications_endpoints_extended.py`.
- Eliminadas suites redundantes en OAuth: `test_oauth_endpoints_extended.py`, `test_oauth_endpoints.py`.
- Eliminadas suites redundantes en Search: `test_search_endpoints.py`, `test_search_endpoints_real.py`, `test_search_extended.py`, `test_search_schemas.py`.

Notas:

- Se mantienen suites canónicas de comportamiento/cobertura por dominio (`*_coverage.py`, `*_additional.py` cuando aporta casos únicos).
- Validación local completa limitada en Windows por dependencia nativa de WeasyPrint (`libgobject-2.0-0`); validación final recomendada en CI Linux.
