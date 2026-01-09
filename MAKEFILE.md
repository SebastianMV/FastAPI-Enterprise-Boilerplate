# Makefile - Instrucciones de Uso

## 🪟 Windows

El `Makefile` está diseñado para sistemas Unix (Linux/macOS) y requiere la herramienta `make` que **NO está disponible nativamente en Windows**.

### ✅ Opción 1: Script PowerShell (Recomendado)

Hemos creado `make.ps1` con comandos equivalentes para Windows:

```powershell
# 1. Cargar el script (dot-sourcing)
. .\make.ps1

# 2. Ver comandos disponibles
Show-Help

# 3. Usar funciones
Start-DevEnvironment      # Igual a: make docker-dev
Run-AllTests              # Igual a: make test
Run-Migrations            # Igual a: make migrate
```

#### Comandos Comunes

| Makefile (Unix) | PowerShell (Windows) | Descripción |
| --------------- | -------------------- | ----------- |
| `make docker-dev` | `Start-DevEnvironment` | Iniciar desarrollo |
| `make test` | `Run-AllTests` | Ejecutar tests |
| `make migrate` | `Run-Migrations` | Aplicar migraciones |
| `make lint` | `Run-Lint` | Linting |
| `make clean` | `Clean-Artifacts` | Limpiar artefactos |

### Opción 2: Instalar `make` en Windows

**Con Chocolatey:**

```powershell
choco install make
```

**Con Scoop:**

```powershell
scoop install make
```

**Con WSL (Windows Subsystem for Linux):**

```bash
# Usar Ubuntu/Debian en WSL
wsl
make help
```

## 🐧 Linux / 🍎 macOS

El Makefile funciona nativamente:

```bash
# Ver comandos disponibles
make help

# Iniciar desarrollo
make docker-dev

# Ejecutar tests
make test

# Aplicar migraciones
make migrate
```

## 📋 Comandos Principales

### Docker Development

```bash
make docker-dev              # Iniciar ambiente dev
make docker-dev-build        # Rebuild e iniciar
make docker-down             # Detener servicios
make docker-logs             # Ver logs
make docker-clean            # Limpiar volúmenes
```

### Docker Production

```bash
make docker-prod             # Iniciar producción
make docker-prod-build       # Rebuild producción
make docker-prod-down        # Detener producción
```

### Testing

```bash
make test                    # Tests completos con cobertura
make test-unit               # Solo tests unitarios
make test-integration        # Solo tests integración
make test-frontend           # Tests frontend
```

### Code Quality

```bash
make lint                    # Linting (ruff + eslint)
make format                  # Formatear código
make type-check              # Type checking (mypy)
make check                   # Todos los checks
```

### Database

```bash
make migrate                 # Aplicar migraciones
make migrate-create msg="nombre"  # Crear migración
make migrate-down            # Revertir 1 migración
make seed                    # Seed database
```

### CLI

```bash
make create-superuser        # Crear superusuario
make create-apikey           # Crear API key
make health                  # Health check
```

### Cleanup

```bash
make clean                   # Limpiar artefactos build
```

## 🔧 Comandos Directos (sin Makefile)

Si prefieres no usar Makefile/script, puedes ejecutar comandos directamente:

### Docker

```bash
docker compose up -d                              # Iniciar dev
docker compose -f docker-compose.prod.yml up -d   # Iniciar prod
docker compose down                               # Detener
```

### Backend

```bash
cd backend
pip install -e ".[dev]"                           # Instalar
uvicorn app.main:app --reload --port 8000         # Ejecutar
pytest tests/ -v --cov=app                        # Tests
alembic upgrade head                              # Migraciones
```

### Frontend

```bash
cd frontend
npm install                                       # Instalar
npm run dev                                       # Ejecutar
npm test                                          # Tests
npm run build                                     # Build producción
```

## ⚙️ Configuración de Entorno

Antes de ejecutar comandos, asegúrate de tener configuradas las variables de entorno:

```bash
# Copiar ejemplo
cp .env.example .env

# Editar con tus valores
# - JWT_SECRET_KEY (mínimo 32 caracteres)
# - DATABASE_URL (app_user en producción)
# - REDIS_PASSWORD (producción)
```

## 🆘 Troubleshooting

### "make: command not found" (Windows)

- Usar `make.ps1` (PowerShell script)
- Instalar make con Chocolatey/Scoop
- Usar WSL (Linux subsystem)

### "docker compose: command not found"

- Instalar Docker Desktop
- Verificar que Docker está en PATH

### "Permission denied" (Linux/macOS)

```bash
chmod +x scripts/*.sh
```

### "alembic: No module named 'alembic'"

```bash
cd backend
pip install -e ".[dev]"
```

## 📚 Más Información

- [GETTING_STARTED.md](docs/GETTING_STARTED.md) - Guía de inicio
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment en producción
- [DOCKER.md](docs/DOCKER.md) - Documentación Docker
