# Roadmap Operativo v1.0.0

**Fecha:** 2026-02-18
**Horizonte:** 30 días
**Objetivo:** cerrar brechas de release para pasar de beta (v0.9.5) a producción (v1.0.0) con gates verificables en CI/CD.

---

## 1) Criterios de salida (Go/No-Go)

La release v1.0.0 se considera **Go** cuando se cumpla todo lo siguiente:

1. **CI bloqueante en calidad y seguridad**
   - Lint + format + type-check + tests + security scans en verde.
   - Sin `continue-on-error` en checks críticos de release.

2. **Cobertura frontend >= 50% (statements)**
   - Sin reducir umbrales para “pasar” artificialmente.
   - Tendencia de cobertura estable o ascendente.

3. **Deuda MyPy backend controlada**
   - Opción A: 0 errores.
   - Opción B (transitoria): baseline formal versionada + budget de reducción semanal + fecha de eliminación.

4. **E2E críticos estables**
   - Flujos mínimos de negocio y seguridad ejecutados en CI.

5. **Documentación sincronizada**
   - Una única “fuente de verdad” para métricas de release.

---

## 2) Brechas actuales (baseline)

- Frontend coverage aproximada: **~32% statements**.
- MyPy backend: **deuda pendiente** (actualmente no bloqueante en CI).
- Backend E2E: cobertura parcial en flujos críticos.
- Inconsistencias documentales históricas entre estado, agentes y roadmap.

---

## 3) Plan por semanas (30 días)

## Semana 1 — Alineación y gates

**Objetivo:** cerrar inconsistencias y definir reglas de release.

- Congelar criterios Go/No-Go de v1.0.0 (este documento + PROJECT_STATUS).
- Confirmar qué checks CI son críticos y cuáles informativos.
- Definir baseline MyPy por módulo (si se usa estrategia transitoria).
- Publicar tablero de seguimiento (P0/P1/P2 + dueño + fecha).

**Entregables:**

- Criterios de salida aprobados.
- Matriz de checks CI (blocking vs non-blocking).
- Baseline de deuda técnica inicial.

## Semana 2 — Cobertura frontend (P0)

**Objetivo:** subir cobertura de ~32% a >=42% con foco en riesgo.

- Priorizar tests en páginas y servicios críticos:
  - auth/login/refresh/logout
  - users/roles/tenants
  - notifications y manejo de errores
- Aumentar cobertura de ramas de error y permisos.
- Evitar tests frágiles de snapshots masivos.

**Entregables:**

- +10 puntos de coverage statements.
- Reporte de áreas cubiertas por riesgo.

## Semana 3 — MyPy + E2E críticos (P0)

**Objetivo:** reducir deuda de tipado y estabilizar pruebas end-to-end mínimas.

- Reducir errores MyPy por dominios de mayor impacto.
- Definir conjunto mínimo de E2E bloqueante:
  - autenticación completa (incl. expiración/refresh)
  - aislamiento multi-tenant
  - autorización por permisos
  - operación crítica de datos
- Corregir flakiness y tiempos de ejecución.

**Entregables:**

- Deuda MyPy bajo umbral acordado o 0 errores.
- Suite E2E crítica ejecutándose estable en CI.

## Semana 4 — Hardening de release

**Objetivo:** validar readiness de producción y cerrar pendientes.

- Rehabilitar gates bloqueantes finales para release.
- Ejecutar rehearsal de despliegue en staging.
- Correr checklist pre-producción (secrets, cookies, CORS, TLS, docs).
- Congelar scope (solo fixes de release, sin nuevas features).

**Entregables:**

- Release Candidate v1.0.0-rc.
- Go/No-Go final documentado.

---

## 4) Backlog priorizado

## P0 (bloquea v1.0.0)

- Cobertura frontend >=50%.
- Strategy MyPy cerrada y aplicada (ideal: gate bloqueante).
- E2E críticos en verde.
- CI de release sin checks críticos en modo informativo.

## P1 (alta prioridad, no bloqueante inmediato)

- Mejorar cobertura ES/PT en calidad lingüística (no solo claves).
- Reducir tiempo total de CI y estabilizar tests intermitentes.
- Fortalecer observabilidad de errores de negocio en staging.

## P2 (post v1.0.0)

- Expansión de cobertura frontend >60%.
- Más E2E en casos no críticos.
- Optimización de performance en rutas secundarias.

---

## 5) Gobierno operativo

- **Cadencia:** checkpoint diario corto + revisión semanal de métricas.
- **Métricas semanales obligatorias:**
  - Coverage frontend (statements/branches)
  - Errores MyPy
  - Tasa de éxito E2E críticos
  - Tiempo total de CI
- **Política de cambios:** durante las últimas 2 semanas, solo fixes alineados a P0/P1.

---

## 6) Riesgos y mitigación

1. **No alcanzar cobertura frontend >=50%**
   Mitigación: priorizar tests por riesgo y no por volumen.

2. **Deuda MyPy excesiva para cierre completo**
   Mitigación: baseline formal + budget de quema semanal + deadline firme.

3. **Flakiness en E2E**
   Mitigación: reducir dependencias externas, datos determinísticos y retries controlados.

4. **Desalineación documental futura**
   Mitigación: actualizar PROJECT_STATUS en cada hito y usarlo como fuente de verdad.

---

## 7) Decisión final de release

- **Go:** todos los criterios de salida cumplidos.
- **No-Go:** cualquier P0 abierto o gate crítico no confiable.

Este plan se actualiza semanalmente hasta la salida de v1.0.0.
