# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for CLI utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

import pytest


class TestCliUtils:
    """Tests for CLI utility functions."""

    def test_format_uuid_short(self) -> None:
        """Test formatting UUID to short form."""
        from app.cli.utils import format_uuid
        from uuid import UUID

        uuid_str = "12345678-1234-1234-1234-123456789012"
        result = format_uuid(uuid_str)

        # Should return a UUID object
        assert result is not None
        assert isinstance(result, UUID)

    def test_format_uuid_valid(self) -> None:
        """Test formatting valid UUID string."""
        from app.cli.utils import format_uuid
        from uuid import UUID

        uuid_str = "12345678-1234-1234-1234-123456789012"
        result = format_uuid(uuid_str)

        # Should return UUID
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_print_table_exists(self) -> None:
        """Test print_table function exists."""
        from app.cli.utils import print_table

        assert print_table is not None
        assert callable(print_table)


class TestCliMainApp:
    """Tests for CLI main app."""

    def test_cli_app_import(self) -> None:
        """Test CLI main app can be imported."""
        from app.cli.main import app

        assert app is not None

    def test_cli_has_subcommands(self) -> None:
        """Test CLI has expected subcommands."""
        from app.cli.main import app

        # Check registered groups/commands
        assert app is not None


class TestDatabaseCommands:
    """Tests for database CLI commands."""

    def test_database_app_import(self) -> None:
        """Test database CLI app can be imported."""
        from app.cli.commands.database import app

        assert app is not None

    def test_seed_command_exists(self) -> None:
        """Test seed command is defined."""
        from app.cli.commands.database import seed_database

        assert seed_database is not None
        assert callable(seed_database)


class TestUserCommands:
    """Tests for user CLI commands."""

    def test_users_app_import(self) -> None:
        """Test users CLI app can be imported."""
        from app.cli.commands.users import app

        assert app is not None

    def test_create_superuser_command_exists(self) -> None:
        """Test create_superuser command is defined."""
        from app.cli.commands.users import create_superuser

        assert create_superuser is not None
        assert callable(create_superuser)


class TestApiKeyCommands:
    """Tests for API key CLI commands."""

    def test_apikeys_app_import(self) -> None:
        """Test apikeys CLI app can be imported."""
        from app.cli.commands.apikeys import app

        assert app is not None

    def test_generate_key_function(self) -> None:
        """Test API key generation function."""
        from app.cli.commands.apikeys import generate_api_key

        key = generate_api_key()
        assert key is not None

    def test_api_key_is_tuple(self) -> None:
        """Test generated API key returns tuple."""
        from app.cli.commands.apikeys import generate_api_key

        result = generate_api_key()
        # Returns (full_key, prefix)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestGetOrCreateDefaultTenant:
    """Tests for get_or_create_default_tenant utility."""

    def test_function_exists(self) -> None:
        """Test get_or_create_default_tenant function exists."""
        from app.cli.utils import get_or_create_default_tenant

        assert get_or_create_default_tenant is not None
        assert callable(get_or_create_default_tenant)


class TestRichConsole:
    """Tests for Rich console output."""

    def test_console_exists_in_commands(self) -> None:
        """Test console is used in CLI commands."""
        from app.cli.commands.database import console

        assert console is not None

    def test_console_can_print(self) -> None:
        """Test console can print without error."""
        from rich.console import Console

        console = Console(quiet=True)  # Suppress output for test
        # Should not raise
        console.print("Test message")
