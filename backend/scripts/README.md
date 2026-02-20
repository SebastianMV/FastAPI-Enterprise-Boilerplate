# Development Scripts

This folder contains utility scripts for development and testing purposes.

## Scripts

| Script                      | Description                              |
| --------------------------- | ---------------------------------------- |
| `create_test_user.py`       | Creates test users for E2E testing       |
| `cleanup_e2e_users.py`      | Cleans up test users after E2E tests     |
| `check_api_keys_columns.py` | Validates API keys table schema          |
| `check_policy.py`           | Validates RLS policies in database       |
| `generate_mypy_baseline.py` | Generates MyPy baseline JSON by module   |
| `check_mypy_baseline.py`    | Fails if MyPy debt increases vs baseline |

## Usage

These scripts are intended for local development only. Run them from the backend directory:

```bash
cd backend
python -m scripts.create_test_user
```

MyPy baseline workflow:

```bash
cd backend
mypy app --show-error-codes --no-color-output > mypy-report.txt || true
python -m scripts.generate_mypy_baseline --report mypy-report.txt --output mypy-baseline.json
python -m scripts.check_mypy_baseline --baseline mypy-baseline.json --report mypy-report.txt
```

> ⚠️ **Warning:** These scripts are not meant for production use.
