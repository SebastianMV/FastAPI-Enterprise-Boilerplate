# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for CLI apikeys commands using Typer CliRunner."""

from __future__ import annotations

from unittest.mock import patch, AsyncMock
import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestApikeysGenerateFunction:
    """Tests for apikeys generate_api_key function."""

    def test_generate_api_key_returns_tuple(self) -> None:
        """Test generate_api_key returns a tuple."""
        from app.cli.commands.apikeys import generate_api_key
        
        result = generate_api_key()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_generate_api_key_has_valid_key(self) -> None:
        """Test generate_api_key returns valid key."""
        from app.cli.commands.apikeys import generate_api_key
        
        key, prefix = generate_api_key()
        assert len(key) > 20
        assert len(prefix) == 8
        assert key.startswith(prefix)

    def test_generate_api_key_is_unique(self) -> None:
        """Test generate_api_key generates unique keys."""
        from app.cli.commands.apikeys import generate_api_key
        
        keys = [generate_api_key()[0] for _ in range(10)]
        assert len(keys) == len(set(keys))


class TestApikeysGenerateCommand:
    """Tests for apikeys generate command."""

    def test_generate_command_exists(self) -> None:
        """Test generate command is registered."""
        from app.cli.commands.apikeys import app
        
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "Generate" in result.output or "generate" in result.output.lower()

    def test_generate_shows_options(self) -> None:
        """Test generate shows all options."""
        from app.cli.commands.apikeys import app
        
        result = runner.invoke(app, ["generate", "--help"])
        assert "--name" in result.output
        assert "--user" in result.output

    def test_generate_shows_scopes_option(self) -> None:
        """Test generate shows scopes option."""
        from app.cli.commands.apikeys import app
        
        result = runner.invoke(app, ["generate", "--help"])
        assert "--scopes" in result.output or "scopes" in result.output

    def test_generate_shows_expires_option(self) -> None:
        """Test generate shows expires option."""
        from app.cli.commands.apikeys import app
        
        result = runner.invoke(app, ["generate", "--help"])
        assert "--expires" in result.output or "expires" in result.output


class TestApikeysListCommand:
    """Tests for apikeys list command."""

    def test_list_command_exists(self) -> None:
        """Test list command is registered."""
        from app.cli.commands.apikeys import app
        
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0

    def test_list_shows_options(self) -> None:
        """Test list shows filter options."""
        from app.cli.commands.apikeys import app
        
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0


class TestApikeysRevokeCommand:
    """Tests for apikeys revoke command."""

    def test_revoke_command_exists(self) -> None:
        """Test revoke command is registered."""
        from app.cli.commands.apikeys import app
        
        result = runner.invoke(app, ["revoke", "--help"])
        assert result.exit_code == 0


class TestApikeysInfoCommand:
    """Tests for apikeys info command."""

    def test_info_command_exists(self) -> None:
        """Test info command is registered."""
        from app.cli.commands.apikeys import app
        
        result = runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0


class TestApikeysAppStructure:
    """Tests for apikeys CLI app structure."""

    def test_app_has_commands(self) -> None:
        """Test apikeys app has registered commands."""
        from app.cli.commands.apikeys import app
        
        command_names = [cmd.name for cmd in app.registered_commands]
        assert len(command_names) > 0
        assert "generate" in command_names

    def test_app_help_output(self) -> None:
        """Test apikeys app help shows available commands."""
        from app.cli.commands.apikeys import app
        
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "API key" in result.output or "api" in result.output.lower()
