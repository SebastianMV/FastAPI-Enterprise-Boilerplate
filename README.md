<p align="center">
  <img src="docs/assets/logo.svg" alt="FastAPI Enterprise Boilerplate Logo" width="200" height="200">
</p>

<h1 align="center">FastAPI Enterprise Boilerplate</h1>

<p align="center">
  <strong>Full-Stack Enterprise Boilerplate — FastAPI + React 19 + PostgreSQL 17 + Redis. Enterprise boilerplate with JWT auth, granular ACL, multi-tenant RLS, and hexagonal architecture.</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.14+-blue.svg" alt="Python 3.14+"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-green.svg" alt="FastAPI"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React"></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/Node.js-22%20LTS-339933?logo=node.js&logoColor=white" alt="Node.js"></a>
  <a href="https://www.apache.org/licenses/LICENSE-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License: Apache 2.0"></a>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/backend%20tests-3500%2B%20passing-brightgreen.svg" alt="Backend Tests"></a>
  <a href="#"><img src="https://img.shields.io/badge/backend%20coverage-99%25-brightgreen.svg" alt="Backend Coverage"></a>
  <a href="#"><img src="https://img.shields.io/badge/frontend%20tests-598%20passing-brightgreen.svg" alt="Frontend Tests"></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker"></a>
  <a href="#"><img src="https://img.shields.io/badge/security%20audits-43%20cycles-brightgreen.svg" alt="Security Audits"></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/status-stable-brightgreen.svg" alt="Stable"></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/version-1.0.0-blue.svg" alt="v1.0.0"></a>
</p>

---

## ⚡ Quick Start

### 🐳 Docker (Recommended)

**Development** (with hot-reload):

```bash
# Clone repository
git clone https://github.com/SebastianMV/FastAPI-Enterprise-Boilerplate.git
cd FastAPI-Enterprise-Boilerplate

# Copy environment variables
cp .env.example .env

# Start all services
docker compose up -d

# Access:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Frontend: http://localhost:3000 (with hot-reload)
```

> **👨‍💻 Windows Users:** Usa PowerShell con `make.ps1` para comandos de desarrollo:
>
> ```powershell
> # Cargar funciones
> . .\make.ps1
>
> # Iniciar desarrollo
> Start-DevEnvironment
>
> # Ver todos los comandos
> Show-Help
> ```
>
> Ver todos los comandos con `Show-Help` o `make help`

**Comandos útiles** (Linux/Mac con Makefile, Windows con make.ps1):

```bash
# Ver todos los comandos disponibles
make help                # Linux/Mac
Show-Help                # Windows (PowerShell)

# Ejecutar tests
make test                # Linux/Mac
Invoke-AllTests          # Windows (PowerShell)

# Ver logs
make docker-logs         # Linux/Mac
Show-DockerLogs          # Windows (PowerShell)

# Limpiar contenedores
make docker-clean        # Linux/Mac
Clear-Docker             # Windows (PowerShell)
```

**Production**:

```bash
# Build and start production containers
docker compose -f docker-compose.deploy.yml up -d --build

# Access:
# - API: http://localhost:8000
# - Frontend: http://localhost:80
```

### 💻 Local Development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### 🚀 Próximos Pasos

Después de iniciar el proyecto **por primera vez**:

#### Inicialización Automática

Las migraciones de base de datos se ejecutan automáticamente al iniciar, creando:

- ✅ **Tenant por defecto**: "Default Organization"
- ✅ **3 Usuarios de desarrollo** (ver tabla abajo)
- ✅ **Roles ACL**: superadmin, admin, user
- ✅ **Permisos configurados** para cada rol

> **Nota**: Los datos se crean mediante migraciones de Alembic. Es idempotente y seguro.

#### Primeros Pasos

1. **Verifica que los servicios estén corriendo**:

   ```bash
   docker compose ps
   # Deberías ver: backend, frontend, db, redis (todos healthy/running)
   ```

