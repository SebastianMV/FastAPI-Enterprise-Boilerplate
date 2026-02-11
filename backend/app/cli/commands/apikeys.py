# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
API Key management CLI commands.

Commands:
- generate: Generate a new API key
- list: List all API keys
- revoke: Revoke an API key
- info: Show API key information
"""

import asyncio
import secrets
from datetime import UTC, datetime, timedelta

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.cli.utils import confirm_action, format_uuid

app = typer.Typer(help="API key management commands")
console = Console()


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key and its hash.

    Returns:
        Tuple of (plain_key, prefix)
    """
    # Generate a secure random key
    key = secrets.token_urlsafe(32)
    prefix = key[:8]

    return key, prefix


@app.command("generate")
def create_api_key(
    name: str = typer.Option(
        ...,
        "--name",
        "-n",
        help="Human-readable name for the API key",
        prompt=True,
    ),
    user_email: str = typer.Option(
        ...,
        "--user",
        "-u",
        help="Email of the user who owns this key",
        prompt=True,
    ),
    scopes: str | None = typer.Option(
        None,
        "--scopes",
        "-s",
        help="Comma-separated list of permission scopes",
    ),
    expires_days: int | None = typer.Option(
        None,
        "--expires",
        "-e",
        help="Days until key expires (default: never)",
    ),
) -> None:
    """
    Generate a new API key.

    Example:
        cli apikeys generate --name "CI/CD Key" --user admin@example.com
        cli apikeys generate -n "Read-only" -u admin@example.com -s "users:read,reports:read"
        cli apikeys generate -n "Temp Key" -u admin@example.com -e 30
    """
    scope_list = scopes.split(",") if scopes else []
    asyncio.run(_create_api_key(name, user_email, scope_list, expires_days))


async def _create_api_key(
    name: str,
    user_email: str,
    scopes: list[str],
    expires_days: int | None,
) -> None:
    """Async implementation of generate command."""
    from app.infrastructure.auth.jwt_handler import hash_password
    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.models.api_key import APIKeyModel
    from app.infrastructure.database.repositories.user_repository import (
        SQLAlchemyUserRepository,
    )

    async with async_session_maker() as session:
        # Find user
        user_repo = SQLAlchemyUserRepository(session)
        user = await user_repo.get_by_email(user_email)

        if not user:
            from rich.markup import escape

            console.print(f"[red]User not found: {escape(user_email)}[/red]")
            raise typer.Exit(1)

        # Generate key
        plain_key, prefix = generate_api_key()
        key_hash = hash_password(plain_key)

        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_days)

        # Create API key model
        api_key_model = APIKeyModel(
            name=name,
            prefix=prefix,
            key_hash=key_hash,
            user_id=user.id,
            tenant_id=user.tenant_id,
            scopes=scopes,
            is_active=True,
            expires_at=expires_at,
        )

        session.add(api_key_model)
        await session.flush()
        await session.refresh(api_key_model)
        await session.commit()

        # Display the key (only shown once!)
        console.print()
        console.print(
            Panel(
                f"[bold green]{plain_key}[/bold green]",
                title="🔑 API Key Generated",
                subtitle="Copy this key now - it won't be shown again!",
                border_style="green",
            )
        )
        console.print()
        console.print(f"  Name: {name}")
        console.print(f"  Prefix: {prefix}")
        console.print(f"  User: {user_email}")
        console.print(
            f"  Scopes: {', '.join(scopes) if scopes else 'All (no restrictions)'}"
        )
        console.print(
            f"  Expires: {expires_at.strftime('%Y-%m-%d') if expires_at else 'Never'}"
        )
        console.print()


@app.command("list")
def list_api_keys(
    user_email: str | None = typer.Option(
        None, "--user", "-u", help="Filter by user email"
    ),
    show_inactive: bool = typer.Option(
        False, "--inactive", "-i", help="Include inactive keys"
    ),
) -> None:
    """
    List all API keys.

    Example:
        cli apikeys list
        cli apikeys list --user admin@example.com
        cli apikeys list --inactive
    """
    asyncio.run(_list_api_keys(user_email, show_inactive))


async def _list_api_keys(
    user_email: str | None,
    show_inactive: bool,
) -> None:
    """Async implementation of list command."""
    from sqlalchemy import select

    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.models.api_key import APIKeyModel
    from app.infrastructure.database.models.user import UserModel

    async with async_session_maker() as session:
        stmt = select(APIKeyModel, UserModel).join(
            UserModel, APIKeyModel.user_id == UserModel.id
        )

        if not show_inactive:
            stmt = stmt.where(APIKeyModel.is_active == True)

        if user_email:
            stmt = stmt.where(UserModel.email == user_email.lower())

        result = await session.execute(stmt)
        keys = result.all()

        if not keys:
            console.print("[yellow]No API keys found[/yellow]")
            raise typer.Exit(0)

        # Build table
        table = Table(title=f"API Keys ({len(keys)} found)")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Prefix")
        table.add_column("User")
        table.add_column("Scopes")
        table.add_column("Active", justify="center")
        table.add_column("Expires")
        table.add_column("Last Used")

        now = datetime.now(UTC)
        for api_key, user in keys:
            # Check if expired
            is_expired = api_key.expires_at and api_key.expires_at < now
            status = "✗" if not api_key.is_active else ("⚠" if is_expired else "✓")

            table.add_row(
                str(api_key.id)[:8] + "...",
                api_key.name,
                api_key.prefix + "...",
                user.email,
                ", ".join(api_key.scopes[:2])
                + ("..." if len(api_key.scopes) > 2 else "")
                if api_key.scopes
                else "*",
                status,
                api_key.expires_at.strftime("%Y-%m-%d")
                if api_key.expires_at
                else "Never",
                api_key.last_used_at.strftime("%Y-%m-%d")
                if api_key.last_used_at
                else "Never",
            )

        console.print(table)


