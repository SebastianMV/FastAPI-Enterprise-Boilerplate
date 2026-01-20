# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Integration tests for API key CLI commands."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from datetime import datetime, UTC
from uuid import uuid4

from app.cli.commands.apikeys import app, generate_api_key, _create_api_key


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_console():
    """Mock rich console to prevent actual output."""
    with patch("app.cli.commands.apikeys.console") as mock:
        yield mock


class TestGenerateAPIKey:
    """Test API key generation utility."""
    
    def test_generate_api_key_format(self):
        """Test that generated API keys have correct format."""
        key, prefix = generate_api_key()
        
        # Key should be URL-safe base64
        assert isinstance(key, str)
        assert len(key) > 0
        
        # Prefix should be first 8 chars of key
        assert prefix == key[:8]
        assert len(prefix) == 8
    
    def test_generate_api_key_uniqueness(self):
        """Test that generated keys are unique."""
        key1, _ = generate_api_key()
        key2, _ = generate_api_key()
        
        assert key1 != key2


class TestCreateAPIKeyCommand:
    """Test API key creation command."""
    
    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_create_with_all_options(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test creating API key with all options specified."""
        result = cli_runner.invoke(
            app,
            [
                "generate",
                "--name", "Test Key",
                "--user", "admin@example.com",
                "--scopes", "users:read,users:write",
                "--expires", "30",
            ],
        )
        
        mock_run.assert_called_once()
        assert result.exit_code == 0
    
    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_create_minimal(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test creating API key with minimal options (will prompt)."""
        result = cli_runner.invoke(
            app,
            ["generate"],
            input="Test Key\nadmin@example.com\n",
        )
        
        mock_run.assert_called_once()
        assert result.exit_code == 0
    
    @pytest.mark.asyncio
    async def test_create_api_key_user_not_found(
        self,
        mock_console: MagicMock,
        db_session,
    ):
        """Test that creation fails when user doesn't exist."""
        with patch("app.cli.commands.apikeys.async_session_maker") as mock_maker:
            mock_maker.return_value.__aenter__.return_value = db_session
            
            await _create_api_key(
                name="Test Key",
                user_email="nonexistent@example.com",
                scopes=[],
                expires_days=None,
            )
            
            # Should print error message
            assert any(
                "not found" in str(call).lower()
                for call in mock_console.print.call_args_list
            )
    
    @pytest.mark.asyncio
    async def test_create_api_key_success(
        self,
        mock_console: MagicMock,
        db_session,
        sample_user,
    ):
        """Test successful API key creation."""
        with patch("app.cli.commands.apikeys.async_session_maker") as mock_maker:
            mock_maker.return_value.__aenter__.return_value = db_session
            
            await _create_api_key(
                name="Integration Key",
                user_email=sample_user.email.value,
                scopes=["users:read"],
                expires_days=30,
            )
            
            # Should show success message and key
            assert mock_console.print.called


class TestListAPIKeys:
    """Test API key listing command."""
    
    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_list_all_keys(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test listing all API keys."""
        result = cli_runner.invoke(app, ["list"])
        
        mock_run.assert_called_once()
        assert result.exit_code == 0
    
    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_list_for_specific_user(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test listing API keys for specific user."""
        result = cli_runner.invoke(
            app,
            ["list", "--user", "admin@example.com"],
        )
        
        mock_run.assert_called_once()
        assert result.exit_code == 0


class TestAPIKeyInfo:
    """Test API key info command."""
    
    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_info_command(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test showing info for specific API key."""
        key_id = str(uuid4())
        result = cli_runner.invoke(app, ["info", key_id])
        
        mock_run.assert_called_once()
        assert result.exit_code == 0
