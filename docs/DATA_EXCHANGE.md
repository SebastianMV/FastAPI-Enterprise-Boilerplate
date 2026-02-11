# Data Exchange System

This document describes the Data Exchange functionality for import, export, and report generation.

## Overview

The Data Exchange system provides a **flexible, entity-based** approach to data import/export and report generation. It's designed to work with any entity in the system through configuration.

| Feature | Description |
| --- | --- |
| **Dynamic Entities** | Configure any entity for import/export/reports |
| **Multiple Formats** | CSV, Excel (XLSX), JSON, PDF, HTML |
| **Field Validation** | Type validation, custom validators, transformers |
| **Tenant Isolation** | Respects RLS for multi-tenant data |
| **Dry Run Import** | Validate before committing |
| **Template Generation** | Download import templates |

## Quick Start

### List Available Entities

```http
GET /api/v1/data/entities
Authorization: Bearer {access_token}
```

Response:

```json
[
  {
    "name": "users",
    "display_name": "Users",
    "exportable": true,
    "importable": true,
    "fields": [
      {"name": "email", "display_name": "Email", "field_type": "email", "required": true},
      {"name": "first_name", "display_name": "First Name", "field_type": "string", "required": true}
    ]
  }
]
```

### Export Data

```http
GET /api/v1/data/export/users?format=csv
Authorization: Bearer {access_token}
```

Returns CSV file with user data.

### Import Data

```http
POST /api/v1/data/import/users?mode=upsert&dry_run=false
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: users.csv
```

Response:

```json
{
  "total_rows": 100,
  "inserted": 85,
  "updated": 10,
  "skipped": 5,
  "error_count": 0,
  "errors": [],
  "warnings": [],
  "dry_run": false,
  "success": true
}
```

### Generate Report

```http
POST /api/v1/data/reports/users
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "title": "Active Users Report",
  "format": "pdf",
  "filters": [
    {"field": "is_active", "operator": "eq", "value": true}
  ],
  "columns": ["email", "first_name", "last_name", "created_at"],
  "include_summary": true
}
```

Returns PDF report file.

---

## API Reference

### Entity Discovery

#### GET /data/entities

List all available entities for data exchange.

#### GET /data/entities/{entity}

Get detailed information about a specific entity.

### Export Endpoints

#### GET /data/export/{entity}

Export data from an entity.

| Parameter | Type | Description |
| --- | --- | --- |
| `format` | string | `csv`, `excel`, `json` (default: csv) |
| `columns` | string | Comma-separated column names |

#### GET /data/export/{entity}/preview

Get a preview of data to be exported.

| Parameter | Type | Description |
| --- | --- | --- |
| `limit` | int | Max rows to preview (1-100) |

### Import Endpoints

#### GET /data/import/{entity}/template

Download an empty template for importing data.

| Parameter | Type | Description |
| --- | --- | --- |
| `format` | string | `csv`, `excel` (default: csv) |

#### POST /data/import/{entity}

Import data from a file.

| Parameter | Type | Description |
| --- | --- | --- |
| `file` | file | CSV or Excel file |
| `mode` | string | `insert`, `upsert`, `update_only` |
| `dry_run` | bool | Validate without importing |
| `skip_errors` | bool | Continue on errors |

### Report Endpoints

#### POST /data/reports/{entity}

Generate a report.

Request body:

```json
{
  "title": "Report Title",
  "format": "pdf|excel|csv|html",
  "filters": [{"field": "...", "operator": "eq", "value": "..."}],
  "columns": ["field1", "field2"],
  "group_by": ["field"],
  "sort_by": "field",
  "include_summary": true,
  "date_range_field": "created_at",
  "date_from": "2026-01-01",
  "date_to": "2026-12-31"
}
```

#### GET /data/reports/{entity}/preview

Get a preview of report data.

#### GET /data/reports/{entity}/summary

Get summary statistics without generating the full report.

---

## Field Types

| Type | Description | Validation |
| --- | --- | --- |
| `string` | Text field | None |
| `integer` | Whole number | Numeric check |
| `float` | Decimal number | Numeric check |
| `boolean` | True/False | true/false, 1/0, yes/no |
| `email` | Email address | Format validation |
| `uuid` | UUID identifier | UUID format check |
| `date` | Date only | YYYY-MM-DD format |
| `datetime` | Date and time | ISO 8601 format |
| `enum` | Fixed choices | Valid choice check |
| `json` | JSON object | Valid JSON check |