@app.command("revoke")
def revoke_api_key(
    key_id: str = typer.Argument(..., help="API key ID or prefix to revoke"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Revoke an API key.

    Example:
        cli apikeys revoke 550e8400-e29b-41d4-a716-446655440000
        cli apikeys revoke abc12345 --force  # Using prefix
    """
    asyncio.run(_revoke_api_key(key_id, force))


async def _revoke_api_key(key_id: str, force: bool) -> None:
    """Async implementation of revoke command."""
    from sqlalchemy import select

    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.models.api_key import APIKeyModel

    async with async_session_maker() as session:
        # Find by ID or prefix
        uuid = format_uuid(key_id)

        if uuid:
            stmt = select(APIKeyModel).where(APIKeyModel.id == uuid)
        else:
            stmt = select(APIKeyModel).where(APIKeyModel.prefix == key_id[:8])

        result = await session.execute(stmt)
        api_key = result.scalar_one_or_none()

        if not api_key:
            from rich.markup import escape

            console.print(f"[red]API key not found: {escape(key_id)}[/red]")
            raise typer.Exit(1)

        if not api_key.is_active:
            console.print(
                f"[yellow]API key is already revoked: {api_key.name}[/yellow]"
            )
            raise typer.Exit(0)

        if not force:
            if not confirm_action(
                f"Revoke API key '{api_key.name}' ({api_key.prefix}...)?"
            ):
                raise typer.Exit(0)

        api_key.is_active = False
        await session.commit()

        console.print(f"[green]✓ API key revoked: {api_key.name}[/green]")


@app.command("info")
def api_key_info(
    key_id: str = typer.Argument(..., help="API key ID or prefix"),
) -> None:
    """
    Show detailed information about an API key.

    Example:
        cli apikeys info 550e8400-e29b-41d4-a716-446655440000
    """
    asyncio.run(_api_key_info(key_id))


async def _api_key_info(key_id: str) -> None:
    """Async implementation of info command."""
    from sqlalchemy import select

    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.models.api_key import APIKeyModel
    from app.infrastructure.database.models.user import UserModel

    async with async_session_maker() as session:
        uuid = format_uuid(key_id)

        if uuid:
            stmt = (
                select(APIKeyModel, UserModel)
                .join(UserModel, APIKeyModel.user_id == UserModel.id)
                .where(APIKeyModel.id == uuid)
            )
        else:
            stmt = (
                select(APIKeyModel, UserModel)
                .join(UserModel, APIKeyModel.user_id == UserModel.id)
                .where(APIKeyModel.prefix == key_id[:8])
            )

        result = await session.execute(stmt)
        row = result.one_or_none()

        if not row:
            from rich.markup import escape

            console.print(f"[red]API key not found: {escape(key_id)}[/red]")
            raise typer.Exit(1)

        api_key, user = row
        now = datetime.now(UTC)
        is_expired = api_key.expires_at and api_key.expires_at < now

        console.print()
        console.print(
            Panel(
                f"[bold]{api_key.name}[/bold]",
                title="API Key Details",
                border_style="cyan",
            )
        )

        console.print(f"  ID:          {api_key.id}")
        console.print(f"  Prefix:      {api_key.prefix}...")
        console.print(f"  Owner:       {user.email}")
        console.print(f"  Tenant:      {api_key.tenant_id}")
        console.print()
        console.print(
            f"  Status:      {'[red]Revoked[/red]' if not api_key.is_active else ('[yellow]Expired[/yellow]' if is_expired else '[green]Active[/green]')}"
        )
        console.print(
            f"  Created:     {api_key.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        console.print(
            f"  Expires:     {api_key.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC') if api_key.expires_at else 'Never'}"
        )
        console.print()
        console.print("  Scopes:")
        if api_key.scopes:
            for scope in api_key.scopes:
                console.print(f"    - {scope}")
        else:
            console.print("    [dim](All permissions)[/dim]")
        console.print()
        console.print("  Usage:")
        console.print(f"    Total requests:  {api_key.usage_count}")
        console.print(
            f"    Last used:       {api_key.last_used_at.strftime('%Y-%m-%d %H:%M:%S UTC') if api_key.last_used_at else 'Never'}"
        )
        console.print(f"    Last IP:         {api_key.last_used_ip or 'N/A'}")
        console.print()
