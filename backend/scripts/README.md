# Development Scripts

This folder contains utility scripts for development, testing, and security auditing.

## Scripts

| Script                       | Description                                               |
| ---------------------------- | --------------------------------------------------------- |
| `create_test_user.py`        | Creates test users for E2E testing                        |
| `cleanup_e2e_users.py`       | Cleans up test users after E2E tests                      |
| `check_api_keys_columns.py`  | Validates API keys table schema                           |
| `check_policy.py`            | Validates RLS policies in database                        |
| `check_mypy_baseline.py`     | Checks MyPy errors against the committed baseline         |
| `generate_mypy_baseline.py`  | Regenerates the MyPy baseline JSON                        |
| `audit_scan.py`              | **Canonical** static AST security scanner (backend + frontend + infra) |
| `build_audit_tables.py`      | Generates Markdown report tables from `audit_scan.py` output |
| `run_semgrep_isolated.ps1`   | Runs Semgrep with custom rules in isolated mode (PowerShell) |

## Security Audit Scan

Run the AST-based static scanner from the **repo root**:

```powershell
# Run scan — outputs issues_full.json + issues_summary.json in backend/scripts/
python backend/scripts/audit_scan.py

# Generate Markdown tables (label is used in headings only)
python backend/scripts/build_audit_tables.py "N43"
```

The JSON outputs (`issues_full.json`, `issues_summary.json`, `issues_table_*.md`) are
listed in `.gitignore` — they are ephemeral scan artifacts, not source code.

## Usage

General scripts are for local development only. Run them from the backend directory:

```bash
cd backend
python -m scripts.create_test_user
```

> ⚠️ **Warning:** These scripts are not meant for production use.
