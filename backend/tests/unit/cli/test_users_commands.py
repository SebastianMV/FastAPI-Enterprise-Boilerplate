# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for CLI user commands."""

import pytest
from typer.testing import CliRunner

from app.cli.commands.users import app


runner = CliRunner()


class TestUserCommands:
    """Tests for user CLI commands."""

    def test_users_help(self):
        """Test users command help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "User management commands" in result.output

    def test_create_superuser_help(self):
        """Test create-superuser command help."""
        result = runner.invoke(app, ["create-superuser", "--help"])
        assert result.exit_code == 0
        assert "--email" in result.output
        assert "--password" in result.output
        assert "--first-name" in result.output
        assert "--last-name" in result.output

    def test_list_users_help(self):
        """Test list command help."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0

    def test_activate_help(self):
        """Test activate command help."""
        result = runner.invoke(app, ["activate", "--help"])
        assert result.exit_code == 0
        assert "--user-id" in result.output or "user_id" in result.output.lower()

    def test_deactivate_help(self):
        """Test deactivate command help."""
        result = runner.invoke(app, ["deactivate", "--help"])
        assert result.exit_code == 0
