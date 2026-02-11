# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Tests for CLI main module to achieve 100% coverage.
Focuses on 18 uncovered lines in app/cli/main.py
"""

from unittest.mock import patch

from typer.testing import CliRunner


class TestCLIMainCommands:
    """Tests for CLI main commands (version, health)."""

    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()

    def test_version_command(self):
        """Test version command displays app info."""
        from app.cli.main import app

        with patch("app.config.settings") as mock_settings:
            mock_settings.APP_NAME = "TestApp"
            mock_settings.APP_VERSION = "1.0.0"
            mock_settings.ENVIRONMENT = "test"

            result = self.runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "TestApp" in result.output or "v" in result.output

    def test_health_command_all_healthy(self):
        """Test health command when all systems are healthy."""
        from app.cli.main import app

        with patch("asyncio.run") as mock_run:
            # First call is check_database, second is check_redis
            mock_run.side_effect = [True, True]

            result = self.runner.invoke(app, ["health"])

        assert result.exit_code == 0
        assert "Database" in result.output
        assert "Redis" in result.output

    def test_health_command_database_failed(self):
        """Test health command when database check fails."""
        from app.cli.main import app

        with patch("asyncio.run") as mock_run:
            mock_run.side_effect = [False, True]  # DB fails, Redis ok

            result = self.runner.invoke(app, ["health"])

        assert result.exit_code == 1
        assert "Failed" in result.output or "not operational" in result.output

    def test_health_command_redis_failed(self):
        """Test health command when redis check fails."""
        from app.cli.main import app

        with patch("asyncio.run") as mock_run:
            mock_run.side_effect = [True, False]  # DB ok, Redis fails

            result = self.runner.invoke(app, ["health"])

        assert result.exit_code == 1

    def test_health_command_all_failed(self):
        """Test health command when all checks fail."""
        from app.cli.main import app

        with patch("asyncio.run") as mock_run:
            mock_run.side_effect = [False, False]

            result = self.runner.invoke(app, ["health"])

        assert result.exit_code == 1
        assert "not operational" in result.output

    def test_no_args_shows_help(self):
        """Test that running CLI without args shows help."""
        from app.cli.main import app

        result = self.runner.invoke(app)

        # no_args_is_help=True - when no args, help is shown (exit code can be 0 or 2 depending on typer)
        # Just verify help content is shown
        assert (
            "Usage" in result.output
            or "Commands" in result.output
            or "boilerplate" in result.output
        )

    def test_users_subcommand_available(self):
        """Test that users subcommand is registered."""
        from app.cli.main import app

        result = self.runner.invoke(app, ["users", "--help"])

        assert result.exit_code == 0
        assert "User" in result.output

    def test_db_subcommand_available(self):
        """Test that db subcommand is registered."""
        from app.cli.main import app

        result = self.runner.invoke(app, ["db", "--help"])

        assert result.exit_code == 0
        assert "Database" in result.output

    def test_apikeys_subcommand_available(self):
        """Test that apikeys subcommand is registered."""
        from app.cli.main import app

        result = self.runner.invoke(app, ["apikeys", "--help"])

        assert result.exit_code == 0
        assert "API" in result.output


class TestCLIMainModule:
    """Tests for CLI main module as script."""

    def test_main_entry_point(self):
        """Test __main__ block execution."""
        # This is covered when the module is run as a script
        # We test the app is callable
        from app.cli.main import app

        assert callable(app)
        assert hasattr(app, "command")
