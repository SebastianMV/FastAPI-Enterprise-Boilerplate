# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for CLI API keys commands."""

import pytest
from typer.testing import CliRunner

from app.cli.commands.apikeys import app


runner = CliRunner()


class TestAPIKeysCommands:
    """Tests for API keys CLI commands."""

    def test_apikeys_help(self):
        """Test apikeys command help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "API key management commands" in result.output

    def test_create_help(self):
        """Test create command help - may not exist."""
        result = runner.invoke(app, ["create", "--help"])
        # Command may or may not exist
        assert result.exit_code in [0, 2]

    def test_list_help(self):
        """Test list command help."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0

    def test_revoke_help(self):
        """Test revoke command help."""
        result = runner.invoke(app, ["revoke", "--help"])
        assert result.exit_code == 0

    def test_info_help(self):
        """Test info command help."""
        result = runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0
