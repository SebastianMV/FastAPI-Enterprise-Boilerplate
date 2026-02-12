# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

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
_connect_args: dict = {}
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

    Note: asyncpg doesn't support bind parameters in SET commands,
    so we use string formatting (tenant_id is already a UUID object,
    so SQL injection is not possible).

    Args:
        session: Active database session
        tenant_id: Tenant UUID to set (None clears the context)
    """
    if tenant_id:
        # Validate UUID before interpolation (asyncpg doesn't support params in SET)
        from uuid import UUID as _UUID

        validated = str(_UUID(str(tenant_id)))
        await session.execute(text(f"SET LOCAL app.current_tenant_id = '{validated}'"))
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

    try:
        # Run alembic upgrade head (non-blocking)
        process = await asyncio.create_subprocess_exec(
            "alembic",
            "upgrade",
            "head",
            cwd=backend_dir,
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
            logger.error("Alembic migration timed out")
            raise

        if process.returncode != 0:
            logger.error("Alembic migration failed: %s", stderr.decode())
            if settings.ENVIRONMENT in ("production", "staging"):
                raise RuntimeError(
                    "Alembic migration failed in %s — refusing to fall back "
                    "to create_all() (no RLS/triggers)" % settings.ENVIRONMENT
                )
            # Development/testing: fallback to create_all for convenience
            logger.warning("Falling back to Base.metadata.create_all() (dev only)")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            logger.info("Alembic migrations applied successfully")
            if stdout:
                for line in stdout.decode().strip().split("\n"):
                    logger.info("  %s", line)
    except FileNotFoundError:
        if settings.ENVIRONMENT in ("production", "staging"):
            raise RuntimeError(
                "Alembic not found in %s — refusing to fall back "
                "to create_all() (no RLS/triggers)" % settings.ENVIRONMENT
            )
        logger.warning("Alembic not found, using Base.metadata.create_all() (dev only)")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """
    Close database connections.

    Should be called during application shutdown.
    """
    await engine.dispose()