2. **Accede a la API Docs**: <http://localhost:8000/docs>
   - Login con cualquier usuario de la tabla
   - Explora los endpoints disponibles

3. **Accede al Frontend**: <http://localhost:3000>
   - Login con las credenciales de desarrollo
   - Dashboard con datos en tiempo real

4. **Registra nuevos usuarios**: <http://localhost:3000/register>
   - Los nuevos usuarios tendrán rol "user" por defecto

5. **Explora la documentación**: Lee [docs/README.md](docs/README.md) para el índice completo

6. **Ejecuta los tests**:

   ```bash
   make test              # Linux/Mac
   Invoke-AllTests           # Windows PowerShell
   ```

#### Credenciales de Desarrollo

| Usuario              | Email                 | Password      | Rol        |
| -------------------- | --------------------- | ------------- | ---------- |
| System Administrator | `admin@example.com`   | `Admin123!`   | superadmin |
| Tenant Manager       | `manager@example.com` | `Manager123!` | admin      |
| Demo User            | `user@example.com`    | `User123!`    | user       |

> ⚠️ **IMPORTANTE**: Estos usuarios son solo para desarrollo. Elimínalos antes de desplegar a producción.
> 📖 **Documentación completa**: Comienza con [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)

## 🎯 Features

### Core

- ✅ **Hexagonal Architecture** - Clean separation of concerns
- ✅ **JWT + Refresh Tokens** - Secure stateless authentication
- ✅ **MFA/2FA (TOTP)** - Two-factor authentication with backup codes
- ✅ **Account Lockout** - Protection against brute-force attacks
- ✅ **Session Management** - View and revoke active sessions
- ✅ **Email Verification** - Validate user email addresses
- ✅ **Granular ACL** - Permission-based access control
- ✅ **Multi-Tenant (RLS)** - PostgreSQL Row Level Security
- ✅ **SQLAlchemy 2.0 Async** - High-performance database operations

### Real-Time Features

- ✅ **WebSocket Support** - Real-time bidirectional communication
- ✅ **Real-time Notifications** - Instant delivery via WebSocket
- ✅ **Pluggable Backend** - Memory (dev) / Redis Pub/Sub (production)

> **💡 Note:** WebSocket is enabled by default for **notifications**. See [docs/WEBSOCKET.md](docs/WEBSOCKET.md) for details.

### Infrastructure

- ✅ **OpenTelemetry** - Traces, metrics, structured logs
- ✅ **Audit Logging** - Complete action trail for compliance
- ✅ **i18n Support (100%)** - Multi-language with lazy loading ([EN/ES/PT](docs/I18N.md))
- ✅ **Health Checks** - Kubernetes liveness/readiness probes
- ✅ **Rate Limiting** - Redis-based API protection
- ✅ **Background Jobs** - Async task processing with retry

### Developer Experience

- ✅ **CLI Tools** - `create-superuser`, `seed-db`, `generate-api-key` (manual admin tools)

