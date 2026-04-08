# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

# ============================================
# Makefile - Development Commands
# ============================================

.PHONY: help install dev test lint format clean docker-up docker-down migrate

# Default target
help:
	@echo "FastAPI-Enterprise-Boilerplate - Available Commands"
	@echo ""
	@echo "🐳 Docker - Development:"
	@echo "  make docker-dev         Start dev environment (hot-reload)"
	@echo "  make docker-dev-build   Rebuild and start dev environment"
	@echo "  make docker-down        Stop all services"
	@echo "  make docker-logs        View all logs"
	@echo "  make docker-clean       Stop and remove volumes"
	@echo ""
	@echo "🚀 Docker - Production:"
	@echo "  make docker-prod        Start production environment"
	@echo "  make docker-prod-build  Rebuild and start production"
	@echo "  make docker-prod-down   Stop production services"
	@echo "  make docker-prod-logs   View production logs"
	@echo ""
	@echo "💻 Local Development:"
	@echo "  make install            Install all dependencies"
	@echo "  make dev                Run development servers locally"
	@echo "  make lint               Run linting"
	@echo "  make format             Format code"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test                   Run all tests"
	@echo "  make test-unit              Run unit tests"
	@echo "  make test-integration       Run integration tests"
	@echo "  make test-integration-coverage  Integration tests with coverage"
	@echo "  make test-frontend          Run frontend tests"
	@echo "  make test-db-start          Start test database (PostgreSQL)"
	@echo "  make test-db-stop           Stop test database"
	@echo ""
	@echo "🗄️ Database:"
	@echo "  make migrate            Run database migrations"
	@echo "  make migrate-create     Create new migration"
	@echo "  make seed               Seed database with sample data"
	@echo "  make cleanup-e2e        Cleanup E2E test users"
	@echo ""
	@echo "🔍 Utilities:"
	@echo "  make check              Run all checks (lint, type-check, test)"
	@echo "  make clean              Clean build artifacts"

# ===========================================
# Installation
# ===========================================
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install
	pre-commit install

# ===========================================
# Development
# ===========================================
dev:
	docker compose up -d db redis
	@echo "Starting backend..."
	cd backend && uvicorn app.main:app --reload --port 8000 &
	@echo "Starting frontend..."
	cd frontend && npm run dev

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# ===========================================
# Testing
# ===========================================
test:
	cd backend && pytest tests/ -v --cov=app

test-unit:
	cd backend && pytest tests/unit/ -v

test-integration:
	cd backend && pytest tests/integration/ -v

test-integration-coverage:
	cd backend && coverage run --source=app -m pytest tests/integration/ -v && coverage report

test-frontend:
	cd frontend && npm test

test-db-start:
	@echo "Starting test database..."
	docker compose -f docker-compose.test.yml up -d
	@echo "PostgreSQL test DB running on port 5433"

test-db-stop:
	docker compose -f docker-compose.test.yml down

# ===========================================
# Code Quality
# ===========================================
lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format

type-check:
	cd backend && mypy app

check: lint type-check test
	@echo "✅ All checks passed!"

# ===========================================
# Docker - Development
# ===========================================
docker-dev:
	docker compose up -d

docker-dev-build:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-clean:
	docker compose down -v

# ===========================================
# Docker - Production
# ===========================================
docker-prod:
	docker compose -f docker-compose.deploy.yml up -d

docker-prod-build:
	docker compose -f docker-compose.deploy.yml up -d --build

docker-prod-down:
	docker compose -f docker-compose.deploy.yml down

docker-prod-logs:
	docker compose -f docker-compose.deploy.yml logs -f

# ===========================================
# Database
# ===========================================
migrate:
	docker compose exec backend alembic upgrade head

migrate-create:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

migrate-down:
	docker compose exec backend alembic downgrade -1

seed:
	docker compose exec backend python -m app.cli.main db seed

cleanup-e2e:
	docker compose exec backend python cleanup_e2e_users.py

# ===========================================
# CLI Commands
# ===========================================
create-superuser:
	docker compose exec backend python -m app.cli.main users create-superuser

create-apikey:
	cd backend && python -m app.cli.main apikeys create

health:
	cd backend && python -m app.cli.main health

# ===========================================
# Cleanup
# ===========================================
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -rf backend/.coverage
	rm -rf frontend/coverage

# ===========================================
# Production
# ===========================================
build:
	docker compose -f docker-compose.deploy.yml build

deploy:
	docker compose -f docker-compose.deploy.yml up -d
	docker compose -f docker-compose.deploy.yml exec backend alembic upgrade head
