# Semana 2 — Frontend Coverage Execution Plan

**Fecha de inicio:** 2026-02-18
**Objetivo de semana:** consolidar cobertura frontend en áreas de mayor riesgo y reducir deuda de calidad en tests (warnings `act(...)`, ramas no cubiertas).

---

## 1) Baseline de entrada (medición actual)

Resultado de `npm run test:coverage` (frontend):

- Statements: **61.99%**
- Branches: **57.54%**
- Functions: **60.63%**
- Lines: **63.21%**

Esto supera el umbral mínimo histórico de 50% statements, por lo que Semana 2 se centra en **calidad de cobertura** y no solo en volumen.

### Medición de cierre parcial (post Bloque B)

Resultado de `npm run test:coverage` (frontend, 2026-02-18):

- Test files: **55 passed**
- Tests: **574 passed**
- Statements: **65.60%** (**+3.61** vs baseline)
- Branches: **59.56%** (**+2.02** vs baseline)
- Functions: **65.24%** (**+4.61** vs baseline)
- Lines: **67.08%** (**+3.87** vs baseline)

### Medición de cierre final (Semana 2 completa)

Resultado de `npm run test:coverage` (frontend, 2026-02-18):

- Test files: **55 passed**
- Tests: **598 passed**
- Statements: **72.43%** (**+10.44** vs baseline)
- Branches: **65.06%** (**+7.52** vs baseline)
- Functions: **69.01%** (**+8.38** vs baseline)
- Lines: **74.11%** (**+10.90** vs baseline)

Hotspots impactados en Semana 2:

- `src/pages/profile/ProfilePage.tsx`: **34.61% → 80.76%** statements.
- `src/pages/data/DataExchangePage.tsx`: **42.26% → 85.71%** statements.
- `src/components/notifications/NotificationsDropdown.tsx`: **34.92% → 87.30%** statements.
- `src/pages/security/MFASettingsPage.tsx`: **47.65% → 67.78%** statements.

---

## 2) Backlog priorizado (6–8 áreas)

Prioridad por impacto (riesgo x bajo coverage actual):

1. `src/services/api.ts` (15.21%)
   - Validar interceptors, manejo 401/403, refresh y retries.
2. `src/pages/admin/TenantsPage.tsx` (38.23%)
   - Flujos de carga, errores de fetch y edge cases de permisos.
3. `src/pages/profile/ProfilePage.tsx` (34.61%)
   - Actualización de perfil/avatar, errores y rollback visual.
4. `src/pages/data/DataExchangePage.tsx` (41.66%)
   - Import/export con estados de progreso y fallos controlados.
5. `src/pages/users/UsersPage.tsx` (44.08%)
   - Filtrado, paginación y paths de error.
6. `src/pages/settings/ApiKeysPage.tsx` (44.80%)
   - CRUD de claves y estados de revocación.
7. `src/pages/security/MFASettingsPage.tsx` (47.65%)
   - Activación/desactivación MFA y errores de token.
8. `src/components/notifications/NotificationsDropdown.tsx` (34.92%)
   - Render condicional, acciones y side-effects.

---

## 3) Calidad de test (deuda inmediata)

Se detectaron warnings recurrentes en pruebas:

- `NotificationsPage.test.tsx` (`act(...)`)
- `DataExchangePage.test.tsx` (`act(...)`)

Acción de Semana 2:

- Normalizar helpers async (`waitFor`, `findBy*`, `userEvent` await).
- Eliminar warnings `act(...)` en los tests priorizados.

Estado actual:

- ✅ Refactor aplicado en `NotificationsPage.test.tsx` para interacciones async.
- ✅ Refactor aplicado en `DataExchangePage.test.tsx` para interacciones async.
- ✅ Corrida focalizada verde en ambos archivos.

---

## 4) Definición de Done (Semana 2)

1. Mantener coverage global >= 60% statements.
2. Aumentar al menos +3 puntos de branch coverage global.
3. Reducir warnings `act(...)` a 0 en archivos priorizados.
4. No introducir regresiones en lint/type-check/tests.

Estado actual contra DoD:

- ✅ DoD 1 cumplido (72.43% statements).
- ✅ DoD 2 cumplido (+7.52 branch points).
- ✅ DoD 3 cumplido en archivos priorizados de esta semana.
- ✅ DoD 4 cumplido en corridas focalizadas y cobertura completa.

---

## 5) Ejecución sugerida por bloques

- Bloque A: `api.ts` + `apiKeysService.ts`
- Bloque B: `UsersPage.tsx` + `TenantsPage.tsx`
- Bloque C: `ProfilePage.tsx` + `MFASettingsPage.tsx`
- Bloque D: `DataExchangePage.tsx` + `NotificationsDropdown.tsx`

Cada bloque cierra con corrida de tests focalizada y luego cobertura completa.

## 6) Avance de ejecución

- ✅ **Bloque A completado**
  - Tests activos y verdes en `src/services/api.test.ts` y `src/services/apiKeysService.test.ts`.
- ✅ **Bloque B completado**
  - Tests ampliados y verdes en `src/pages/users/UsersPage.test.tsx` y `src/pages/admin/TenantsPage.test.tsx` (**30 tests passing** en corrida focalizada).
- ✅ **Bloque C completado**
  - Tests ampliados y verdes en `src/pages/profile/ProfilePage.test.tsx` y `src/pages/security/MFASettingsPage.test.tsx`.
- ✅ **Bloque D completado**
  - Tests ampliados y verdes en `src/pages/data/DataExchangePage.test.tsx` y `src/components/notifications/NotificationsDropdown.test.tsx`.

### Estado de Semana 2

- ✅ **Semana 2 cerrada**: objetivo de cobertura consolidado y mejora de branches por encima del target.
