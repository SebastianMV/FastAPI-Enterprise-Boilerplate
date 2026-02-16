# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Database management CLI commands.

Commands:
- seed: Seed the database with sample data
- migrate: Run database migrations
- reset: Reset the database (development only)
- info: Show database information
"""

import asyncio

import typer
from rich.console import Console

from app.cli.utils import confirm_action
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

app = typer.Typer(help="Database management commands")
console = Console()


@app.command("seed")
def seed_database(
    include_users: bool = typer.Option(
        True, "--users/--no-users", help="Seed sample users"
    ),
    include_roles: bool = typer.Option(
        True, "--roles/--no-roles", help="Seed default roles"
    ),
    include_tenants: bool = typer.Option(
        True, "--tenants/--no-tenants", help="Seed sample tenants"
    ),
    clear_existing: bool = typer.Option(
        False, "--clear", "-c", help="Clear existing data first"
    ),
) -> None:
    """
    Seed the database with sample data.

    Example:
        cli db seed --users --roles
        cli db seed --clear  # Clear and reseed
    """
    if clear_existing:
        if not confirm_action("This will delete existing data. Continue?"):
            raise typer.Exit(0)

    asyncio.run(
        _seed_database(include_users, include_roles, include_tenants, clear_existing)
    )


async def _seed_database(
    include_users: bool,
    include_roles: bool,
    include_tenants: bool,
    clear_existing: bool,
) -> None:
    """Async implementation of seed command."""

    from app.domain.entities.role import Permission, Role
    from app.domain.entities.tenant import Tenant
    from app.domain.entities.user import User
    from app.domain.value_objects.email import Email
    from app.infrastructure.auth.jwt_handler import hash_password
    from app.infrastructure.database.connection import async_session_maker
    from app.infrastructure.database.repositories.role_repository import (
        SQLAlchemyRoleRepository,
    )
    from app.infrastructure.database.repositories.tenant_repository import (
        SQLAlchemyTenantRepository,
    )
    from app.infrastructure.database.repositories.user_repository import (
        SQLAlchemyUserRepository,
    )

    console.print("\n[bold]Seeding database...[/bold]\n")

    async with async_session_maker() as session:
        tenant_repo = SQLAlchemyTenantRepository(session)
        role_repo = SQLAlchemyRoleRepository(session)
        user_repo = SQLAlchemyUserRepository(session)

        created_counts = {"tenants": 0, "roles": 0, "users": 0}

        # 1. Seed Tenants
        if include_tenants:
            console.print("[cyan]Creating tenants...[/cyan]")

            sample_tenants = [
                Tenant(name="Acme Corporation", slug="acme", is_active=True),
                Tenant(name="TechStart Inc", slug="techstart", is_active=True),
                Tenant(name="Demo Company", slug="demo", is_active=True),
            ]

            for tenant in sample_tenants:
                try:
                    existing = await tenant_repo.get_by_slug(tenant.slug)
                    if not existing:
                        await tenant_repo.create(tenant)
                        created_counts["tenants"] += 1
                        console.print(f"  ✓ Created tenant: {tenant.name}")
                    else:
                        console.print(f"  - Skipped (exists): {tenant.name}")
                except Exception as exc:
                    logger.error(
                        "seed_tenant_failed",
                        tenant=tenant.name,
                        error=type(exc).__name__,
                    )
                    console.print(
                        f"  [red]✗ Failed to create tenant: {tenant.name}[/red]"
                    )

        # Get first tenant for roles (roles are tenant-scoped)
        tenants = await tenant_repo.list(limit=1)
        first_tenant_id = tenants[0].id if tenants else None

        if not first_tenant_id and (include_roles or include_users):
            console.print("  [yellow]No tenant found, creating default...[/yellow]")
            from app.cli.utils import get_or_create_default_tenant

            first_tenant_id = await get_or_create_default_tenant()

        # 2. Seed Roles
        if include_roles:
            console.print("\n[cyan]Creating roles...[/cyan]")

            sample_roles = [
                {
                    "name": "Administrator",
                    "description": "Full system access",
                    "permissions": ["*:*"],  # All permissions
                    "is_system": True,
                },
                {
                    "name": "Manager",
                    "description": "Team management access",
                    "permissions": [
                        "users:read",
                        "users:update",
                        "reports:read",
                        "reports:create",
                    ],
                    "is_system": True,
                },
                {
                    "name": "User",
                    "description": "Standard user access",
                    "permissions": [
                        "profile:read",
                        "profile:update",
                    ],
                    "is_system": True,
                },
                {
                    "name": "Viewer",
                    "description": "Read-only access",
                    "permissions": [
                        "dashboard:read",
                    ],
                    "is_system": True,
                },
            ]

            for role_data in sample_roles:
                try:
                    existing = await role_repo.get_by_name(
                        role_data["name"], first_tenant_id
                    )
                    if not existing:
                        role = Role(
                            tenant_id=first_tenant_id,
                            name=role_data["name"],
                            description=role_data["description"],
                            permissions=[
                                Permission.from_string(p)
                                for p in role_data["permissions"]
                            ],
                            is_system=role_data["is_system"],
                        )
                        await role_repo.create(role)
                        created_counts["roles"] += 1
                        console.print(f"  ✓ Created role: {role.name}")
                    else:
                        console.print(f"  - Skipped (exists): {role_data['name']}")
                except Exception as exc:
                    logger.error(
                        "seed_role_failed",
                        role=role_data["name"],
                        error=type(exc).__name__,
                    )
                    console.print(
                        f"  [red]✗ Failed to create role: {role_data['name']}[/red]"
                    )

        # 3. Seed Users
        if include_users:
            console.print("\n[cyan]Creating sample users...[/cyan]")

            # Use first_tenant_id from above
            tenant_id = first_tenant_id

            sample_users = [
                {
                    "email": "demo@example.com",
                    "password": "Demo123!@#",
                    "first_name": "Demo",
                    "last_name": "User",
                    "is_superuser": False,
                },
                {
                    "email": "manager@example.com",
                    "password": "Manager123!@#",
                    "first_name": "Jane",
                    "last_name": "Manager",
                    "is_superuser": False,
                },
                {
                    "email": "viewer@example.com",
                    "password": "Viewer123!@#",
                    "first_name": "John",
                    "last_name": "Viewer",
                    "is_superuser": False,
                },
            ]

            for user_data in sample_users:
                try:
                    existing = await user_repo.get_by_email(user_data["email"])
                    if not existing:
                        user = User(
                            email=Email(user_data["email"]),
                            password_hash=hash_password(user_data["password"]),
                            first_name=user_data["first_name"],
                            last_name=user_data["last_name"],
                            is_active=True,
                            is_superuser=user_data["is_superuser"],
                            tenant_id=tenant_id,
                        )
                        await user_repo.create(user)
                        created_counts["users"] += 1
                        console.print("  ✓ Created a sample user")
                    else:
                        console.print(f"  - Skipped (exists): {user_data['email']}")
                except Exception as exc:
                    logger.error(
                        "seed_user_failed",
                        email=user_data["email"],
                        error=type(exc).__name__,
                    )
                    console.print(
                        f"  [red]✗ Failed to create user: {user_data['email']}[/red]"
                    )

        await session.commit()

        # Summary
        console.print("\n[bold green]✓ Seeding complete![/bold green]")
        console.print(f"  Tenants created: {created_counts['tenants']}")
        console.print(f"  Roles created: {created_counts['roles']}")
        console.print(f"  Users created: {created_counts['users']}")


@app.command("info")
def database_info() -> None:
    """
    Show database connection information.

    Example:
        cli db info
    """
    asyncio.run(_database_info())


async def _database_info() -> None:
    """Async implementation of info command."""
    from sqlalchemy import text

    from app.config import settings
    from app.infrastructure.database.connection import async_session_maker

    console.print("\n[bold]Database Information[/bold]\n")

    # Connection info (masked)
    db_url = str(settings.DATABASE_URL)
    try:
        from urllib.parse import urlparse

        parsed = urlparse(db_url)
        masked_url = db_url.replace(
            f"{parsed.username or ''}:{parsed.password or ''}@",
            "***:***@",
        )
    except Exception:
        masked_url = "<unable to parse>"
    console.print(f"Connection: {masked_url}")
    console.print(f"Pool Size: {settings.DB_POOL_SIZE}")
    console.print(f"Max Overflow: {settings.DB_MAX_OVERFLOW}")

    try:
        async with async_session_maker() as session:
            # PostgreSQL version
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            console.print(f"Server: {version}")

            # Database size
            result = await session.execute(
                text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            )
            size = result.scalar()
            console.print(f"Database Size: {size}")

            # Table count
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """)
            )
            table_count = result.scalar()
            console.print(f"Tables: {table_count}")

            console.print("\n[green]✓ Database connection successful[/green]")

    except Exception:
        console.print("\n[red]✗ Database connection failed (check DATABASE_URL)[/red]")
        raise typer.Exit(1) from None


