# Development Scripts

This folder contains utility scripts for development and testing purposes.

## Scripts

| Script                 | Description                          |
| ---------------------- | ------------------------------------ |
| `create_test_user.py`  | Creates test users for E2E testing   |
| `cleanup_e2e_users.py` | Cleans up test users after E2E tests |

## Usage

These scripts are intended for local development only. Run them from the backend directory:

```bash
cd backend
python -m scripts.create_test_user
```

> ⚠️ **Warning:** These scripts are not meant for production use.
