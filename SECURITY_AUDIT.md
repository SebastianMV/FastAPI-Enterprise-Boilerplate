# 🛡️ SECURITY AUDIT — FastAPI-Enterprise-Boilerplate

> **Auditoría N°43** | Fecha: 2026-02-20 | Auditor: security-auditor
> **Auditorías previas:** 42 | **0 regresiones toleradas**

## 📋 Resumen Ejecutivo

- **Nuevos hallazgos:** 2 (0 críticos, 0 altos, 1 medio, 1 bajo) — ambos **CORREGIDOS**
- **Regresiones detectadas:** 0
- **Estado:** ✅ LIMPIO (sin hallazgos significativos abiertos)
- **Cobertura manual:** 19 endpoints, 3 middlewares, 2 servicios de infra, 1 config
- **Meta-tests:** ❌ bloqueado por dependencia nativa de WeasyPrint en Windows (`libgobject-2.0-0`)

## 🟡 MEDIUM (Sev 5-6)

### M-01: Stored XSS — `create_schedule` / `update_schedule` — `report_templates.py` ✅ CORREGIDO

- **OWASP:** A03:2021 Injection (XSS)
- **CWE:** CWE-79
- **Archivos:** `backend/app/api/v1/endpoints/report_templates.py`
- **Riesgo:** `ScheduledReportCreate.name` y `.description` eran almacenados en el dict in-memory sin pasar por `_html.escape()`, a diferencia de `ReportTemplateCreate` (que sí los escapaba). Si esos campos se renderizan en un contexto HTML (email de notificación, reporte HTML, reporte PDF con HTML interno), constituyen un vector de XSS almacenado.
- **Regla violada:** Regla 9 (`html.escape()` antes de interpolación en HTML)
- **FIX aplicado:**
  - `create_schedule`: Se aplica `_html.escape()` a `name` y `description` en la construcción del dict del schedule.
  - `update_schedule`: Se agrega bloque de escape selectivo de campos string sensibles (`name`, `description`) antes del merge al dict almacenado, siguiendo el mismo patrón que `update_template`.
- **Verificación:** Buscar `request.name` raw en el scope de `create_schedule`/`update_schedule` → resultado: 0.

## 🟢 LOW / HARDENING (Sev 3-4)

### L-01: Detección de tipo de archivo solo por extensión en `import_data` — `data_exchange.py` ✅ CORREGIDO

- **OWASP:** A05:2021 Security Misconfiguration
- **CWE:** CWE-434
- **Archivo:** `backend/app/api/v1/endpoints/data_exchange.py`
- **Riesgo:** El endpoint `POST /data/import/{entity}` detectaba el tipo de archivo exclusivamente vía `filename.endswith()`. Un atacante podría renombrar un archivo binario (`.xlsx`) como `.csv` o viceversa para provocar confusión en el parser subyacente.
- **FIX aplicado:** Tras el `await file.seek(0)` post size-check, se leen los primeros 8 bytes (magic bytes) y se valida coherencia extensión↔contenido:
  - `.csv` no puede comenzar con magic XLSX (`PK\x03\x04`) ni XLS (`\xD0\xCF\x11\xE0`).
  - `.xlsx/.xls` debe comenzar con uno de esos dos magic bytes.
  - Se añade `.lower()` al `endswith()` para aceptar `.CSV`, `.XLSX`, etc.
- **Verificación:** Enviar un archivo `.xls` renombrado a `.csv` → HTTP 400 `FILE_TYPE_MISMATCH`.

### PENDIENTES (de auditorías anteriores)

- [ ] Ajustar reglas Semgrep para reducir FPs en `endpoint-missing-tenant-id` cuando existe alias `tenant_id: CurrentTenantId = None`.
- [ ] Ajustar regla `no-stdlib-logging` para excluir `backend/app/infrastructure/observability/logging.py` (módulo wrapper legítimo).
- [ ] Ejecutar `pytest backend/tests/security/test_security_meta.py -v` en entorno Linux con librerías nativas de WeasyPrint instaladas.
- [ ] Migrar `report_templates` y `scheduled_reports` de in-memory a storage persistente (base de datos) para uso en producción.
- [ ] Agregar resolución DNS en tiempo de validación en `_validate_webhook_url` para mitigar DNS rebinding / SSRF completo (actualmente bloqueado por `_check_demo_mode()` en prod/staging).

### Ejecución recomendada (AST scan canónico)

```powershell
# Run static AST scan (outputs issues_full.json + issues_summary.json in backend/scripts/)
python backend/scripts/audit_scan.py

# Generate Markdown report tables from scan output
python backend/scripts/build_audit_tables.py "N43"
```

```powershell
# Semgrep scan (aislado)
pwsh -File backend/scripts/run_semgrep_isolated.ps1
```

## 🔄 REGRESIONES (issues que volvieron a aparecer)

- Ninguna.

## 📊 Cobertura del Scan (Auditoría N°43)

| Área                         | Archivos | Revisados | Issues         |
| ---------------------------- | -------- | --------- | -------------- |
| Backend endpoints            | 19       | 19        | 2 (corregidos) |
| Backend infra / middleware   | 7        | 7         | 0              |
| Backend config & deps        | 2        | 2         | 0              |
| Docker/CI                    | 8        | 0         | N/A (sin cambios desde N°42) |