@app.command("migrate")
def run_migrations(
    revision: str = typer.Option("head", "--revision", "-r", help="Target revision"),
) -> None:
    """
    Run database migrations using Alembic.

    Example:
        cli db migrate
        cli db migrate --revision abc123
    """
    import re
    import subprocess

    if not re.match(r"^[a-zA-Z0-9_]+$", revision):
        console.print("[red]Invalid revision format[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Running migrations to revision: {revision}[/cyan]")

    try:
        result = subprocess.run(
            ["alembic", "upgrade", revision],
            capture_output=True,
            text=True,
            check=True,
        )
        console.print(result.stdout)
        console.print("[green]✓ Migrations complete[/green]")
    except subprocess.CalledProcessError as e:
        console.print("[red]Migration failed (check alembic logs)[/red]")
        logger.error("migration_failed", stderr=e.stderr)
        raise typer.Exit(1) from None


@app.command("reset")
def reset_database(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """
    Reset the database (DEVELOPMENT ONLY).

    This will drop all tables and re-run migrations.

    Example:
        cli db reset --force
    """
    from app.config import settings

    if settings.ENVIRONMENT in ("production", "staging"):
        console.print("[red]Cannot reset database in production or staging![/red]")
        raise typer.Exit(1)

    if not force and not confirm_action("This will DELETE all data. Are you sure?"):
        raise typer.Exit(0)

    asyncio.run(_reset_database())


async def _reset_database() -> None:
    """Async implementation of reset command."""
    from sqlalchemy import text

    from app.config import settings as app_settings
    from app.infrastructure.database.connection import engine

    # Defense-in-depth: independent environment guard
    if app_settings.ENVIRONMENT in ("production", "staging"):
        console.print("[red]Cannot reset database in production or staging![/red]")
        raise typer.Exit(1)

    logger.warning("database_reset_initiated", environment=app_settings.ENVIRONMENT)
    console.print("[yellow]Resetting database...[/yellow]")

    try:
        # Drop all tables
        console.print("  Dropping all tables...")
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))

        # Run migrations (async subprocess to avoid blocking event loop)
        console.print("  Running migrations...")
        process = await asyncio.create_subprocess_exec(
            "alembic",
            "upgrade",
            "head",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(
                "migration_failed_during_reset",
                stderr=stderr.decode() if stderr else "",
            )
            console.print("[red]Migration failed (check logs)[/red]")
            raise typer.Exit(1)

        console.print("[green]✓ Database reset complete[/green]")

    except typer.Exit:
        raise
    except Exception:
        console.print("[red]Reset failed (check logs)[/red]")
        logger.error("database_reset_failed", exc_info=True)
        raise typer.Exit(1) from None
