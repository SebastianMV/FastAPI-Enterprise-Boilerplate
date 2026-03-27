# Getting Started

> For quick Docker/local setup commands and credentials table, see [README.md](../README.md#-quick-start).
> This document expands on **first-time setup**, **verification**, and **configuration**.

## Prerequisites

- Docker & Docker Compose (recommended)
- **OR** for local development:
  - Python 3.13+
  - Node.js 24 LTS (Krypton) — active LTS until Apr 2028
  - PostgreSQL 17+ (if not using Docker)

### First-Time Setup

On first startup, the backend automatically runs Alembic migrations which create:

#### ✅ What Gets Created

1. **Default Tenant**: "Default Organization"
2. **Development Users** (see credentials table)
3. **ACL Roles** with permissions:
   - **superadmin**: Full access (`*:*`)
   - **admin**: User and tenant management
   - **user**: Basic access (profile only)

#### 🔑 Development Credentials

| User                 | Email                 | Password      | Role       |
| -------------------- | --------------------- | ------------- | ---------- |
| System Administrator | `admin@example.com`   | `Admin123!`   | superadmin |
| Tenant Manager       | `manager@example.com` | `Manager123!` | admin      |
| Demo User            | `user@example.com`    | `User123!`    | user       |

> 🚨 **SECURITY WARNING - DEVELOPMENT ONLY**
>
> These users are **automatically created by migrations** for testing. They have **known public passwords**.
>
> 📖 **For production deployment instructions**, see the complete [Production Security & Initial Setup Guide](./DEPLOYMENT.md#production-security--initial-setup).

#### ✅ Verification

```bash
# Check backend logs for successful migrations
docker compose logs backend | grep "Alembic migrations applied successfully"

# Test login with admin user
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "Admin123!"}'
```

> **Note**: Migrations are idempotent - safe for subsequent restarts.

**Useful commands:**

```bash
# Stop services
docker compose down

# Rebuild containers
docker compose up -d --build

# View all logs
docker compose logs -f

# Execute commands in containers
docker compose exec backend python -m pytest
docker compose exec backend alembic upgrade head

# Clean everything (including volumes)
docker compose down -v
```

### Production Environment

Optimized builds with nginx for frontend and multi-worker uvicorn for backend.

```bash
# 1. Set production environment variables
cp .env.example .env
# Edit .env with production values (database, secrets, etc.)

# 2. Build and start production containers
docker compose -f docker-compose.deploy.yml up -d --build

# 3. Check health
curl http://localhost:8000/health
curl http://localhost:80/health
```

**Production features:**

- Multi-stage Docker builds (smaller images)
- Nginx serving static frontend
- Uvicorn with 4 workers
- Non-root users for security
- Resource limits configured
- Health checks enabled
- Auto-restart on failure

**Access:**

- API: <http://localhost:8000>
- Frontend: <http://localhost:80>

## 💻 Local Development (Without Docker)

See [README.md § Local Development](../README.md#-local-development-without-docker) for setup commands.

## Configuration

Environment variables (`.env`):

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT (CHANGE IN PRODUCTION!)
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Environment
ENVIRONMENT=development
DEBUG=true
```

## Next Steps

1. [Security Features](./SECURITY.md) — Authentication, authorization, and security best practices
2. [Multi-Tenant RLS](./RLS_SETUP.md) — Row-Level Security setup
3. [API Reference](./API_REFERENCE.md) — Complete endpoint documentation
4. [Docker Guide](./DOCKER.md) — Docker configuration and troubleshooting
5. [Deployment](./DEPLOYMENT.md) — Production deployment guide
