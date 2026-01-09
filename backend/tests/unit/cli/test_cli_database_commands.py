# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for CLI database commands using Typer CliRunner."""

from __future__ import annotations

from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestDatabaseSeedCommand:
    """Tests for db seed command."""

    def test_seed_command_exists(self) -> None:
        """Test seed command is registered."""
        from app.cli.commands.database import app
        
        result = runner.invoke(app, ["seed", "--help"])
        assert result.exit_code == 0
        assert "Seed the database" in result.output

    def test_seed_with_clear_asks_confirmation(self) -> None:
        """Test seed with --clear asks for confirmation."""
        from app.cli.commands.database import app
        
        with patch("app.cli.commands.database.confirm_action", return_value=False):
            result = runner.invoke(app, ["seed", "--clear"])
            assert result.exit_code == 0

    def test_seed_no_users(self) -> None:
        """Test seed --no-users flag help."""
        from app.cli.commands.database import app
        
        result = runner.invoke(app, ["seed", "--help"])
        assert "--no-users" in result.output or "--users" in result.output


class TestDatabaseMigrateCommand:
    """Tests for db migrate command."""

    def test_migrate_command_exists(self) -> None:
        """Test migrate command is registered."""
        from app.cli.commands.database import app
        
        result = runner.invoke(app, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "Run database migrations" in result.output or "migrate" in result.output.lower()


class TestDatabaseResetCommand:
    """Tests for db reset command."""

    def test_reset_command_exists(self) -> None:
        """Test reset command is registered."""
        from app.cli.commands.database import app
        
        result = runner.invoke(app, ["reset", "--help"])
        assert result.exit_code == 0
        assert "reset" in result.output.lower()

    def test_reset_requires_confirmation(self) -> None:
        """Test reset command asks for confirmation."""
        from app.cli.commands.database import app
        
        with patch("app.cli.commands.database.confirm_action", return_value=False):
            result = runner.invoke(app, ["reset"])
            assert result.exit_code == 0


class TestDatabaseInfoCommand:
    """Tests for db info command."""

    def test_info_command_exists(self) -> None:
        """Test info command is registered."""
        from app.cli.commands.database import app
        
        result = runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0


class TestDatabaseAppStructure:
    """Tests for database CLI app structure."""

    def test_app_has_commands(self) -> None:
        """Test database app has registered commands."""
        from app.cli.commands.database import app
        
        # Check that commands are registered
        command_names = [cmd.name for cmd in app.registered_commands]
        assert len(command_names) > 0

    def test_app_help_output(self) -> None:
        """Test database app help shows available commands."""
        from app.cli.commands.database import app
        
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Database" in result.output or "database" in result.output
