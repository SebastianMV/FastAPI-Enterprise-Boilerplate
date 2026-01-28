# Makefile - Usage Instructions

##  Windows

The `Makefile` is designed for Unix systems (Linux/macOS) and requires the `make` tool which **is NOT natively available on Windows**.

###  Option 1: PowerShell Script (Recommended)

We've created `make.ps1` with equivalent commands for Windows:

```powershell
# 1. Load the script (dot-sourcing)
. .\make.ps1

# 2. View available commands
Show-Help

# 3. Use functions
Start-DevEnvironment      # Equivalent to: make docker-dev
Run-AllTests              # Equivalent to: make test
Run-Migrations            # Equivalent to: make migrate
```

#### Common Commands

| Makefile (Unix) | PowerShell (Windows) | Description |
| --------------- | -------------------- | ----------- |
| `make docker-dev` | `Start-DevEnvironment` | Start development |
| `make test` | `Run-AllTests` | Run tests |
| `make migrate` | `Run-Migrations` | Apply migrations |
| `make lint` | `Run-Lint` | Linting |
| `make clean` | `Clean-Artifacts` | Clean artifacts |

### Option 2: Install `make` on Windows

**With Chocolatey:**

```powershell
choco install make
```

**With Scoop:**

```powershell
scoop install make
```

**With WSL (Windows Subsystem for Linux):**

```bash
# Use Ubuntu/Debian in WSL
wsl
make help
```

##  Linux /  macOS

The Makefile works natively:

```bash
# View available commands
make help

# Start development
make docker-dev

# Run tests
make test

# Apply migrations
make migrate
```

##  Main Commands

### Docker Development

```bash
make docker-dev              # Start dev environment
make docker-dev-build        # Rebuild and start
make docker-down             # Stop services
make docker-logs             # View logs
make docker-clean            # Clean volumes
```

### Docker Production

```bash
make docker-prod             # Start production
make docker-prod-build       # Rebuild production
make docker-prod-down        # Stop production
```

### Testing

```bash
make test                    # Complete tests with coverage
make test-unit               # Unit tests only
make test-integration        # Integration tests only
make test-frontend           # Frontend tests
```

### Code Quality

```bash
make lint                    # Linting (ruff + eslint)
make format                  # Format code
make type-check              # Type checking (mypy)
make check                   # All checks
```

### Database

```bash
make migrate                 # Apply migrations
make migrate-create msg="name"  # Create migration
make migrate-down            # Revert 1 migration
make seed                    # Seed database
```

### CLI

```bash
make create-superuser        # Create superuser
make create-apikey           # Create API key
make health                  # Health check
```

### Cleanup

```bash
make clean                   # Clean build artifacts
```

##  Direct Commands (without Makefile)

If you prefer not to use Makefile/script, you can run commands directly:

### Docker

```bash
docker compose up -d                              # Start dev
docker compose -f docker-compose.prod.yml up -d   # Start prod
docker compose down                               # Stop
```

### Backend

```bash
cd backend
pip install -e ".[dev]"                           # Install
uvicorn app.main:app --reload --port 8000         # Run
pytest tests/ -v --cov=app                        # Tests
alembic upgrade head                              # Migrations
```

### Frontend

```bash
cd frontend
npm install                                       # Install
npm run dev                                       # Run
npm test                                          # Tests
npm run build                                     # Production build
```

##  Environment Configuration

Before running commands, make sure to configure environment variables:

```bash
# Copy example
cp .env.example .env

# Edit with your values
# - JWT_SECRET_KEY (minimum 32 characters)
# - DATABASE_URL (app_user for production)
# - REDIS_PASSWORD (production)
```

##  Troubleshooting

### "make: command not found" (Windows)

- Use `make.ps1` (PowerShell script)
- Install make with Chocolatey/Scoop
- Use WSL (Linux subsystem)

### "docker compose: command not found"

- Install Docker Desktop
- Verify Docker is in PATH

### "Permission denied" (Linux/macOS)

```bash
chmod +x scripts/*.sh
```

### "alembic: No module named 'alembic'"

```bash
cd backend
pip install -e ".[dev]"
```

##  More Information

- [GETTING_STARTED.md](docs/GETTING_STARTED.md) - Getting started guide
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production deployment
- [DOCKER.md](docs/DOCKER.md) - Docker documentation
