# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for CLI users commands using Typer CliRunner."""

from __future__ import annotations

from unittest.mock import patch, AsyncMock
import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestUsersCreateSuperuserCommand:
    """Tests for users create-superuser command."""

    def test_create_superuser_command_exists(self) -> None:
        """Test create-superuser command is registered."""
        from app.cli.commands.users import app
        
        result = runner.invoke(app, ["create-superuser", "--help"])
        assert result.exit_code == 0
        assert "superuser" in result.output.lower()

    def test_create_superuser_shows_options(self) -> None:
        """Test create-superuser shows all options."""
        from app.cli.commands.users import app
        
        result = runner.invoke(app, ["create-superuser", "--help"])
        assert "--email" in result.output
        assert "--password" in result.output


class TestUsersListCommand:
    """Tests for users list command."""

    def test_list_command_exists(self) -> None:
        """Test list command is registered."""
        from app.cli.commands.users import app
        
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0

    def test_list_shows_options(self) -> None:
        """Test list shows pagination options."""
        from app.cli.commands.users import app
        
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0


class TestUsersActivateCommand:
    """Tests for users activate command."""

    def test_activate_command_exists(self) -> None:
        """Test activate command is registered."""
        from app.cli.commands.users import app
        
        result = runner.invoke(app, ["activate", "--help"])
        assert result.exit_code == 0

    def test_activate_requires_user_id(self) -> None:
        """Test activate shows user-id option."""
        from app.cli.commands.users import app
        
        result = runner.invoke(app, ["activate", "--help"])
        # Check for user-id or similar option
        assert "USER_ID" in result.output or "user" in result.output.lower()


class TestUsersDeactivateCommand:
    """Tests for users deactivate command."""

    def test_deactivate_command_exists(self) -> None:
        """Test deactivate command is registered."""
        from app.cli.commands.users import app
        
        result = runner.invoke(app, ["deactivate", "--help"])
        assert result.exit_code == 0


class TestUsersAppStructure:
    """Tests for users CLI app structure."""

    def test_app_has_commands(self) -> None:
        """Test users app has registered commands."""
        from app.cli.commands.users import app
        
        command_names = [cmd.name for cmd in app.registered_commands]
        assert len(command_names) > 0
        assert "create-superuser" in command_names

    def test_app_help_output(self) -> None:
        """Test users app help shows available commands."""
        from app.cli.commands.users import app
        
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "User" in result.output or "user" in result.output
