# 🛡️ SECURITY AUDIT — FastAPI-Enterprise-Boilerplate

> **Auditoría N°42** | Fecha: 2026-02-18 | Auditor: security-auditor
> **Auditorías previas:** 41 | **0 regresiones toleradas**

## 📋 Resumen Ejecutivo

- **Nuevos hallazgos:** 1 (0 críticos, 0 altos, 1 medio)
- **Regresiones detectadas:** 0
- **Estado:** ✅ LIMPIO (sin hallazgos significativos abiertos)
- **Semgrep ejecutado:** ✅ (entorno aislado via `backend/scripts/run_semgrep_isolated.ps1`)
- **Meta-tests:** ❌ bloqueado por dependencia nativa de WeasyPrint en Windows (`libgobject-2.0-0`)

## 🟡 MEDIUM (Sev 5-6)

### M-01: Interpolación SQL en tenant context setter — `backend/app/infrastructure/database/connection.py:104`

- **OWASP:** A03:2021 Injection
- **CWE:** CWE-89
- **Riesgo:** Uso de `text(f"...")` en statement SQL; aunque había validación UUID previa, se endurece a bind params para eliminar superficie de interpolación.
- **Regla 19 violada:** N/A (hardening adicional)
- **FIX:**
  ```python
  await session.execute(
      text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
      {"tenant_id": validated},
  )
  ```
- **Verificación:** Semgrep post-fix (`semgrep.no-raw-sql-fstring=0`)

## 🟢 LOW / HARDENING (Sev 3-4)

- [x] Aislar Semgrep en `.venv-semgrep` para evitar conflictos con la `.venv` principal.
- [ ] Ajustar reglas Semgrep para reducir FPs en `endpoint-missing-tenant-id` cuando existe alias `tenant_id: CurrentTenantId = None`.
- [ ] Ajustar regla `no-stdlib-logging` para excluir explícitamente `backend/app/infrastructure/observability/logging.py` (módulo wrapper legítimo).
- [ ] Ejecutar `pytest backend/tests/security/test_security_meta.py -v` en entorno Linux con librerías nativas de WeasyPrint instaladas.

### Ejecución recomendada (aislada)

```powershell
pwsh -File backend/scripts/run_semgrep_isolated.ps1
```

## 🔄 REGRESIONES (issues que volvieron a aparecer)

- Ninguna.

## 📊 Cobertura del Scan

| Área              | Archivos | Escaneados | Issues        |
| ----------------- | -------- | ---------- | ------------- |
| Backend endpoints | 19       | 19         | 0             |
| Backend infra     | 58       | 58         | 1 (corregido) |
| Frontend pages    | 38       | 38         | 0             |
| Frontend services | 31       | 31         | 0             |
| Docker/CI         | 8        | 8          | 0             |
