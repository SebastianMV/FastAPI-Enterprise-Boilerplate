# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Async database engine and session configuration.

Uses SQLAlchemy 2.0 async with asyncpg for PostgreSQL.
Includes RLS (Row Level Security) support for multi-tenant isolation.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


# Build connect_args with optional SSL
_connect_args: dict[str, object] = {}
if settings.DB_SSL_REQUIRED:
    import ssl as _ssl

    _ssl_ctx = _ssl.create_default_context()
    _connect_args["ssl"] = _ssl_ctx

# Create async engine
engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO,  # Log SQL queries (separate from DEBUG)
    connect_args=_connect_args,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# SQLAlchemy event listener to set RLS context at transaction start
# NOTE: Temporarily disabled due to asyncpg parameterization issues with SET
# @event.listens_for(Session, "after_begin")
# def receive_after_begin(session, transaction, connection):
#     """
#     SQLAlchemy event: Set RLS tenant context after transaction begins.
#
#     This ensures the PostgreSQL session variable is set BEFORE any
#     queries execute, making RLS policies work correctly with asyncpg.
#
#     The tenant_id is retrieved from the context variable set by
#     TenantMiddleware.
#     """
#     # Import here to avoid circular dependency
#     from app.middleware.tenant import get_current_tenant_id
#
#     tenant_id = get_current_tenant_id()
#     if tenant_id:
#         # Use exec_driver_sql to avoid parameterization issues with SET
#         connection.exec_driver_sql(
#             f"SET LOCAL app.current_tenant_id = '{tenant_id}'"
#         )


async def set_tenant_context(session: AsyncSession, tenant_id: UUID | None) -> None:
    """
    Set PostgreSQL session variable for RLS filtering.

    This sets app.current_tenant_id which is used by RLS policies
    to filter queries automatically by tenant.

    Uses set_config(..., is_local=true) with bind params to avoid
    string interpolation while keeping transaction-local scope.

    Args:
        session: Active database session
        tenant_id: Tenant UUID to set (None clears the context)
    """
    if tenant_id:
        # Validate UUID and set via bind params (transaction-local)
        from uuid import UUID as _UUID

        validated = str(_UUID(str(tenant_id)))
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": validated},
        )
    else:
        await session.execute(text("RESET app.current_tenant_id"))


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """
    Dependency that provides a database session with RLS context.

    Automatically sets tenant context from middleware if available.

    Usage in FastAPI:
        @router.get("/users")
        async def get_users(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    # Import here to avoid circular dependency
    from app.middleware.tenant import get_current_tenant_id

    async with async_session_maker() as session:
        try:
            # Set RLS context from middleware
            tenant_id = get_current_tenant_id()
            if tenant_id:
                await set_tenant_context(session, tenant_id)

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context(
    tenant_id: UUID | None = None,
) -> AsyncGenerator[AsyncSession]:
    """
    Context manager for database session with optional tenant context.

    Usage:
        async with get_db_context(tenant_id) as session:
            ...

    Args:
        tenant_id: Optional tenant UUID for RLS context
    """
    async with async_session_maker() as session:
        try:
            if tenant_id:
                await set_tenant_context(session, tenant_id)

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """
    Initialize database by running Alembic migrations.

    Should be called during application startup.
    Uses Alembic for proper migration tracking instead of create_all.
    Uses asyncio subprocess to avoid blocking the event loop.
    """
    import asyncio
    import os

    from app.infrastructure.observability.logging import get_logger

    logger = get_logger(__name__)

    # Get the backend directory (where alembic.ini is located)
    backend_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    process_env = os.environ.copy()
    existing_pythonpath = process_env.get("PYTHONPATH", "")
    if existing_pythonpath:
        process_env["PYTHONPATH"] = f"{backend_dir}{os.pathsep}{existing_pythonpath}"
    else:
        process_env["PYTHONPATH"] = backend_dir

    try:
        # Run alembic upgrade head (non-blocking)
        process = await asyncio.create_subprocess_exec(
            "alembic",
            "upgrade",
            "head",
            cwd=backend_dir,
            env=process_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        migration_timeout_seconds = 60

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=migration_timeout_seconds
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            logger.error("alembic_migration_timeout")
            raise

        if process.returncode != 0:
            logger.error("alembic_migration_failed")
            if settings.ENVIRONMENT in ("production", "staging"):
                raise RuntimeError(
                    f"Alembic migration failed in {settings.ENVIRONMENT} — refusing to fall back "
                    "to create_all() (no RLS/triggers)"
                )
            # Development/testing: fallback to create_all for convenience
            logger.warning("alembic_fallback_create_all")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            logger.info("alembic_migrations_applied")
            if stdout:
                for line in stdout.decode().strip().split("\n"):
                    logger.info("alembic_migration_output", line=line)
    except FileNotFoundError:
        if settings.ENVIRONMENT in ("production", "staging"):
            raise RuntimeError(
                f"Alembic not found in {settings.ENVIRONMENT} — refusing to fall back "
                "to create_all() (no RLS/triggers)"
            ) from None
        logger.warning("alembic_not_found_fallback")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """
    Close database connections.

    Should be called during application shutdown.
    """
    await engine.dispose()
