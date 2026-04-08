# ==============================================================================
# FastAPI-Enterprise-Boilerplate - PowerShell Scripts (Windows)
# ==============================================================================
#
# This file contains Makefile-equivalent commands for Windows/PowerShell
# Copy and paste the commands you need into your PowerShell terminal
#
# ==============================================================================

# ------------------------------------------------------------------------------
# 🐳 DOCKER - DEVELOPMENT
# ------------------------------------------------------------------------------

# Start development environment
function Start-DevEnvironment {
    docker compose up -d
}

# Rebuild and start
function Start-DevEnvironmentBuild {
    docker compose up -d --build
}

# Stop services
function Stop-DockerServices {
    docker compose down
}

# View logs
function Show-DockerLogs {
    docker compose logs -f
}

# Clean (stop and remove volumes)
function Clear-Docker {
    docker compose down -v
}

# ------------------------------------------------------------------------------
# 🚀 DOCKER - PRODUCTION
# ------------------------------------------------------------------------------

# Start production
function Start-Production {
    docker compose -f docker-compose.deploy.yml up -d
}

# Rebuild production
function Start-ProductionBuild {
    docker compose -f docker-compose.deploy.yml up -d --build
}

# Stop production
function Stop-Production {
    docker compose -f docker-compose.deploy.yml down
}

# View production logs
function Show-ProductionLogs {
    docker compose -f docker-compose.deploy.yml logs -f
}

# Build production
function New-ProductionBuild {
    docker compose -f docker-compose.deploy.yml build
}

# Deploy production
function Publish-Production {
    docker compose -f docker-compose.deploy.yml up -d
    docker compose -f docker-compose.deploy.yml exec backend alembic upgrade head
}

# ------------------------------------------------------------------------------
# 💻 LOCAL DEVELOPMENT
# ------------------------------------------------------------------------------

# Install dependencies
function Install-Dependencies {
    Write-Host "📦 Installing backend..." -ForegroundColor Cyan
    Set-Location backend
    pip install -e ".[dev]"
    Set-Location ..

    Write-Host "📦 Installing frontend..." -ForegroundColor Cyan
    Set-Location frontend
    npm install
    Set-Location ..

    Write-Host "✅ Dependencies installed" -ForegroundColor Green
}

# Start backend development
function Start-Backend {
    Set-Location backend
    uvicorn app.main:app --reload --port 8000
}

# Start frontend development
function Start-Frontend {
    Set-Location frontend
    npm run dev
}

# ------------------------------------------------------------------------------
# 🧪 TESTING
# ------------------------------------------------------------------------------

# Start PostgreSQL for testing
function Start-TestDatabase {
    Write-Host "🗄️  Starting test PostgreSQL..." -ForegroundColor Cyan
    docker compose -f docker-compose.test.yml up -d
    Write-Host "✅ Test PostgreSQL started on port 5433" -ForegroundColor Green
    Write-Host "📝 Use: `$env:TEST_DATABASE_URL='postgresql+asyncpg://test_user:test_password@localhost:5433/test_boilerplate'" -ForegroundColor Yellow
}

# Stop test PostgreSQL
function Stop-TestDatabase {
    Write-Host "🛑 Stopping test PostgreSQL..." -ForegroundColor Cyan
    docker compose -f docker-compose.test.yml down
}

# Run all tests (SQLite)
function Invoke-AllTests {
    Set-Location backend
    python -m pytest tests/ -v --cov=app
    Set-Location ..
}

# Run unit tests (SQLite)
function Invoke-UnitTests {
    Set-Location backend
    python -m pytest tests/unit/ -v
    Set-Location ..
}

# Run integration tests with PostgreSQL
function Invoke-IntegrationTests {
    Write-Host "🗄️  Running integration tests with PostgreSQL..." -ForegroundColor Cyan
    Set-Location backend
    $env:TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/test_boilerplate"
    python -m pytest tests/integration/ -v
    Remove-Item env:TEST_DATABASE_URL
    Set-Location ..
}

# Run integration tests with coverage
function Invoke-IntegrationTestsCoverage {
    Write-Host "🗄️  Running integration tests with coverage..." -ForegroundColor Cyan
    Set-Location backend
    $env:TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/test_boilerplate"
    coverage run --source=app -m pytest tests/integration/ -v
    coverage report
    Remove-Item env:TEST_DATABASE_URL
    Set-Location ..
}

# Run frontend tests
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
    Write-Host "✨ Formatting backend..." -ForegroundColor Cyan
    Set-Location backend
    ruff format .
    Set-Location ..

    Write-Host "✨ Formatting frontend..." -ForegroundColor Cyan
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