> 🚨 **Production Security**: Development users with known passwords are created automatically by migrations for testing. [**Delete them before production deployment!**](docs/DEPLOYMENT.md#production-security--initial-setup)

- ✅ **4000+ Tests Passing** - 99% backend coverage (smoke gate), 598 frontend tests (72% stmt coverage, threshold 30%)
- ✅ **E2E Validated** - Login flow + WebSocket tested (20/84 E2E passing, 63 skipped pending full environment)
- ✅ **Docker Compose** - One-command dev environment
- ✅ **Auto-generated Docs** - OpenAPI with examples
- ✅ **Windows Compatible** - PowerShell scripts included (make.ps1)

### Frontend

- ✅ **React 19** - Latest React with TypeScript
- ✅ **Node.js 22 LTS** - Long-term support (until Oct 2027)
- ✅ **Vite 6** - Next-generation build tool
- ✅ **Tailwind CSS** - Utility-first styling
- ✅ **React Query** - Server state management
- ✅ **React Router v6** - Client-side routing
- ✅ **Zustand** - Client state management
- ✅ **i18n (react-i18next)** - Multi-language support (100% coverage, lazy loading)

### Frontend Pages

**Authentication & Security:**

- ✅ **Login/Logout** - JWT authentication flow
- ✅ **User Registration** - `/register` with validation
- ✅ **Password Recovery** - Forgot/Reset password flow
- ✅ **Email Verification** - Verify email with banner and resend
- ✅ **OAuth/SSO Callback** - External provider authentication

**User Management:**

- ✅ **Profile Settings** - View and edit user info + avatar upload
- ✅ **Users Management** - CRUD operations (admin)
- ✅ **Roles Management** - Permissions and role assignment (admin)
- ✅ **Sessions Management** - View and revoke active sessions

**Security & API:**

- ✅ **API Keys Management** - Create, view, revoke keys with scopes
- ✅ **MFA Configuration** - Enable/disable 2FA with TOTP and backup codes

**Operations:**

- ✅ **Dashboard** - Real-time metrics and system health
- ✅ **Audit Log Viewer** - Filter and search security events
- ✅ **Notifications Center** - Real-time WebSocket notifications
- ✅ **Search** - Full-text search across resources
- ✅ **Tenant Management** - Multi-tenant administration (superadmin)

> **🌍 i18n:** All pages are fully translated to 3 languages (EN/ES/PT). See [docs/I18N.md](docs/I18N.md) for details.

## 📁 Project Structure

```text
├── backend/
│   ├── app/
│   │   ├── api/              # HTTP layer (thin controllers)
│   │   ├── domain/           # Business logic (pure Python)
│   │   ├── application/      # Use cases & services
│   │   └── infrastructure/   # External adapters (DB, auth, cache)
│   ├── tests/
│   └── alembic/              # Database migrations
├── frontend/
│   └── src/
├── docs/
└── docker-compose.yml
```

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                           │
│  (FastAPI endpoints, middleware, request/response schemas)  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Application Layer                         │
│         (Use cases, services, business orchestration)        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                      Domain Layer                            │
│    (Entities, value objects, business rules - NO deps)       │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  Infrastructure Layer                        │
│   (PostgreSQL, Redis, JWT, Email, Feature Flags, etc.)       │
└─────────────────────────────────────────────────────────────┘
```

## 🔐 Authentication & Authorization

### JWT Flow

```text
1. POST /auth/login → Access Token (15min) + Refresh Token (7d)
2. Request with: Authorization: Bearer {access_token}
3. On expiry: POST /auth/refresh → New Access Token
```

### ACL Example

```python
from app.api.deps import require_permission

@router.get("/users")
@require_permission("users", "read")
async def list_users(current_user: User = Depends(get_current_user)):
    ...

@router.delete("/users/{id}")
@require_permission("users", "delete")
async def delete_user(id: int):
    ...
```

## 🏢 Multi-Tenant (RLS)

Data isolation at database level:

```sql
-- Automatic filtering by tenant
CREATE POLICY tenant_isolation ON users
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

No manual filtering needed in code - PostgreSQL handles it.

## � Pluggable Storage System

The boilerplate includes a **pluggable storage architecture** that works out-of-the-box without requiring external cloud services. This design follows the **Adapter Pattern** from hexagonal architecture.

### How It Works

```text
┌─────────────────────────────────────────────────────────────┐
│                    Your Application Code                    │
│              (uses StoragePort interface only)              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     StoragePort (ABC)                       │
│   upload() │ download() │ delete() │ get_presigned_url()    │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │    Local    │ │   AWS S3    │ │    MinIO    │
   │  (Default)  │ │ (Optional)  │ │ (Optional)  │
   └─────────────┘ └─────────────┘ └─────────────┘
```

### Automatic Fallback

| Configuration                          | Storage Used                            |
| -------------------------------------- | --------------------------------------- |
| Nothing configured                     | ✅ **LocalStorage** (works immediately) |
| `S3_BUCKET` set                        | AWS S3                                  |
| `STORAGE_BACKEND=minio` + MinIO config | MinIO                                   |
| `STORAGE_BACKEND=local`                | Force local storage                     |

### Configuration Examples

```bash
# 1. Default: Local Storage (zero configuration)
# Just works! Files stored in ./storage

# 2. AWS S3
STORAGE_BACKEND=s3
S3_BUCKET=my-app-files
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# 3. MinIO (self-hosted S3-compatible)
STORAGE_BACKEND=minio
MINIO_ENDPOINT=http://minio:9000
MINIO_BUCKET=my-app-files
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Usage in Code

```python
from app.infrastructure.storage import get_storage

# Get the configured storage (auto-selected)
storage = get_storage()

# Upload a file
await storage.upload(file_data, "documents/report.pdf")

# Generate presigned URL (works for all backends!)
url = await storage.get_presigned_url("documents/report.pdf")

# Download
content = await storage.download("documents/report.pdf")
```

### Presigned URLs

All backends support presigned URLs:

- **S3/MinIO**: Native AWS Signature V4
- **LocalStorage**: Simulated signed URLs with expiration tokens

This means your code works identically regardless of the storage backend.

## �🛠️ CLI Commands

```bash
# User management
cli users create-superuser --email admin@example.com
cli users list --active
cli users activate <user-id>

# Database operations
cli db seed --users --roles --tenants
cli db migrate --revision head
cli db info

# API keys
cli apikeys generate --name "CI/CD" --user admin@example.com
cli apikeys list
cli apikeys revoke <key-id>

# Health check
cli health
cli version
```

## 📊 Observability

```python
# Automatic tracing for all requests
# Metrics: request_count, request_latency, db_query_time
# Structured logs with correlation IDs

# Export to:
# - Jaeger/Tempo (traces)
# - Prometheus (metrics)
# - Loki (logs)
```

## 🚀 Deployment

```bash
# Production
docker-compose -f docker-compose.deploy.yml up -d

# Kubernetes
kubectl apply -f k8s/
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete deployment guide.

## 📚 Documentation

Use the centralized documentation index: [docs/README.md](docs/README.md).

Quick links:

- [⭐ Getting Started](docs/GETTING_STARTED.md)
- [� Security](docs/SECURITY.md)
- [📡 API Reference](docs/API_REFERENCE.md)
- [📝 Changelog](CHANGELOG.md)

## 🎯 Project Status

**Version:** v1.0.0 — **Stable Release** — feature-complete, 43 security audit cycles passed (Mar 2026)

> See [CHANGELOG.md](CHANGELOG.md) for release history.

### 📊 Metrics

| Metric            | Value                           | Status |
| ----------------- | ------------------------------- | ------ |
| Backend Tests     | 3,500+ passing                  | ✅     |
| Backend Coverage  | 99%                             | ✅     |
| Frontend Tests    | 598 passing                     | ✅     |
| Frontend Coverage | 72% statements                  | ✅     |
| Backend E2E       | 20/84 passing (63 skipped)      | 🔶     |
| Migrations        | 12 applied                      | ✅     |
| Security Audits   | 43 cycles (992+ items resolved) | ✅     |
| Docker Build      | < 2 minutes                     | ✅     |

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## 📝 License

Apache License 2.0 — See [LICENSE](LICENSE) and [NOTICE](NOTICE) for details.

Contributors must sign the [CLA](CLA.md) before their first PR can be merged.
The CLA grants relicensing rights so the maintainer can adjust licensing in the future if needed.

## 🙏 Credits

Extracted from [KairOS](https://github.com/SebastianMV/kairOS) - Enterprise Attendance Control System.

---

Made with ❤️ for the Python community
