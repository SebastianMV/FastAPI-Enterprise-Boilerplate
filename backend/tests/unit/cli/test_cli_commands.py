# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for CLI commands modules."""

from datetime import datetime, timezone as tz
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestAPIKeysCommands:
    """Tests for API keys CLI commands."""

    def test_generate_api_key_function(self) -> None:
        """Test API key generation function."""
        from app.cli.commands.apikeys import generate_api_key

        key, prefix = generate_api_key()

        assert len(key) > 0
        assert len(prefix) == 8
        assert key.startswith(prefix)

    def test_generate_api_key_unique(self) -> None:
        """Test that generated keys are unique."""
        from app.cli.commands.apikeys import generate_api_key

        keys = [generate_api_key()[0] for _ in range(100)]
        unique_keys = set(keys)

        assert len(unique_keys) == 100

    def test_generate_api_key_secure_length(self) -> None:
        """Test API key has secure length."""
        from app.cli.commands.apikeys import generate_api_key

        key, prefix = generate_api_key()

        # Base64 encoded 32 bytes = ~43 characters
        assert len(key) >= 40


class TestDatabaseCommands:
    """Tests for database CLI commands."""

    @pytest.mark.asyncio
    async def test_seed_database_structure(self) -> None:
        """Test seed database async function exists."""
        from app.cli.commands.database import _seed_database

        # Function should exist
        assert callable(_seed_database)

    def test_seed_command_exists(self) -> None:
        """Test seed command is registered."""
        from app.cli.commands.database import app

        # Get all registered commands
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "seed" in command_names

    def test_info_command_exists(self) -> None:
        """Test info command is registered."""
        from app.cli.commands.database import app

        command_names = [cmd.name for cmd in app.registered_commands]
        assert "info" in command_names

    def test_reset_command_exists(self) -> None:
        """Test reset command is registered."""
        from app.cli.commands.database import app

        command_names = [cmd.name for cmd in app.registered_commands]
        assert "reset" in command_names


class TestUsersCommands:
    """Tests for users CLI commands."""

    def test_users_app_exists(self) -> None:
        """Test users CLI app exists."""
        from app.cli.commands.users import app

        assert app is not None

    def test_create_command_exists(self) -> None:
        """Test create-superuser command is registered."""
        from app.cli.commands.users import app

        command_names = [cmd.name for cmd in app.registered_commands]
        assert "create-superuser" in command_names

    def test_list_command_exists(self) -> None:
        """Test list command is registered."""
        from app.cli.commands.users import app

        command_names = [cmd.name for cmd in app.registered_commands]
        assert "list" in command_names


class TestCLIUtils:
    """Tests for CLI utility functions."""

    def test_format_uuid_exists(self) -> None:
        """Test format_uuid function exists."""
        from app.cli.utils import format_uuid

        test_uuid = str(uuid4())
        result = format_uuid(test_uuid)

        assert result is not None

    def test_confirm_action_function_exists(self) -> None:
        """Test confirm_action function exists."""
        from app.cli.utils import confirm_action

        assert callable(confirm_action)


class TestAPIKeysIntegration:
    """Integration tests for API keys CLI."""

    def test_apikeys_app_registered(self) -> None:
        """Test API keys app is registered."""
        from app.cli.commands.apikeys import app

        assert app is not None
        assert len(app.registered_commands) > 0

    def test_generate_command_exists(self) -> None:
        """Test generate command is registered."""
        from app.cli.commands.apikeys import app

        command_names = [cmd.name for cmd in app.registered_commands]
        assert "generate" in command_names

    def test_list_command_exists(self) -> None:
        """Test list command is registered."""
        from app.cli.commands.apikeys import app

        command_names = [cmd.name for cmd in app.registered_commands]
        assert "list" in command_names

    def test_revoke_command_exists(self) -> None:
        """Test revoke command is registered."""
        from app.cli.commands.apikeys import app

        command_names = [cmd.name for cmd in app.registered_commands]
        assert "revoke" in command_names


class TestDatabaseSeeding:
    """Tests for database seeding functions."""

    def test_seed_options(self) -> None:
        """Test seed command has expected options."""
        from app.cli.commands.database import seed_database
        import inspect

        sig = inspect.signature(seed_database)
        params = list(sig.parameters.keys())

        assert "include_users" in params
        assert "include_roles" in params
        assert "include_tenants" in params
        assert "clear_existing" in params

    def test_seed_with_options_defaults(self) -> None:
        """Test seed command option defaults."""
        from app.cli.commands.database import seed_database
        import inspect

        sig = inspect.signature(seed_database)
        
        # Get default values
        include_users_default = sig.parameters["include_users"].default
        clear_existing_default = sig.parameters["clear_existing"].default
        
        # Check it has a default (typer.Option)
        assert include_users_default is not None
        assert clear_existing_default is not None


class TestCLIHelpText:
    """Tests for CLI help text and documentation."""

    def test_database_app_help(self) -> None:
        """Test database app has help text."""
        from app.cli.commands.database import app

        assert app.info.help is not None

    def test_apikeys_app_help(self) -> None:
        """Test API keys app has help text."""
        from app.cli.commands.apikeys import app

        assert app.info.help is not None

    def test_users_app_help(self) -> None:
        """Test users app has help text."""
        from app.cli.commands.users import app

        assert app.info.help is not None


class TestAPIKeyGeneration:
    """Additional tests for API key generation."""

    def test_key_format_url_safe(self) -> None:
        """Test generated key is URL safe."""
        from app.cli.commands.apikeys import generate_api_key

        key, _ = generate_api_key()

        # URL safe characters only
        for char in key:
            assert char.isalnum() or char in "-_"

    def test_prefix_is_start_of_key(self) -> None:
        """Test prefix matches key start."""
        from app.cli.commands.apikeys import generate_api_key

        key, prefix = generate_api_key()

        assert key[:8] == prefix

    def test_multiple_generations_all_unique(self) -> None:
        """Test many generated keys are all unique."""
        from app.cli.commands.apikeys import generate_api_key

        keys_and_prefixes = [generate_api_key() for _ in range(50)]
        all_keys = [k[0] for k in keys_and_prefixes]
        all_prefixes = [k[1] for k in keys_and_prefixes]

        assert len(set(all_keys)) == 50
        # Prefixes might collide but should be mostly unique
        assert len(set(all_prefixes)) >= 45