# Run all checks
function Invoke-AllChecks {
    Invoke-Lint
    Invoke-TypeCheck
    Invoke-AllTests
    Write-Host "✅ All checks passed!" -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 🗄️ DATABASE
# ------------------------------------------------------------------------------

# Run migrations (upgrade)
function Invoke-Migrations {
    docker compose exec backend alembic upgrade head
}

# Create migration
function New-Migration {
    param([string]$Message)
    docker compose exec backend alembic revision --autogenerate -m "$Message"
}

# Downgrade migration
function Undo-Migration {
    docker compose exec backend alembic downgrade -1
}

# Seed database
function Initialize-Database {
    docker compose exec backend python -m app.cli.main db seed
}

# Cleanup E2E test users
function Remove-E2EUsers {
    docker compose exec backend python cleanup_e2e_users.py
}

# ------------------------------------------------------------------------------
# 👤 CLI COMMANDS
# ------------------------------------------------------------------------------

# Create superuser
function New-Superuser {
    docker compose exec backend python -m app.cli.main users create-superuser
}

# Create API key
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

# Clean artifacts
function Clear-Artifacts {
    Write-Host "🧹 Cleaning artifacts..." -ForegroundColor Cyan

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

    Write-Host "✅ Cleanup complete" -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 📚 HELP
# ------------------------------------------------------------------------------

function Show-Help {
    Write-Host ""
    Write-Host "FastAPI-Enterprise-Boilerplate - PowerShell Commands" -ForegroundColor Green
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "🐳 Docker - Development:" -ForegroundColor Cyan
    Write-Host "  Start-DevEnvironment         Start dev environment"
    Write-Host "  Start-DevEnvironmentBuild    Rebuild and start dev"
    Write-Host "  Stop-DockerServices          Stop services"
    Write-Host "  Show-DockerLogs              View logs"
    Write-Host "  Clear-Docker                 Clean volumes"
    Write-Host ""
    Write-Host "🚀 Docker - Production:" -ForegroundColor Cyan
    Write-Host "  Start-Production             Start production"
    Write-Host "  Start-ProductionBuild        Rebuild production"
    Write-Host "  Stop-Production              Stop production"
    Write-Host "  Show-ProductionLogs          View production logs"
    Write-Host "  New-ProductionBuild          Build prod images"
    Write-Host "  Publish-Production           Deploy production"
    Write-Host ""
    Write-Host "💻 Local Development:" -ForegroundColor Cyan
    Write-Host "  Install-Dependencies         Install dependencies"
    Write-Host "  Start-Backend                Run backend"
    Write-Host "  Start-Frontend               Run frontend"
    Write-Host ""
    Write-Host "🧪 Testing:" -ForegroundColor Cyan
    Write-Host "  Invoke-AllTests              Run all tests"
    Write-Host "  Invoke-UnitTests             Run unit tests"
    Write-Host "  Invoke-IntegrationTests      Run integration tests"
    Write-Host "  Invoke-IntegrationTestsCoverage  Integration tests + coverage"
    Write-Host "  Invoke-FrontendTests         Run frontend tests"
    Write-Host "  Start-TestDatabase           Start test DB"
    Write-Host "  Stop-TestDatabase            Stop test DB"
    Write-Host ""
    Write-Host "🔍 Code Quality:" -ForegroundColor Cyan
    Write-Host "  Invoke-Lint                  Linting"
    Write-Host "  Format-Code                  Format code"
    Write-Host "  Invoke-TypeCheck             Type checking"
    Write-Host "  Invoke-AllChecks             Run all checks"
    Write-Host ""
    Write-Host "🗄️ Database:" -ForegroundColor Cyan
    Write-Host "  Invoke-Migrations            Apply migrations"
    Write-Host "  New-Migration -Message '...' Create migration"
    Write-Host "  Undo-Migration               Revert migration"
    Write-Host "  Initialize-Database          Seed data"
    Write-Host "  Remove-E2EUsers              Remove E2E users"
    Write-Host ""
    Write-Host "👤 CLI:" -ForegroundColor Cyan
    Write-Host "  New-Superuser                Create superuser"
    Write-Host "  New-ApiKey                   Create API key"
    Write-Host "  Test-Health                  Health check"
    Write-Host ""
    Write-Host "🧹 Cleanup:" -ForegroundColor Cyan
    Write-Host "  Clear-Artifacts              Clean artifacts"
    Write-Host ""
    Write-Host "To use: dot-source this file first:" -ForegroundColor Yellow
    Write-Host "  . .\make.ps1" -ForegroundColor Yellow
    Write-Host "  Show-Help" -ForegroundColor Yellow
    Write-Host ""
}

# Show help when loading the script
Show-Help
