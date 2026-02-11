# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for users CLI commands.

Tests command line interface functionality.
"""

from unittest.mock import patch
from uuid import uuid4

from typer.testing import CliRunner

from app.cli.commands.users import app


class TestUserCommands:
    """Tests for user CLI commands."""

    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()

    @patch("app.cli.commands.users.asyncio.run")
    def test_create_superuser_basic(self, mock_run):
        """Test basic create-superuser command."""
        result = self.runner.invoke(
            app,
            [
                "create-superuser",
                "--email",
                "admin@example.com",
                "--password",
                "SecurePass123!",
                "--first-name",
                "Admin",
                "--last-name",
                "User",
            ],
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.users.asyncio.run")
    def test_create_superuser_default_names(self, mock_run):
        """Test create-superuser with default names."""
        result = self.runner.invoke(
            app,
            [
                "create-superuser",
                "--email",
                "admin@example.com",
                "--password",
                "SecurePass123!",
            ],
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.users.asyncio.run")
    def test_list_command_default(self, mock_run):
        """Test list command with defaults."""
        result = self.runner.invoke(app, ["list"])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.users.asyncio.run")
    def test_list_with_limit(self, mock_run):
        """Test list with custom limit."""
        result = self.runner.invoke(app, ["list", "--limit", "20"])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.users.asyncio.run")
    def test_list_active_only(self, mock_run):
        """Test list active users only."""
        result = self.runner.invoke(app, ["list", "--active"])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.users.asyncio.run")
    @patch("app.cli.commands.users.format_uuid")
    def test_activate_user(self, mock_format_uuid, mock_run):
        """Test activate user command."""
        user_id = uuid4()
        mock_format_uuid.return_value = user_id

        result = self.runner.invoke(app, ["activate", str(user_id)])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.users.format_uuid", return_value=None)
    def test_activate_invalid_uuid(self, mock_format_uuid):
        """Test activate with invalid UUID."""
        result = self.runner.invoke(app, ["activate", "invalid-uuid"])

        assert result.exit_code == 1

    @patch("app.cli.commands.users.asyncio.run")
    @patch("app.cli.commands.users.format_uuid")
    def test_deactivate_user(self, mock_format_uuid, mock_run):
        """Test deactivate user command."""
        user_id = uuid4()
        mock_format_uuid.return_value = user_id

        result = self.runner.invoke(app, ["deactivate", str(user_id)])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.users.format_uuid", return_value=None)
    def test_deactivate_invalid_uuid(self, mock_format_uuid):
        """Test deactivate with invalid UUID."""
        result = self.runner.invoke(app, ["deactivate", "invalid-uuid"])

        assert result.exit_code == 1
