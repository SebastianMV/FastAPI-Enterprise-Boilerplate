# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.
    
    Startup: Initialize database, Redis, telemetry.
    Shutdown: Close connections gracefully.
    """
    # Startup
    from app.infrastructure.database.connection import init_database
    
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    
    # Setup logging
    from app.infrastructure.observability.logging import setup_logging
    setup_logging()
    logger.info("✅ Logging configured")
    
    # Setup telemetry (if enabled)
    if settings.OTEL_ENABLED:
        from app.infrastructure.observability.telemetry import setup_telemetry
        setup_telemetry()
        logger.info("✅ OpenTelemetry initialized")
    
    # Initialize database (runs Alembic migrations automatically)
    try:
        await init_database()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"⚠️ Database initialization failed: {e}")
    
    # Initialize uptime tracker
    try:
        from app.infrastructure.monitoring import get_uptime_tracker
        uptime_tracker = get_uptime_tracker()
        await uptime_tracker.initialize()
        logger.info("✅ Uptime tracker initialized")
    except Exception as e:
        logger.warning(f"⚠️ Uptime tracker initialization failed (non-critical): {e}")
    
    yield
    
    # Shutdown
    from app.infrastructure.database.connection import close_database
    
    await close_database()
    logger.info("👋 Shutting down gracefully...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## FastAPI Enterprise Boilerplate

Production-ready starter kit with:

- 🔐 **JWT Authentication** with refresh tokens
- 🛡️ **Granular ACL** - Permission-based access control
- 🏢 **Multi-Tenant (RLS)** - Data isolation at database level
- 🏗️ **Hexagonal Architecture** - Clean separation of concerns
- 📊 **OpenTelemetry** - Traces, metrics, structured logs
- ⚡ **Rate Limiting** - Redis-based API protection
- 🚀 **Background Jobs** - Async task processing

[GitHub Repository](https://github.com/your-username/fastapi-enterprise-boilerplate)
    """,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ===========================================
# Middleware (order matters: last added = first executed)
# ===========================================

# CORS (outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics (track response times)
from app.middleware.metrics import MetricsMiddleware
app.add_middleware(MetricsMiddleware)

# Rate Limiting (if enabled)
if settings.RATE_LIMIT_ENABLED:
    from app.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

# Tenant Context
from app.middleware.tenant import TenantMiddleware
app.add_middleware(TenantMiddleware)


# ===========================================
# Routers
# ===========================================

# Include API v1 router
app.include_router(api_router, prefix="/api/v1")


# ===========================================
# Root endpoint
# ===========================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if not settings.is_production else None,
        "health": "/api/v1/health",
    }
