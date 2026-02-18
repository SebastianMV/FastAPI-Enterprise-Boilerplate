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
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from app.cli.utils import format_uuid
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

app = typer.Typer(help="User management commands")
console = Console()


@app.command("create-superuser")
def create_superuser(
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        help="Email address for the superuser",
        prompt=True,
    ),
    password: str = typer.Option(
        ...,
        "--password",
        "-p",
        help="Password for the superuser",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
    ),
    first_name: str = typer.Option(
        "Admin",
        "--first-name",
        "-f",
        help="First name",
    ),
    last_name: str = typer.Option(
        "User",
        "--last-name",
        "-l",
        help="Last name",
    ),
) -> None:
    """
    Create a new superuser account.

    Example:
        cli users create-superuser --email admin@example.com
    """
    asyncio.run(_create_superuser(email, password, first_name, last_name))


MAX_NAME_LENGTH = 200


async def _create_superuser(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> None:
    """Async implementation of create-superuser command."""
    from app.cli.utils import get_or_create_default_tenant
    from app.domain.entities.user import User
    from app.domain.exceptions.base import ValidationError as DomainValidationError
    from app.domain.value_objects.email import Email
    from app.domain.value_objects.password import Password
    from app.infrastructure.auth.jwt_handler import hash_password
    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.repositories.user_repository import (
        SQLAlchemyUserRepository,
    )

    # Validate name lengths (Rule 6)
    if len(first_name) > MAX_NAME_LENGTH:
        console.print(f"[red]First name too long (max {MAX_NAME_LENGTH})[/red]")
        raise typer.Exit(1)
    if len(last_name) > MAX_NAME_LENGTH:
        console.print(f"[red]Last name too long (max {MAX_NAME_LENGTH})[/red]")
        raise typer.Exit(1)

    try:
        # Validate email
        validated_email = Email(email)
    except (ValueError, DomainValidationError):
        console.print("[red]Invalid email format[/red]")
        raise typer.Exit(1) from None

    try:
        # Validate password
        validated_password = Password(password)
    except (ValueError, DomainValidationError):
        console.print("[red]Password does not meet security requirements[/red]")
        raise typer.Exit(1) from None

    async with async_session_maker() as session:
        repo = SQLAlchemyUserRepository(session)

        # Check if email already exists
        existing = await repo.get_by_email(email)
        if existing:
            console.print("[red]Error: A user with this email already exists[/red]")
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

        logger.info(
            "superuser_created",
            email=email,
            user_id=str(created_user.id),
            tenant_id=str(tenant_id),
        )
        console.print("\n[green]✓ Superuser created successfully![/green]")
        console.print(f"  ID: {created_user.id}")
        console.print(f"  Email: {email}")
        console.print(f"  Tenant: {tenant_id}")


@app.command("list")
def list_users(
    limit: int = typer.Option(
        50, "--limit", "-n", help="Maximum users to display", min=1, max=1000
    ),
    active_only: bool = typer.Option(
        False, "--active", "-a", help="Show only active users"
    ),
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
    from app.infrastructure.database.repositories.user_repository import (
        SQLAlchemyUserRepository,
    )

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


async def _set_user_active(user_id: UUID, active: bool) -> None:
    """Async implementation of activate/deactivate commands."""
    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.repositories.user_repository import (
        SQLAlchemyUserRepository,
    )

    async with async_session_maker() as session:
        repo = SQLAlchemyUserRepository(session)

        user = await repo.get_by_id(user_id)
        if not user:
            console.print("[red]User not found[/red]")
            raise typer.Exit(1)

        if active:
            user.activate()
        else:
            user.deactivate()

        await repo.update(user)
        await session.commit()

        action = "activated" if active else "deactivated"
        logger.info(
            "user_status_changed",
            user_id=str(user_id),
            email=str(user.email),
            action=action,
        )
        console.print(f"[green]✓ User {user.email} {action}[/green]")
