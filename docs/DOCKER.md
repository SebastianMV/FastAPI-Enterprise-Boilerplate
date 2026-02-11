# 🐳 Docker Guide

Complete guide for running FastAPI Enterprise Boilerplate with Docker.

## Table of Contents

- [Quick Start](#quick-start)
- [Development vs Production](#development-vs-production)
- [Docker Compose Files](#docker-compose-files)
- [Dockerfiles](#dockerfiles)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

For quick start commands, see [README.md](../README.md#quick-start) or [GETTING_STARTED.md](./GETTING_STARTED.md).

Below you'll find detailed Docker configuration and troubleshooting information.

---

## Development vs Production

| Feature | Development | Production |
| ------- | ----------- | ---------- |
| **Compose File** | `docker-compose.yml` | `docker-compose.prod.yml` |
| **Backend Dockerfile** | `Dockerfile` | `Dockerfile.prod` |
| **Frontend Dockerfile** | `Dockerfile.dev` | `Dockerfile` |
| **Backend Server** | Uvicorn (1 worker, reload) | Uvicorn (4 workers) |
| **Frontend Server** | Vite dev server | Nginx |
| **Hot-Reload** | ✅ Yes | ❌ No |
| **Volume Mounting** | ✅ Yes | ❌ No |
| **Ports** | Backend: 8000, Frontend: 3000 | Backend: 8000, Frontend: 80 |
| **Build Time** | Fast (uses cache) | Slower (optimized) |
| **Image Size** | Larger | Smaller (multi-stage) |
| **Security** | Standard | Enhanced (non-root, limits) |

---

## Docker Compose Files

### `docker-compose.yml` (Development)

**Purpose:** Local development with hot-reload and debugging.

**Features:**

- Volume mounting for live code changes
- Backend: Uvicorn with `--reload` flag
- Frontend: Vite dev server (port 3000)
- Debug mode enabled
- Development environment variables

**Services:**

```yaml
services:
  backend:    # FastAPI with auto-reload
  frontend:   # Vite dev server
  db:         # PostgreSQL 17
  redis:      # Redis 7
  jaeger:     # Optional observability
```

### `docker-compose.prod.yml` (Production)

**Purpose:** Production deployment with optimizations.

**Features:**

- Multi-stage builds for smaller images
- Backend: Uvicorn with 4 workers
- Frontend: Nginx serving static files (port 80)
- Resource limits configured
- Health checks enabled
- Restart policies
- Non-root users

**Additional Configuration:**

- Named containers
- Custom networks
- Resource limits (CPU, memory)
- Health checks for all services

---

## Dockerfiles

### Backend

#### `backend/Dockerfile` (Development)

```dockerfile
# Single-stage build
# Installs all dependencies including dev tools
# Used with volume mounting
```

**Characteristics:**

- Base: `python:3.13-slim`
- Installs: All dependencies from `requirements.txt`
- Command: `uvicorn app.main:app --reload`
- Size: ~500MB

#### `backend/Dockerfile.prod` (Production)

```dockerfile
# Multi-stage build
# Stage 1: Builder (installs dependencies)
# Stage 2: Runtime (copies only needed files)
```

**Characteristics:**

- Base: `python:3.13-slim`
- Multi-stage: Builder + Runtime
- Non-root user: `appuser`
- Cleanup: Removes tests, cache, docs
- Size: ~300MB
- Workers: 4

### Frontend

#### `frontend/Dockerfile.dev` (Development)

```dockerfile
# Vite dev server with hot-reload
FROM node:22-alpine
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

**Characteristics:**

- Base: `node:22-alpine`
- Server: Vite dev server
- Port: 3000 (configurable in vite.config.ts)
- Hot-reload: ✅ Enabled
- Size: ~200MB

#### `frontend/Dockerfile` (Production)

```dockerfile
# Multi-stage build
# Stage 1: Dependencies
# Stage 2: Builder (npm run build)
# Stage 3: Nginx serving static files
```

**Characteristics:**

- Base: `node:22-alpine` → `nginx:1.28-alpine`
- Multi-stage: Dependencies → Builder → Nginx
- Output: Optimized static files in `/usr/share/nginx/html`
- Size: ~25MB
- Features: Gzip, caching headers, API proxy

---

## Common Tasks

### Development

```bash
# Start services
docker compose up -d

# Rebuild specific service
docker compose up -d --build backend

# View logs (follow)
docker compose logs -f backend

# Execute commands in container
docker compose exec backend python -m pytest
docker compose exec backend alembic upgrade head
docker compose exec frontend npm run lint

# Open shell in container
docker compose exec backend bash
docker compose exec frontend sh

# Restart service
docker compose restart backend

# Stop all services
docker compose down

# Stop and remove volumes (clean state)
docker compose down -v
```

### Production Tasks

```bash
# Build and start
docker compose -f docker-compose.prod.yml up -d --build

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Check health
docker compose -f docker-compose.prod.yml ps

# Scale backend (multiple workers)
docker compose -f docker-compose.prod.yml up -d --scale backend=3

# Update single service
docker compose -f docker-compose.prod.yml up -d --build frontend

# Stop all
docker compose -f docker-compose.prod.yml down
```

### Database Migrations

```bash
# Run migrations
docker compose exec backend alembic upgrade head

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Rollback migration
docker compose exec backend alembic downgrade -1

# Check current version
docker compose exec backend alembic current
```

### Testing

```bash
# Run all tests
docker compose exec backend python -m pytest

# Run with coverage
docker compose exec backend python -m pytest --cov=app --cov-report=term

# Run specific test file
docker compose exec backend python -m pytest tests/unit/test_auth.py

# Frontend tests
docker compose exec frontend npm run test
```

---

## Environment Variables

### Required for Production

Create a `.env` file in the project root:

```bash
# Production secrets (CHANGE THESE!)
JWT_SECRET_KEY=<STRONG-SECRET-KEY-HERE-MIN-32-CHARS>
POSTGRES_PASSWORD=<STRONG-DB-PASSWORD>

# Database (production)
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/dbname

# Redis (production)
REDIS_URL=redis://redis:6379/0

# Environment
ENVIRONMENT=production
DEBUG=false
```

### Development Defaults

Development uses defaults from `docker-compose.yml`:

```yaml
JWT_SECRET_KEY: "change-this-in-production-with-strong-secret-key-min-32-chars"
DATABASE_URL: "postgresql+asyncpg://boilerplate:boilerplate@db:5432/boilerplate"
REDIS_URL: "redis://redis:6379/0"
```

---

## Troubleshooting

### Frontend not loading

**Symptom:** Curl returns "Empty reply from server" or connection refused.

**Solution:**

```bash
# Check if container is running
docker compose ps

# Check logs
docker compose logs frontend

# Verify port mapping
docker compose ps frontend
# Should show: 0.0.0.0:3000->3000/tcp (dev) or 0.0.0.0:80->80/tcp (prod)

# Rebuild frontend
docker compose up -d --build frontend
```

### Backend errors

**Symptom:** 500 errors or connection issues.

**Solution:**

```bash
# Check logs
docker compose logs backend

# Verify database connection
docker compose exec backend python -c "from app.infrastructure.database import engine; print('DB OK')"

# Run migrations
docker compose exec backend alembic upgrade head

# Restart backend
docker compose restart backend
```

### Database connection refused

**Symptom:** `could not connect to server: Connection refused`.

**Solution:**

```bash
# Check if DB is running
docker compose ps db

# Check DB health
docker compose exec db pg_isready -U boilerplate

# View DB logs
docker compose logs db

# Restart DB (will lose data without volumes)
docker compose restart db
```

### Port already in use

**Symptom:** `Error: port is already allocated`.

**Solution:**

```bash
# Find process using port 8000
# Linux/Mac:
lsof -i :8000

# Windows:
netstat -ano | findstr :8000

# Kill process or change port in docker-compose.yml
# Example: Change "8000:8000" to "8001:8000"
```

### Volumes not updating

**Symptom:** Code changes not reflected in container.

**Solution:**

```bash
# Restart service
docker compose restart backend

# Or rebuild without cache
docker compose up -d --build --force-recreate backend

# Check volume mounts
docker compose config
```

### Clean restart

**When nothing works:**

```bash
# Stop everything
docker compose down -v

# Remove images (optional)
docker compose down --rmi all -v

# Rebuild from scratch
docker compose up -d --build
```

---

## Best Practices

### Development Best Practices

1. **Use hot-reload:** `docker compose up -d` gives you instant feedback
2. **Volume mounting:** Your local changes appear immediately in containers
3. **Separate terminals:** One for logs (`docker compose logs -f`), one for commands
4. **Clean state:** Use `docker compose down -v` when switching branches

### Production Best Practices

1. **Use .env file:** Never commit secrets to git
2. **Health checks:** Ensure all services have health checks
3. **Resource limits:** Set appropriate CPU and memory limits
4. **Logging:** Configure structured logging for monitoring
5. **Backups:** Regular database backups (`pg_dump`)

### Security

1. **Non-root users:** All production containers run as non-root
2. **Strong secrets:** Generate strong JWT keys (`openssl rand -hex 32`)
3. **Network isolation:** Use Docker networks to isolate services
4. **Regular updates:** Keep base images updated

---

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [Nginx Docker](https://hub.docker.com/_/nginx)