---

## Import Modes

| Mode | Description |
| --- | --- |
| `insert` | Only insert new records (error on duplicates) |
| `upsert` | Insert new, update existing (match by unique fields) |
| `update_only` | Only update existing records |

---

## Adding Custom Entities

### 1. Create Entity Configuration

```python
from app.domain.ports.data_exchange import EntityConfig, FieldConfig, FieldType
from app.infrastructure.data_exchange import register_entity

# Define fields
CONDOMINIUM_FIELDS = [
    FieldConfig(
        name="id",
        display_name="ID",
        field_type=FieldType.UUID,
        exportable=True,
        importable=False,  # Auto-generated
    ),
    FieldConfig(
        name="name",
        display_name="Name",
        field_type=FieldType.STRING,
        required=True,
        exportable=True,
        importable=True,
    ),
    FieldConfig(
        name="address",
        display_name="Address",
        field_type=FieldType.STRING,
        required=True,
        exportable=True,
        importable=True,
    ),
    FieldConfig(
        name="unit_count",
        display_name="Number of Units",
        field_type=FieldType.INTEGER,
        required=False,
        exportable=True,
        importable=True,
        default=0,
    ),
]

# Create configuration
CONDOMINIUM_CONFIG = EntityConfig(
    name="condominiums",
    display_name="Condominiums",
    model=CondominiumModel,  # SQLAlchemy model
    fields=CONDOMINIUM_FIELDS,
    permission_resource="condominiums",
    unique_fields=["name"],  # For upsert matching
)

# Register at app startup
register_entity(CONDOMINIUM_CONFIG)
```

### 2. Custom Validators

```python
def validate_phone(value: str) -> bool:
    """Validate phone number format."""
    import re
    pattern = r'^\+?[0-9]{10,15}$'
    return bool(re.match(pattern, value))

FieldConfig(
    name="phone",
    display_name="Phone",
    field_type=FieldType.STRING,
    validator=validate_phone,
)
```

### 3. Custom Transformers

```python
def normalize_phone(value: str) -> str:
    """Normalize phone number format."""
    digits = ''.join(c for c in value if c.isdigit())
    return f"+{digits}" if not digits.startswith('+') else digits

FieldConfig(
    name="phone",
    display_name="Phone",
    field_type=FieldType.STRING,
    transformer=normalize_phone,
)
```

---

## Built-in Entities

The following entities are pre-configured:

| Entity | Exportable | Importable | Notes |
| --- | --- | --- | --- |
| `users` | ✅ | ✅ | User accounts |
| `tenants` | ✅ | ✅ | Tenant organizations |
| `roles` | ✅ | ✅ | Permission roles |
| `audit_logs` | ✅ | ❌ | Read-only audit trail |

---

## Optional Dependencies

| Package | Required For | Install |
| --- | --- | --- |
| `openpyxl` | Excel (XLSX) support | `pip install openpyxl` |
| `weasyprint` | PDF generation | `pip install weasyprint` |

Without these packages, the system gracefully falls back to CSV/HTML formats.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                       │
│  /data/entities, /data/export, /data/import, /data/reports  │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│                    Domain Ports                              │
│  EntityRegistry, ImportPort, ExportPort, ReportPort          │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│                 Infrastructure                               │
│  GenericImporter, GenericExporter, GenericReporter           │
│  CSVHandler, ExcelHandler                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

1. **Permission Checks**: Each entity has a `permission_resource` for ACL validation
2. **Tenant Isolation**: All operations respect RLS tenant boundaries
3. **File Validation**: Uploaded files are validated before processing
4. **Rate Limiting**: Consider adding rate limits for bulk operations
5. **Audit Logging**: Import/export operations are logged

---

## Performance Tips

1. **Use `dry_run`** first to validate large imports
2. **Limit export columns** to only needed fields
3. **Use pagination** for large exports (implement in queries)
4. **Batch processing** is built into imports (default 100 records)
5. **Consider async** for very large files

---

**Last Updated:** February 2, 2026  
**Version:** 1.3.9
