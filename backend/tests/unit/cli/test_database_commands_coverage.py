# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Complete unit tests for database CLI commands to achieve 90%+ coverage.
All patches use correct module paths (imports happen inside functions).
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import typer

from app.cli.commands.database import (
    _database_info,
    _reset_database,
    _seed_database,
    database_info,
    reset_database,
    run_migrations,
    seed_database,
)


class TestSeedDatabaseCommand:
    """Tests for seed_database command and _seed_database async function."""

    def test_seed_database_calls_async_implementation(self):
        """Test that seed_database calls asyncio.run with correct parameters."""
        with patch("asyncio.run") as mock_run:
            seed_database(
                include_users=True,
                include_roles=True,
                include_tenants=True,
                clear_existing=False,
            )

            mock_run.assert_called_once()

    def test_seed_database_with_clear_prompts_confirmation(self):
        """Test that clear_existing prompts for confirmation."""
        with patch("typer.prompt", return_value="n"):
            with pytest.raises(typer.Exit) as exc_info:
                seed_database(clear_existing=True)

            assert exc_info.value.exit_code == 0

    def test_seed_database_with_clear_confirmed(self):
        """Test seed_database proceeds when confirmation is given."""
        with patch("typer.prompt", return_value="y"), patch("asyncio.run") as mock_run:
            seed_database(clear_existing=True)
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_database_creates_tenants(self):
        """Test _seed_database creates sample tenants."""
        mock_session = AsyncMock()
        mock_tenant_repo = AsyncMock()
        mock_role_repo = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_tenant_repo.get_by_slug.return_value = None
        mock_tenant_repo.list.return_value = []

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository",
                return_value=mock_tenant_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.role_repository.SQLAlchemyRoleRepository",
                return_value=mock_role_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.utils.get_or_create_default_tenant", return_value=uuid4()),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None

            await _seed_database(
                include_users=False,
                include_roles=False,
                include_tenants=True,
                clear_existing=False,
            )

            assert mock_tenant_repo.create.call_count == 3

    @pytest.mark.asyncio
    async def test_seed_database_creates_roles(self):
        """Test _seed_database creates sample roles."""
        mock_session = AsyncMock()
        mock_tenant_repo = AsyncMock()
        mock_role_repo = AsyncMock()
        mock_user_repo = AsyncMock()

        tenant_id = uuid4()
        mock_tenant = MagicMock(id=tenant_id)
        mock_tenant_repo.list.return_value = [mock_tenant]
        mock_role_repo.get_by_name.return_value = None

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository",
                return_value=mock_tenant_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.role_repository.SQLAlchemyRoleRepository",
                return_value=mock_role_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None

            await _seed_database(
                include_users=False,
                include_roles=True,
                include_tenants=False,
                clear_existing=False,
            )

            assert mock_role_repo.create.call_count == 4

    @pytest.mark.asyncio
    async def test_seed_database_creates_users(self):
        """Test _seed_database creates sample users."""
        mock_session = AsyncMock()
        mock_tenant_repo = AsyncMock()
        mock_role_repo = AsyncMock()
        mock_user_repo = AsyncMock()

        tenant_id = uuid4()
        mock_tenant = MagicMock(id=tenant_id)
        mock_tenant_repo.list.return_value = [mock_tenant]
        mock_user_repo.get_by_email.return_value = None

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository",
                return_value=mock_tenant_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.role_repository.SQLAlchemyRoleRepository",
                return_value=mock_role_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "app.infrastructure.auth.jwt_handler.hash_password",
                return_value="hashed",
            ),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None

            await _seed_database(
                include_users=True,
                include_roles=False,
                include_tenants=False,
                clear_existing=False,
            )

            assert mock_user_repo.create.call_count == 3

    @pytest.mark.asyncio
    async def test_seed_database_skips_existing_tenants(self):
        """Test _seed_database skips tenants that already exist."""
        mock_session = AsyncMock()
        mock_tenant_repo = AsyncMock()
        mock_role_repo = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_tenant_repo.get_by_slug.return_value = MagicMock()

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository",
                return_value=mock_tenant_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.role_repository.SQLAlchemyRoleRepository",
                return_value=mock_role_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None

            await _seed_database(
                include_users=False,
                include_roles=False,
                include_tenants=True,
                clear_existing=False,
            )

            mock_tenant_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_database_handles_tenant_creation_error(self):
        """Test _seed_database handles errors during tenant creation."""
        mock_session = AsyncMock()
        mock_tenant_repo = AsyncMock()
        mock_role_repo = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_tenant_repo.get_by_slug.return_value = None
        mock_tenant_repo.create.side_effect = [None, Exception("DB Error"), None]
        mock_tenant_repo.list.return_value = []

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository",
                return_value=mock_tenant_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.role_repository.SQLAlchemyRoleRepository",
                return_value=mock_role_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.utils.get_or_create_default_tenant", return_value=uuid4()),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None

            await _seed_database(
                include_users=False,
                include_roles=False,
                include_tenants=True,
                clear_existing=False,
            )

            assert mock_tenant_repo.create.call_count == 3

    @pytest.mark.asyncio
    async def test_seed_database_creates_default_tenant_when_needed(self):
        """Test _seed_database creates default tenant for roles/users."""
        mock_session = AsyncMock()
        mock_tenant_repo = AsyncMock()
        mock_role_repo = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_tenant_repo.list.return_value = []
        mock_role_repo.get_by_name.return_value = None
        default_tenant_id = uuid4()

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository",
                return_value=mock_tenant_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.role_repository.SQLAlchemyRoleRepository",
                return_value=mock_role_repo,
            ),
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "app.cli.utils.get_or_create_default_tenant",
                return_value=default_tenant_id,
            ) as mock_default,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None

            await _seed_database(
                include_users=False,
                include_roles=True,
                include_tenants=False,
                clear_existing=False,
            )

            mock_default.assert_called_once()


