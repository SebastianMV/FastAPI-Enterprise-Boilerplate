# FastAPI Enterprise Boilerplate - Backend

Production-ready FastAPI backend with JWT authentication, ACL, multi-tenant RLS, and hexagonal architecture.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload
```

## Development

```bash
# Install with dev dependencies
pip install -e .[dev]

# Run tests
pytest
```

## Maintenance Scripts

### Create Test User

```bash
python create_test_user.py
```

Creates a test user `test@example.com` with password `Test123!` for development.

### Cleanup E2E Test Users

E2E tests create temporary users with emails like `e2e_*@example.com`. To clean them up:

```bash
# Using Docker:
make cleanup-e2e
# or PowerShell:
Cleanup-E2EUsers

# Locally:
python cleanup_e2e_users.py
```

This script removes all users created during end-to-end testing.

For full documentation, see the [project README](../README.md).
