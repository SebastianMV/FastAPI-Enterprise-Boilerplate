# ==============================================================================
# FastAPI Enterprise Boilerplate - PowerShell Scripts (Windows)
# ==============================================================================
# 
# Este archivo contiene comandos equivalentes al Makefile para Windows/PowerShell
# Copia y pega los comandos que necesites en tu terminal PowerShell
#
# ==============================================================================

# ------------------------------------------------------------------------------
# 🐳 DOCKER - DEVELOPMENT
# ------------------------------------------------------------------------------

# Iniciar ambiente de desarrollo
function Start-DevEnvironment {
    docker compose up -d
}

# Rebuild y iniciar
function Start-DevEnvironmentBuild {
    docker compose up -d --build
}

# Detener servicios
function Stop-DockerServices {
    docker compose down
}

# Ver logs
function Show-DockerLogs {
    docker compose logs -f
}

# Limpiar (detener y eliminar volúmenes)
function Clear-Docker {
    docker compose down -v
}

# ------------------------------------------------------------------------------
# 🚀 DOCKER - PRODUCTION
# ------------------------------------------------------------------------------

# Iniciar producción
function Start-Production {
    docker compose -f docker-compose.prod.yml up -d
}

# Rebuild producción
function Start-ProductionBuild {
    docker compose -f docker-compose.prod.yml up -d --build
}

# Detener producción
function Stop-Production {
    docker compose -f docker-compose.prod.yml down
}

# ------------------------------------------------------------------------------
# 💻 LOCAL DEVELOPMENT
# ------------------------------------------------------------------------------

# Instalar dependencias
function Install-Dependencies {
    Write-Host "📦 Instalando backend..." -ForegroundColor Cyan
    Set-Location backend
    pip install -e ".[dev]"
    Set-Location ..
    
    Write-Host "📦 Instalando frontend..." -ForegroundColor Cyan
    Set-Location frontend
    npm install
    Set-Location ..
    
    Write-Host "✅ Dependencias instaladas" -ForegroundColor Green
}

# Desarrollo backend
function Start-Backend {
    Set-Location backend
    uvicorn app.main:app --reload --port 8000
}

# Desarrollo frontend
function Start-Frontend {
    Set-Location frontend
    npm run dev
}

# ------------------------------------------------------------------------------
# 🧪 TESTING
# ------------------------------------------------------------------------------

# Iniciar PostgreSQL para testing
function Start-TestDatabase {
    Write-Host "🗄️  Iniciando PostgreSQL de testing..." -ForegroundColor Cyan
    docker compose -f docker-compose.test.yml up -d
    Write-Host "✅ PostgreSQL de testing iniciado en puerto 5433" -ForegroundColor Green
    Write-Host "📝 Usa: `$env:TEST_DATABASE_URL='postgresql+asyncpg://test_user:test_password@localhost:5433/test_boilerplate'" -ForegroundColor Yellow
}

# Detener PostgreSQL de testing
function Stop-TestDatabase {
    Write-Host "🛑 Deteniendo PostgreSQL de testing..." -ForegroundColor Cyan
    docker compose -f docker-compose.test.yml down
}

# Tests completos (SQLite)
function Invoke-AllTests {
    Set-Location backend
    python -m pytest tests/ -v --cov=app
    Set-Location ..
}

# Tests unitarios (SQLite)
function Invoke-UnitTests {
    Set-Location backend
    python -m pytest tests/unit/ -v
    Set-Location ..
}

# Tests integración con PostgreSQL
function Invoke-IntegrationTests {
    Write-Host "🗄️  Ejecutando tests de integración con PostgreSQL..." -ForegroundColor Cyan
    Set-Location backend
    $env:TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/test_boilerplate"
    python -m pytest tests/integration/ -v
    Remove-Item env:TEST_DATABASE_URL
    Set-Location ..
}

# Tests integración con coverage
function Invoke-IntegrationTestsCoverage {
    Write-Host "🗄️  Ejecutando tests de integración con coverage..." -ForegroundColor Cyan
    Set-Location backend
    $env:TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/test_boilerplate"
    coverage run --source=app -m pytest tests/integration/ -v
    coverage report
    Remove-Item env:TEST_DATABASE_URL
    Set-Location ..
}

# Tests frontend
function Invoke-FrontendTests {
    Set-Location frontend
    npm test
    Set-Location ..
}

# ------------------------------------------------------------------------------
# 🔍 CODE QUALITY
# ------------------------------------------------------------------------------

# Linting
function Invoke-Lint {
    Write-Host "🔍 Linting backend..." -ForegroundColor Cyan
    Set-Location backend
    ruff check .
    Set-Location ..
    
    Write-Host "🔍 Linting frontend..." -ForegroundColor Cyan
    Set-Location frontend
    npm run lint
    Set-Location ..
}

# Format code
function Format-Code {
    Write-Host "✨ Formateando backend..." -ForegroundColor Cyan
    Set-Location backend
    ruff format .
    Set-Location ..
    
    Write-Host "✨ Formateando frontend..." -ForegroundColor Cyan
    Set-Location frontend
    npm run format
    Set-Location ..
}

# Type check
function Invoke-TypeCheck {
    Set-Location backend
    mypy app
    Set-Location ..
}

