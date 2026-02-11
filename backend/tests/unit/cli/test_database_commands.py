# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for database CLI commands.

Tests command line interface functionality.
"""

from unittest.mock import patch

from typer.testing import CliRunner

from app.cli.commands.database import app


class TestDatabaseCommands:
    """Tests for database CLI commands."""

    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()

    @patch("app.cli.commands.database.asyncio.run")
    @patch("app.cli.commands.database.confirm_action", return_value=True)
    def test_seed_with_clear_confirmed(self, mock_confirm, mock_run):
        """Test seed --clear with confirmation."""
        result = self.runner.invoke(app, ["seed", "--clear"])

        assert result.exit_code == 0
        mock_confirm.assert_called_once()
        mock_run.assert_called_once()

    @patch("app.cli.commands.database.confirm_action", return_value=False)
    def test_seed_with_clear_cancelled(self, mock_confirm):
        """Test seed --clear cancelled."""
        result = self.runner.invoke(app, ["seed", "--clear"])

        assert result.exit_code == 0
        mock_confirm.assert_called_once()

    @patch("app.cli.commands.database.asyncio.run")
    def test_seed_with_no_users(self, mock_run):
        """Test seed --no-users option."""
        result = self.runner.invoke(app, ["seed", "--no-users"])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.database.asyncio.run")
    def test_seed_with_no_roles(self, mock_run):
        """Test seed --no-roles option."""
        result = self.runner.invoke(app, ["seed", "--no-roles"])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.database.asyncio.run")
    def test_seed_with_no_tenants(self, mock_run):
        """Test seed --no-tenants option."""
        result = self.runner.invoke(app, ["seed", "--no-tenants"])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.database.asyncio.run")
    def test_seed_all_options_combined(self, mock_run):
        """Test seed with multiple flags."""
        result = self.runner.invoke(
            app, ["seed", "--no-users", "--no-roles", "--tenants"]
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()
