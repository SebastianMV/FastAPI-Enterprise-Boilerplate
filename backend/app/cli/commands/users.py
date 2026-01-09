# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
User management CLI commands.

Commands:
- create-superuser: Create a new superuser account
- list: List all users
- activate: Activate a user account
- deactivate: Deactivate a user account
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from app.cli.utils import format_uuid, print_table

app = typer.Typer(help="User management commands")
console = Console()


@app.command("create-superuser")
def create_superuser(
    email: str = typer.Option(
        ...,
        "--email", "-e",
        help="Email address for the superuser",
        prompt=True,
    ),
    password: str = typer.Option(
        ...,
        "--password", "-p",
        help="Password for the superuser",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
    ),
    first_name: str = typer.Option(
        "Admin",
        "--first-name", "-f",
        help="First name",
    ),
    last_name: str = typer.Option(
        "User",
        "--last-name", "-l",
        help="Last name",
    ),
) -> None:
    """
    Create a new superuser account.
    
    Example:
        cli users create-superuser --email admin@example.com
    """
    asyncio.run(_create_superuser(email, password, first_name, last_name))


async def _create_superuser(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> None:
    """Async implementation of create-superuser command."""
    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
    from app.infrastructure.auth.jwt_handler import hash_password
    from app.domain.entities.user import User
    from app.domain.value_objects.email import Email
    from app.domain.value_objects.password import Password
    from app.cli.utils import get_or_create_default_tenant
    
    try:
        # Validate email
        validated_email = Email(email)
    except ValueError as e:
        console.print(f"[red]Invalid email: {e}[/red]")
        raise typer.Exit(1)
    
    try:
        # Validate password
        validated_password = Password(password)
    except ValueError as e:
        console.print(f"[red]Invalid password: {e}[/red]")
        raise typer.Exit(1)
    
    async with async_session_maker() as session:
        repo = SQLAlchemyUserRepository(session)
        
        # Check if email already exists
        existing = await repo.get_by_email(email)
        if existing:
            console.print(f"[red]Error: User with email '{email}' already exists[/red]")
            raise typer.Exit(1)
        
        # Get or create default tenant
        tenant_id = await get_or_create_default_tenant()
        
        # Create user entity
        user = User(
            email=validated_email,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_superuser=True,
            tenant_id=tenant_id,
        )
        user.set_password(validated_password, hash_password)
        
        # Save to database
        created_user = await repo.create(user)
        await session.commit()
        
        console.print(f"\n[green]✓ Superuser created successfully![/green]")
        console.print(f"  ID: {created_user.id}")
        console.print(f"  Email: {email}")
        console.print(f"  Tenant: {tenant_id}")


@app.command("list")
def list_users(
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum users to display"),
    active_only: bool = typer.Option(False, "--active", "-a", help="Show only active users"),
) -> None:
    """
    List all users in the system.
    
    Example:
        cli users list --limit 20 --active
    """
    asyncio.run(_list_users(limit, active_only))


async def _list_users(limit: int, active_only: bool) -> None:
    """Async implementation of list command."""
    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
    
    async with async_session_maker() as session:
        repo = SQLAlchemyUserRepository(session)
        
        users = await repo.list(
            limit=limit,
            is_active=True if active_only else None,
        )
        
        if not users:
            console.print("[yellow]No users found[/yellow]")
            raise typer.Exit(0)
        
        # Build table
        table = Table(title=f"Users ({len(users)} found)")
        table.add_column("ID", style="dim")
        table.add_column("Email", style="cyan")
        table.add_column("Name")
        table.add_column("Active", justify="center")
        table.add_column("Superuser", justify="center")
        table.add_column("Created At")
        
        for user in users:
            table.add_row(
                str(user.id)[:8] + "...",
                str(user.email),
                user.full_name or "-",
                "✓" if user.is_active else "✗",
                "✓" if user.is_superuser else "✗",
                user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "-",
            )
        
        console.print(table)


@app.command("activate")
def activate_user(
    user_id: str = typer.Argument(..., help="User ID to activate"),
) -> None:
    """
    Activate a user account.
    
    Example:
        cli users activate 550e8400-e29b-41d4-a716-446655440000
    """
    uuid = format_uuid(user_id)
    if not uuid:
        console.print("[red]Invalid UUID format[/red]")
        raise typer.Exit(1)
    
    asyncio.run(_set_user_active(uuid, True))


@app.command("deactivate")
def deactivate_user(
    user_id: str = typer.Argument(..., help="User ID to deactivate"),
) -> None:
    """
    Deactivate a user account.
    
    Example:
        cli users deactivate 550e8400-e29b-41d4-a716-446655440000
    """
    uuid = format_uuid(user_id)
    if not uuid:
        console.print("[red]Invalid UUID format[/red]")
        raise typer.Exit(1)
    
    asyncio.run(_set_user_active(uuid, False))


async def _set_user_active(user_id, active: bool) -> None:
    """Async implementation of activate/deactivate commands."""
    from uuid import UUID
    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
    
    async with async_session_maker() as session:
        repo = SQLAlchemyUserRepository(session)
        
        user = await repo.get_by_id(user_id)
        if not user:
            console.print(f"[red]User not found: {user_id}[/red]")
            raise typer.Exit(1)
        
        if active:
            user.activate()
        else:
            user.deactivate()
        
        await repo.update(user)
        await session.commit()
        
        action = "activated" if active else "deactivated"
        console.print(f"[green]✓ User {user.email} {action}[/green]")