# Check completo
function Invoke-AllChecks {
    Invoke-Lint
    Invoke-TypeCheck
    Invoke-AllTests
    Write-Host "✅ Todos los checks pasaron!" -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 🗄️ DATABASE
# ------------------------------------------------------------------------------

# Migraciones (upgrade)
function Invoke-Migrations {
    docker compose exec backend alembic upgrade head
}

# Crear migración
function New-Migration {
    param([string]$Message)
    docker compose exec backend alembic revision --autogenerate -m "$Message"
}

# Downgrade migración
function Undo-Migration {
    docker compose exec backend alembic downgrade -1
}

# Seed database
function Initialize-Database {
    docker compose exec backend python -m app.cli.main db seed
}

# Cleanup E2E test users
function Cleanup-E2EUsers {
    docker compose exec backend python cleanup_e2e_users.py
}

# ------------------------------------------------------------------------------
# 👤 CLI COMMANDS
# ------------------------------------------------------------------------------

# Crear superusuario
function New-Superuser {
    docker compose exec backend python -m app.cli.main users create-superuser
}

# Crear API key
function New-ApiKey {
    Set-Location backend
    python -m app.cli.main apikeys create
    Set-Location ..
}

# Health check
function Test-Health {
    Set-Location backend
    python -m app.cli.main health
    Set-Location ..
}

# ------------------------------------------------------------------------------
# 🧹 CLEANUP
# ------------------------------------------------------------------------------

# Limpiar artefactos
function Clear-Artifacts {
    Write-Host "🧹 Limpiando artefactos..." -ForegroundColor Cyan
    
    # Python
    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter ".mypy_cache" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter ".ruff_cache" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter "htmlcov" | Remove-Item -Recurse -Force
    
    # Frontend
    Get-ChildItem -Path . -Recurse -Directory -Filter "node_modules" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -Directory -Filter "dist" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    
    # Coverage
    if (Test-Path "backend\.coverage") { Remove-Item "backend\.coverage" -Force }
    if (Test-Path "frontend\coverage") { Remove-Item "frontend\coverage" -Recurse -Force }
    
    Write-Host "✅ Limpieza completa" -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 📚 HELP
# ------------------------------------------------------------------------------

function Show-Help {
    Write-Host ""
    Write-Host "FastAPI Enterprise Boilerplate - Comandos PowerShell" -ForegroundColor Green
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "🐳 Docker - Development:" -ForegroundColor Cyan
    Write-Host "  Start-DevEnvironment         Iniciar ambiente dev"
    Write-Host "  Start-DevEnvironmentBuild    Rebuild e iniciar dev"
    Write-Host "  Stop-DockerServices          Detener servicios"
    Write-Host "  Show-DockerLogs              Ver logs"
    Write-Host "  Clean-Docker                 Limpiar volúmenes"
    Write-Host ""
    Write-Host "🚀 Docker - Production:" -ForegroundColor Cyan
    Write-Host "  Start-Production             Iniciar producción"
    Write-Host "  Start-ProductionBuild        Rebuild producción"
    Write-Host "  Stop-Production              Detener producción"
    Write-Host ""
    Write-Host "💻 Local Development:" -ForegroundColor Cyan
    Write-Host "  Install-Dependencies         Instalar dependencias"
    Write-Host "  Start-Backend                Ejecutar backend"
    Write-Host "  Start-Frontend               Ejecutar frontend"
    Write-Host ""
    Write-Host "🧪 Testing:" -ForegroundColor Cyan
    Write-Host "  Run-AllTests                 Tests completos"
    Write-Host "  Run-UnitTests                Tests unitarios"
    Write-Host "  Run-IntegrationTests         Tests integración"
    Write-Host "  Run-FrontendTests            Tests frontend"
    Write-Host ""
    Write-Host "🔍 Code Quality:" -ForegroundColor Cyan
    Write-Host "  Run-Lint                     Linting"
    Write-Host "  Format-Code                  Formatear código"
    Write-Host "  Run-TypeCheck                Type checking"
    Write-Host "  Run-AllChecks                Todos los checks"
    Write-Host ""
    Write-Host "🗄️ Database:" -ForegroundColor Cyan
    Write-Host "  Run-Migrations               Aplicar migraciones"
    Write-Host "  New-Migration -Message '...' Crear migración"
    Write-Host "  Rollback-Migration           Revertir migración"
    Write-Host "  Seed-Database                Seed data"
    Write-Host "  Cleanup-E2EUsers             Eliminar usuarios E2E"
    Write-Host ""
    Write-Host "👤 CLI:" -ForegroundColor Cyan
    Write-Host "  New-Superuser                Crear superusuario"
    Write-Host "  New-ApiKey                   Crear API key"
    Write-Host "  Test-Health                  Health check"
    Write-Host ""
    Write-Host "🧹 Cleanup:" -ForegroundColor Cyan
    Write-Host "  Clear-Artifacts              Limpiar artefactos"
    Write-Host ""
    Write-Host "Para usar: dot-source este archivo primero:" -ForegroundColor Yellow
    Write-Host "  . .\make.ps1" -ForegroundColor Yellow
    Write-Host "  Show-Help" -ForegroundColor Yellow
    Write-Host ""
}

# Mostrar help al cargar el script
Show-Help
