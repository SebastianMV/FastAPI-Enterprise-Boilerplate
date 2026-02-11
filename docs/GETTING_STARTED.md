# Getting Started

## Prerequisites

- Docker & Docker Compose (recommended)
- **OR** for local development:
  - Python 3.13+
  - Node.js 22 LTS (Jod) - recommended for long-term support until Oct 2027
  - PostgreSQL 17+ (if not using Docker)

> **Security Note:** This project uses LTS (Long-Term Support) versions for maximum stability and security. All dependencies are regularly audited for vulnerabilities.

## 🐳 Docker Setup (Recommended)

### Development Environment

Perfect for local development with hot-reload for both backend and frontend.

```bash
# 1. Clone the repository
git clone https://github.com/SebastianMV/fastapi-enterprise-boilerplate.git
cd fastapi-enterprise-boilerplate

# 2. Copy environment file
cp .env.example .env

# 3. Start all services (with hot-reload)
docker compose up -d

# 4. Check status
docker compose ps

# 5. View logs
docker compose logs -f backend
docker compose logs -f frontend
```

**What's included:**

- Backend API with uvicorn auto-reload
- Frontend with Vite dev server (hot-reload)
- PostgreSQL 17 with health checks
- Redis for caching
- Volume mounting for live code changes

**Access:**

- API: <http://localhost:8000>
- API Docs: <http://localhost:8000/docs>
- Frontend: <http://localhost:3000>

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

| User                 | Email                  | Password      | Role       |
| -------------------- | ---------------------- | ------------- | ---------- |
| System Administrator | `admin@example.com`    | `Admin123!`   | superadmin |
| Tenant Manager       | `manager@example.com`  | `Manager123!` | admin      |
| Demo User            | `user@example.com`     | `User123!`    | user       |

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
docker compose -f docker-compose.prod.yml up -d --build

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

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

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

## Project Structure

```text
├── backend/
│   ├── app/
│   │   ├── api/           # Endpoints
│   │   ├── application/   # Use cases
│   │   ├── domain/        # Business logic
│   │   └── infrastructure/# Database, auth
│   ├── tests/
│   └── alembic/           # Migrations
├── frontend/
│   └── src/
├── docs/
└── docker-compose.yml
```

## Default Users (Development Only)

The database migrations create example users for development and testing:

| Email | Password | Role | Permissions |
| ------- | ---------- | ------ | ------------- |
| `admin@example.com` | `Admin123!` | **superadmin** | Full system access (`*:*`) |
| `manager@example.com` | `Manager123!` | **admin** | User & tenant management |
| `user@example.com` | `User123!` | **user** | Basic read access |

### Quick Login Test

```bash
# Login as admin
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "Admin123!"}'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Role Permissions

| Role | Permissions |
| ------ | ------------- |
| **superadmin** | `*:*` (all resources, all actions) |
| **admin** | `users:read`, `users:create`, `users:update`, `tenants:read`, `reports:*` |
| **user** | `users:read`, `profile:*` |

> 🚨 **CRITICAL: Production Security**
>
> **Before deploying to production, you MUST:**
>
> 1. Delete all development users (`admin@example.com`, `manager@example.com`, `user@example.com`)
> 2. Create secure production admin accounts
> 3. Change all default passwords and secrets
>
> 📖 **Complete step-by-step guide:** [Production Security & Initial Setup](./DEPLOYMENT.md#production-security--initial-setup)

## Next Steps

1. [Security Features](./SECURITY.md) — Authentication, authorization, and security best practices
2. [Multi-Tenant RLS](./RLS_SETUP.md) — Row-Level Security setup
3. [API Reference](./API_REFERENCE.md) — Complete endpoint documentation
4. [Docker Guide](./DOCKER.md) — Docker configuration and troubleshooting
5. [Deployment](./DEPLOYMENT.md) — Production deployment guide
