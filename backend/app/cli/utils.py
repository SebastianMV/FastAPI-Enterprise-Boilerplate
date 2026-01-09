# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Utility functions for CLI commands."""

import asyncio
from typing import Optional
from uuid import UUID


async def check_database() -> bool:
    """
    Check database connectivity.
    
    Returns:
        True if database is accessible, False otherwise
    """
    try:
        from sqlalchemy import text
        from app.infrastructure.database.connection import async_session_maker
        
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


async def check_redis() -> bool:
    """
    Check Redis connectivity.
    
    Returns:
        True if Redis is accessible, False otherwise
    """
    try:
        from app.infrastructure.cache.redis_client import get_redis_client
        
        redis = await get_redis_client()
        await redis.ping()
        return True
    except Exception:
        return False


def format_uuid(uuid_str: str) -> Optional[UUID]:
    """
    Parse and validate a UUID string.
    
    Args:
        uuid_str: String representation of UUID
        
    Returns:
        UUID object if valid, None otherwise
    """
    try:
        return UUID(uuid_str)
    except ValueError:
        return None


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask for user confirmation.
    
    Args:
        message: Confirmation message
        default: Default value if user presses enter
        
    Returns:
        True if confirmed, False otherwise
    """
    import typer
    
    suffix = "[Y/n]" if default else "[y/N]"
    response = typer.prompt(f"{message} {suffix}", default="y" if default else "n")
    
    return response.lower() in ("y", "yes")


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """
    Print a formatted table to console.
    
    Args:
        headers: Column headers
        rows: Table rows
    """
    import typer
    
    if not rows:
        typer.echo("No data to display")
        return
    
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    
    # Print header
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    typer.echo(header_line)
    typer.echo("-" * len(header_line))
    
    # Print rows
    for row in rows:
        row_line = " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(row))
        typer.echo(row_line)


async def get_or_create_default_tenant() -> UUID:
    """
    Get or create a default tenant for CLI operations.
    
    Returns:
        UUID of the default tenant
    """
    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
    from app.domain.entities.tenant import Tenant
    
    async with async_session_maker() as session:
        repo = SQLAlchemyTenantRepository(session)
        
        # Try to find existing default tenant
        tenants = await repo.list(limit=1)
        if tenants:
            return tenants[0].id
        
        # Create default tenant
        tenant = Tenant(
            name="Default",
            slug="default",
            is_active=True,
        )
        created = await repo.create(tenant)
        await session.commit()
        
        return created.id
