# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for API keys CLI commands.

Tests command line interface functionality.
"""

from unittest.mock import patch
from typer.testing import CliRunner

from app.cli.commands.apikeys import app, generate_api_key


class TestAPIKeyGeneration:
    """Tests for API key generation function."""

    def test_generate_api_key_format(self):
        """Test API key generation returns correct format."""
        plain_key, prefix = generate_api_key()
        
        assert isinstance(plain_key, str)
        assert isinstance(prefix, str)
        assert len(plain_key) > 32
        assert prefix == plain_key[:8]

    def test_generate_api_key_unique(self):
        """Test each generated key is unique."""
        key1, prefix1 = generate_api_key()
        key2, prefix2 = generate_api_key()
        
        assert key1 != key2
        assert prefix1 != prefix2


class TestAPIKeyCommands:
    """Tests for API key CLI commands."""

    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()

    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_generate_command_basic(self, mock_run):
        """Test basic generate command."""
        result = self.runner.invoke(app, [
            "generate",
            "--name", "Test Key",
            "--user", "test@example.com"
        ])
        
        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_generate_with_scopes(self, mock_run):
        """Test generate with scopes."""
        result = self.runner.invoke(app, [
            "generate",
            "--name", "Limited Key",
            "--user", "test@example.com",
            "--scopes", "users:read,reports:read"
        ])
        
        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_generate_with_expiration(self, mock_run):
        """Test generate with expiration."""
        result = self.runner.invoke(app, [
            "generate",
            "--name", "Temp Key",
            "--user", "test@example.com",
            "--expires", "30"
        ])
        
        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_list_command_default(self, mock_run):
        """Test list command."""
        result = self.runner.invoke(app, ["list"])
        
        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_list_with_user_filter(self, mock_run):
        """Test list filtered by user."""
        result = self.runner.invoke(app, [
            "list",
            "--user", "admin@example.com"
        ])
        
        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_list_include_inactive(self, mock_run):
        """Test list including inactive keys."""
        result = self.runner.invoke(app, [
            "list",
            "--inactive"
        ])
        
        assert result.exit_code == 0
        mock_run.assert_called_once()
