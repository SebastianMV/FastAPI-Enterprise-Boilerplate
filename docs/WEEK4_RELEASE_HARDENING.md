# Semana 4 — Hardening de Release (Ejecución)

**Fecha:** 2026-02-19
**Objetivo:** validar readiness de producción, cerrar hardening operativo y documentar decisión Go/No-Go parcial.

---

## 1) Resumen ejecutivo

Estado general al corte:

- **Semana 4:** 🟡 En progreso
- **Readiness:** **Production candidate** (cerca de producción, con pendientes operativos explícitos)
- **Go/No-Go parcial:** **No-Go temporal** hasta cerrar el blocker operativo de staging (db/redis no levantan por conflicto de hardening runtime).

---

## 2) Evidencia validada en este corte

### Calidad y estabilidad

- Frontend coverage consolidada Semana 2: **72.43% statements**, **65.06% branches**.
- MyPy backend validado contra baseline:
  - Baseline: **282**
  - Current: **225**
  - Delta: **-57**
  - Resultado: ✅ sin regresión
- Subset E2E crítico (8 nodeids): **8/8 passing** ✅

### CI / Gates

- CI tiene gates bloqueantes activos para:
  - backend smoke tests
  - subset E2E crítico Linux
  - security scan
  - SAST (Semgrep baseline gate)
  - quality guardian
- Decisión final Week4 aplicada para MyPy en CI:
  - no regresión vs baseline **y**
  - cap absoluto de release: `--max-total 225`.

### Infraestructura/hardening

- Imágenes en staging/prod: minor pinning correcto (`postgres:17.7-alpine`, `redis:7.4-alpine`).
- Restricciones de contenedor presentes en staging/prod:
  - `security_opt: no-new-privileges:true`
  - `cap_drop: ALL`
- Ajuste aplicado en Semana 4:
  - `AUTH_COOKIE_SECURE` ahora requiere valor explícito en staging/prod:
    - `${AUTH_COOKIE_SECURE:?AUTH_COOKIE_SECURE must be set}`

### Rehearsal de staging (ejecución y evidencia)

Ejecución realizada:

1. `docker compose -f docker-compose.staging.yml config -q` ✅
2. `docker compose -f docker-compose.staging.yml up -d --build` ⚠️
3. `docker compose -f docker-compose.staging.yml down` ✅ (rollback validado)

Resultados observados:

- Build de imágenes backend/frontend completado.
- Fallo de arranque en `staging-db` y `staging-redis` por runtime hardening:
  - `error: failed switching to 'postgres': operation not permitted`
  - `error: failed switching to "redis": operation not permitted`
- Causa probable: combinación `security_opt: no-new-privileges:true` + flujo de entrypoint que requiere cambio de usuario en imágenes oficiales.
- Estado del rehearsal: **ejecutado con evidencia, pero no exitoso** (blocker operativo abierto).

---

## 3) Semáforo de readiness

| Área | Estado | Comentario |
|---|---|---|
| Seguridad de plataforma | 🟢 | Hardening y auditorías maduros (38 ciclos) |
| Calidad frontend | 🟢 | Cobertura y estabilidad por encima de objetivo |
| E2E crítico | 🟢 | 8/8 estable en corrida de verificación |
| CI release gates | 🟢 | Gates clave activos + política final MyPy aplicada |
| Tipado backend (MyPy) | 🟡 | Tendencia positiva, deuda remanente relevante |
| Rehearsal staging | 🔴 | Ejecutado, pero fallido por conflicto runtime en db/redis |
| Go/No-Go final | 🔴 | Pendiente cierre de puntos amarillos/rojos |

---

## 4) Pendientes mínimos para pasar a Go

1. Ejecutar **rehearsal de despliegue en staging** con evidencia:
  - resolver conflicto runtime de `db/redis` con hardening actual
  - repetir deploy + migraciones + smoke + rollback
2. Cerrar checklist preproducción con evidencias (secrets, CORS, cookies, TLS, observabilidad).

---

## 5) Artefactos relacionados

- `docs/WEEKLY_RELEASE_METRICS.md`
- `docs/ROADMAP_1_0_OPERATIONAL_PLAN.md`
- `PROJECT_STATUS.md`
- `docs/WEEK3_MYPY_E2E_EXECUTION.md`
