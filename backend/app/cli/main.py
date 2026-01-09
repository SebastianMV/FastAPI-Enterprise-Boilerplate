# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
CLI application entry point.

Provides administrative commands for:
- User management (create-superuser)
- Database operations (seed-db, migrate)
- API key generation
- Health checks
"""

import typer

from app.cli.commands import users, database, apikeys

app = typer.Typer(
    name="boilerplate",
    help="FastAPI Enterprise Boilerplate CLI",
    add_completion=True,
    no_args_is_help=True,
)

# Register command groups
app.add_typer(users.app, name="users", help="User management commands")
app.add_typer(database.app, name="db", help="Database management commands")
app.add_typer(apikeys.app, name="apikeys", help="API key management commands")


@app.command()
def version() -> None:
    """Show the application version."""
    from app.config import settings
    
    typer.echo(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    typer.echo(f"Environment: {settings.ENVIRONMENT}")


@app.command()
def health() -> None:
    """Check application health status."""
    import asyncio
    from app.cli.utils import check_database, check_redis
    
    typer.echo("Checking application health...\n")
    
    # Database check
    db_ok = asyncio.run(check_database())
    db_status = "[green]✓[/green]" if db_ok else "[red]✗[/red]"
    typer.echo(f"Database: {'Connected' if db_ok else 'Failed'}")
    
    # Redis check
    redis_ok = asyncio.run(check_redis())
    redis_status = "[green]✓[/green]" if redis_ok else "[red]✗[/red]"
    typer.echo(f"Redis: {'Connected' if redis_ok else 'Failed'}")
    
    # Overall status
    if db_ok and redis_ok:
        typer.echo("\n[green]All systems operational[/green]")
        raise typer.Exit(0)
    else:
        typer.echo("\n[red]Some systems are not operational[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
