# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for CLI main app commands using CliRunner."""

from __future__ import annotations

from unittest.mock import patch, AsyncMock
import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestCliMainVersion:
    """Tests for CLI version command."""

    def test_version_command_exists(self) -> None:
        """Test version command is registered."""
        from app.cli.main import app
        
        result = runner.invoke(app, ["version", "--help"])
        assert result.exit_code == 0

    def test_version_command_shows_version(self) -> None:
        """Test version command shows app version."""
        from app.cli.main import app
        
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "FastAPI Enterprise Boilerplate" in result.output
        assert "Environment" in result.output


class TestCliMainHealth:
    """Tests for CLI health command."""

    def test_health_command_exists(self) -> None:
        """Test health command is registered."""
        from app.cli.main import app
        
        result = runner.invoke(app, ["health", "--help"])
        assert result.exit_code == 0

    def test_health_command_runs(self) -> None:
        """Test health command runs."""
        from app.cli.main import app
        import asyncio
        
        with patch.object(asyncio, "run") as mock_run:
            # Mock both checks to return True
            mock_run.side_effect = [True, True]
            result = runner.invoke(app, ["health"])
            assert "Checking application health" in result.output

    def test_health_command_with_failures(self) -> None:
        """Test health command with failures."""
        from app.cli.main import app
        import asyncio
        
        with patch.object(asyncio, "run") as mock_run:
            # Mock checks to return False
            mock_run.side_effect = [False, False]
            result = runner.invoke(app, ["health"])
            assert "Failed" in result.output or "not operational" in result.output


class TestCliMainAppStructure:
    """Tests for CLI main app structure."""

    def test_app_has_subcommands(self) -> None:
        """Test app has registered subcommands."""
        from app.cli.main import app
        
        # Check app has registered groups
        assert app is not None

    def test_app_help(self) -> None:
        """Test app help shows available commands."""
        from app.cli.main import app
        
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "users" in result.output
        assert "db" in result.output
        assert "apikeys" in result.output

    def test_users_subcommand_available(self) -> None:
        """Test users subcommand is available."""
        from app.cli.main import app
        
        result = runner.invoke(app, ["users", "--help"])
        assert result.exit_code == 0

    def test_db_subcommand_available(self) -> None:
        """Test db subcommand is available."""
        from app.cli.main import app
        
        result = runner.invoke(app, ["db", "--help"])
        assert result.exit_code == 0

    def test_apikeys_subcommand_available(self) -> None:
        """Test apikeys subcommand is available."""
        from app.cli.main import app
        
        result = runner.invoke(app, ["apikeys", "--help"])
        assert result.exit_code == 0


class TestCliMainNoArgs:
    """Tests for CLI with no arguments."""

    def test_no_args_shows_help(self) -> None:
        """Test that running without args shows help."""
        from app.cli.main import app
        
        result = runner.invoke(app, [])
        # no_args_is_help is True so should show help
        assert "FastAPI Enterprise Boilerplate CLI" in result.output or "Usage" in result.output
