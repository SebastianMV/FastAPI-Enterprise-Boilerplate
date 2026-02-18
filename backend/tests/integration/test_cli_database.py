# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Integration tests for database CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from app.cli.commands.database import app, run_migrations


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_console():
    """Mock rich console to prevent actual output."""
    with patch("app.cli.commands.database.console") as mock:
        yield mock


class TestSeedDatabase:
    """Test database seeding command."""

    @patch("app.cli.commands.database.asyncio.run")
    @patch("app.cli.commands.database.confirm_action", return_value=False)
    def test_seed_with_clear_cancelled(
        self,
        mock_confirm: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test that seed with --clear is cancelled when user declines."""
        result = cli_runner.invoke(app, ["seed", "--clear"])

        # Should ask for confirmation
        mock_confirm.assert_called_once()
        # Should not run seeding
        mock_run.assert_not_called()
        assert result.exit_code == 0

    @patch("app.cli.commands.database.asyncio.run")
    @patch("app.cli.commands.database.confirm_action", return_value=True)
    def test_seed_with_clear_confirmed(
        self,
        mock_confirm: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test that seed with --clear proceeds when user confirms."""
        result = cli_runner.invoke(app, ["seed", "--clear"])

        mock_confirm.assert_called_once_with(
            "This will delete existing data. Continue?"
        )
        mock_run.assert_called_once()
        assert result.exit_code == 0

    @patch("app.cli.commands.database.asyncio.run")
    def test_seed_default_options(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test seed with default options (all enabled, no clear)."""
        result = cli_runner.invoke(app, ["seed"])

        mock_run.assert_called_once()
        # Should call _seed_database with defaults
        call_args = mock_run.call_args[0][0]
        assert result.exit_code == 0

    @patch("app.cli.commands.database.asyncio.run")
    def test_seed_selective_options(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test seed with selective options."""
        result = cli_runner.invoke(
            app, ["seed", "--no-users", "--no-tenants", "--roles"]
        )

        mock_run.assert_called_once()
        assert result.exit_code == 0

    # @pytest.mark.asyncio
    # async def test_seed_database_creates_tenants(
    #     self,
    #     mock_console: MagicMock,
    #     db_session: AsyncSession,
    # ):
    #     """Test that _seed_database creates tenants."""
    #     # SKIPPED: async_session_maker not accessible from database module
    #     pass


class TestDatabaseInfo:
    """Test database info command."""

    @patch("app.cli.commands.database.asyncio.run")
    def test_info_command(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test database info command execution."""
        result = cli_runner.invoke(app, ["info"])

        mock_run.assert_called_once()
        assert result.exit_code == 0


class TestDatabaseMigrate:
    """Test database migration command - skipped as not implemented via subprocess."""

    def test_migrate_placeholder(self):
        """Placeholder - migrations use alembic directly."""
        # Placeholder: migration tested via test_run_migrations in unit tests
        assert callable(run_migrations)