class TestDatabaseInfoCommand:
    """Tests for database_info command and _database_info async function."""

    def test_database_info_calls_async_implementation(self):
        """Test that database_info calls asyncio.run."""
        with patch("asyncio.run") as mock_run:
            database_info()
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_info_displays_connection_info(self):
        """Test _database_info displays database connection information."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.side_effect = ["PostgreSQL 17.2", "42 MB", 15]
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.config.settings") as mock_settings,
        ):
            mock_settings.DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"
            mock_settings.DB_POOL_SIZE = 10
            mock_settings.DB_MAX_OVERFLOW = 20

            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None

            await _database_info()

            assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_database_info_handles_connection_error(self):
        """Test _database_info handles database connection errors."""
        with patch(
            "app.infrastructure.database.connection.async_session_maker"
        ) as mock_maker:
            mock_maker.return_value.__aenter__.side_effect = Exception(
                "Connection failed"
            )

            with pytest.raises(typer.Exit) as exc_info:
                await _database_info()

            assert exc_info.value.exit_code == 1


class TestRunMigrationsCommand:
    """Tests for run_migrations command."""

    def test_run_migrations_default_revision(self):
        """Test run_migrations with default revision (head)."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Done!", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            run_migrations(
                revision="head"
            )  # Explicitly pass head instead of using default

    def test_run_migrations_custom_revision(self):
        """Test run_migrations with custom revision."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Done!", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            run_migrations(revision="abc123")

    def test_run_migrations_handles_subprocess_error(self):
        """Test run_migrations handles subprocess errors."""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Migration failed"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(typer.Exit) as exc_info:
                run_migrations(revision="head")

            assert exc_info.value.exit_code == 1


class TestResetDatabaseCommand:
    """Tests for reset_database command and _reset_database async function."""

    def test_reset_database_blocks_in_production(self):
        """Test reset_database blocks execution in production environment."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"

            with pytest.raises(typer.Exit) as exc_info:
                reset_database()

            assert exc_info.value.exit_code == 1

    def test_reset_database_prompts_confirmation_when_not_forced(self):
        """Test reset_database prompts for confirmation without --force."""
        with (
            patch("app.config.settings") as mock_settings,
            patch("typer.prompt", return_value="n"),
        ):
            mock_settings.ENVIRONMENT = "development"

            with pytest.raises(typer.Exit) as exc_info:
                reset_database(force=False)

            assert exc_info.value.exit_code == 0

    def test_reset_database_proceeds_with_force(self):
        """Test reset_database proceeds without confirmation with --force."""
        with (
            patch("app.config.settings") as mock_settings,
            patch("asyncio.run") as mock_run,
        ):
            mock_settings.ENVIRONMENT = "development"

            reset_database(force=True)

            mock_run.assert_called_once()

    def test_reset_database_proceeds_with_confirmation(self):
        """Test reset_database proceeds when user confirms."""
        with (
            patch("app.config.settings") as mock_settings,
            patch("typer.prompt", return_value="y"),
            patch("asyncio.run") as mock_run,
        ):
            mock_settings.ENVIRONMENT = "development"

            reset_database(force=False)

            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_database_drops_and_recreates_schema(self):
        """Test _reset_database drops schema and runs migrations."""
        mock_conn = AsyncMock()
        mock_begin_ctx = AsyncMock()
        mock_begin_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_begin_ctx.__aexit__ = AsyncMock(return_value=None)

        # Mock async subprocess for alembic migration
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("app.infrastructure.database.connection.engine") as mock_engine,
            patch(
                "asyncio.create_subprocess_exec", return_value=mock_process
            ) as mock_subprocess,
            patch("app.config.settings") as mock_settings,
        ):
            mock_engine.begin.return_value = mock_begin_ctx
            mock_settings.ENVIRONMENT = "development"

            await _reset_database()

            assert mock_conn.execute.call_count == 3
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_database_handles_error(self):
        """Test _reset_database handles errors during reset."""
        with patch("app.infrastructure.database.connection.engine") as mock_engine:
            mock_engine.begin.side_effect = Exception("Database error")

            with pytest.raises(typer.Exit) as exc_info:
                await _reset_database()

            assert exc_info.value.exit_code == 1
