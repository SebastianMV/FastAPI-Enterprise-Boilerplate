# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Integration tests for user management CLI commands."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.cli.commands.users import app, _create_superuser


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_console():
    """Mock rich console to prevent actual output."""
    with patch("app.cli.commands.users.console") as mock:
        yield mock


class TestCreateSuperuser:
    """Test superuser creation command."""
    
    @patch("app.cli.commands.users.asyncio.run")
    def test_create_superuser_with_prompts(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test creating superuser with prompts."""
        result = cli_runner.invoke(
            app,
            ["create-superuser"],
            input="superadmin@example.com\nSuperSecure123!\nSuperSecure123!\n",
        )
        
        mock_run.assert_called_once()
        assert result.exit_code == 0
    
    @patch("app.cli.commands.users.asyncio.run")
    def test_create_superuser_with_options(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test creating superuser with all options specified."""
        result = cli_runner.invoke(
            app,
            [
                "create-superuser",
                "--email", "admin@example.com",
                "--password", "AdminPass123!",
                "--first-name", "John",
                "--last-name", "Doe",
            ],
        )
        
        mock_run.assert_called_once()
        assert result.exit_code == 0
    
    @pytest.mark.asyncio
    async def test_create_superuser_invalid_email(
        self,
        mock_console: MagicMock,
        db_session,
    ):
        """Test that invalid email is rejected."""
        with pytest.raises(SystemExit):
            await _create_superuser(
                email="not-an-email",
                password="ValidPass123!",
                first_name="Admin",
                last_name="User",
            )
        
        # Should print error
        assert any(
            "invalid email" in str(call).lower()
            for call in mock_console.print.call_args_list
        )
    
    @pytest.mark.asyncio
    async def test_create_superuser_weak_password(
        self,
        mock_console: MagicMock,
        db_session,
    ):
        """Test that weak password is rejected."""
        with pytest.raises(SystemExit):
            await _create_superuser(
                email="admin@example.com",
                password="weak",
                first_name="Admin",
                last_name="User",
            )
        
        # Should print error
        assert any(
            "invalid password" in str(call).lower()
            for call in mock_console.print.call_args_list
        )
    
    @pytest.mark.asyncio
    async def test_create_superuser_duplicate_email(
        self,
        mock_console: MagicMock,
        db_session,
        sample_user,
    ):
        """Test that duplicate email is rejected."""
        with patch("app.cli.commands.users.async_session_maker") as mock_maker:
            mock_maker.return_value.__aenter__.return_value = db_session
            
            with pytest.raises(SystemExit):
                await _create_superuser(
                    email=sample_user.email.value,
                    password="ValidPass123!",
                    first_name="Admin",
                    last_name="User",
                )
            
            # Should print error about existing user
            assert any(
                "already exists" in str(call).lower()
                for call in mock_console.print.call_args_list
            )


class TestListUsers:
    """Test user listing command."""
    
    @patch("app.cli.commands.users.asyncio.run")
    def test_list_all_users(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test listing all users."""
        result = cli_runner.invoke(app, ["list"])
        
        mock_run.assert_called_once()
        assert result.exit_code == 0
    
    @patch("app.cli.commands.users.asyncio.run")
    def test_list_with_limit(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test listing users with limit."""
        result = cli_runner.invoke(app, ["list", "--limit", "10"])
        
        mock_run.assert_called_once()
        assert result.exit_code == 0


class TestActivateUser:
    """Test user activation command."""
    
    @patch("app.cli.commands.users.asyncio.run")
    def test_activate_user(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test activating user by ID."""
        user_id = str(uuid4())
        result = cli_runner.invoke(
            app,
            ["activate", user_id],
        )
        
        mock_run.assert_called_once()
        assert result.exit_code == 0


class TestDeactivateUser:
    """Test user deactivation command."""
    
    @patch("app.cli.commands.users.asyncio.run")
    def test_deactivate_user(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test deactivating user by ID."""
        user_id = str(uuid4())
        result = cli_runner.invoke(
            app,
            ["deactivate", user_id],
        )
        
        mock_run.assert_called_once()
        assert result.exit_code == 0
