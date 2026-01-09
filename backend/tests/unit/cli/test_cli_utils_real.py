# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for CLI utils module with real execution."""

from __future__ import annotations

from uuid import uuid4, UUID
import pytest


class TestCliUtilsFormatUuid:
    """Tests for CLI format_uuid utility."""

    def test_format_uuid_valid(self) -> None:
        """Test format_uuid with valid UUID string."""
        from app.cli.utils import format_uuid

        valid_uuid = str(uuid4())
        result = format_uuid(valid_uuid)
        assert result is not None
        assert isinstance(result, UUID)

    def test_format_uuid_invalid_returns_none(self) -> None:
        """Test format_uuid with invalid string returns None."""
        from app.cli.utils import format_uuid

        result = format_uuid("not-a-uuid")
        assert result is None

    def test_format_uuid_empty_string(self) -> None:
        """Test format_uuid with empty string returns None."""
        from app.cli.utils import format_uuid

        result = format_uuid("")
        assert result is None

    def test_format_uuid_partial_uuid(self) -> None:
        """Test format_uuid with partial UUID returns None."""
        from app.cli.utils import format_uuid

        result = format_uuid("12345678-1234")
        assert result is None


class TestCliCheckFunctions:
    """Tests for CLI check database/redis functions."""

    @pytest.mark.asyncio
    async def test_check_database_returns_bool(self) -> None:
        """Test check_database returns boolean."""
        from app.cli.utils import check_database

        result = await check_database()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_check_redis_returns_bool(self) -> None:
        """Test check_redis returns boolean."""
        from app.cli.utils import check_redis

        result = await check_redis()
        assert isinstance(result, bool)


class TestCliPrintTable:
    """Tests for CLI print_table utility."""

    def test_print_table_empty_rows(self, capsys) -> None:
        """Test print_table with empty rows."""
        from app.cli.utils import print_table

        headers = ["Name", "Email"]
        rows = []
        print_table(headers, rows)
        
        captured = capsys.readouterr()
        assert "No data" in captured.out

    def test_print_table_with_matching_data(self, capsys) -> None:
        """Test print_table with proper data structure."""
        from app.cli.utils import print_table

        headers = ["ID", "Name"]
        rows = [
            ["1", "John"],
            ["2", "Jane"],
        ]
        print_table(headers, rows)
        
        captured = capsys.readouterr()
        assert "ID" in captured.out
        assert "Name" in captured.out
        assert "John" in captured.out
        assert "Jane" in captured.out

    def test_print_table_single_row(self, capsys) -> None:
        """Test print_table with single row."""
        from app.cli.utils import print_table

        headers = ["Column"]
        rows = [["Value"]]
        print_table(headers, rows)
        
        captured = capsys.readouterr()
        assert "Column" in captured.out
        assert "Value" in captured.out


class TestCliConfirmAction:
    """Tests for CLI confirm_action utility."""

    def test_confirm_action_import(self) -> None:
        """Test confirm_action can be imported."""
        from app.cli.utils import confirm_action
        
        assert confirm_action is not None
        assert callable(confirm_action)


class TestCliGetOrCreateTenant:
    """Tests for CLI tenant utilities."""

    def test_get_or_create_default_tenant_import(self) -> None:
        """Test get_or_create_default_tenant can be imported."""
        from app.cli.utils import get_or_create_default_tenant
        
        assert get_or_create_default_tenant is not None
        assert callable(get_or_create_default_tenant)


class TestCliMainApp:
    """Tests for CLI main app."""

    def test_app_import(self) -> None:
        """Test CLI app can be imported."""
        from app.cli.main import app

        assert app is not None

    def test_app_is_typer(self) -> None:
        """Test CLI app is a Typer app."""
        from app.cli.main import app
        import typer

        assert isinstance(app, typer.Typer)


class TestCliDatabaseCommands:
    """Tests for CLI database commands."""

    def test_database_app_import(self) -> None:
        """Test database CLI app can be imported."""
        from app.cli.commands.database import app

        assert app is not None

    def test_database_app_is_typer(self) -> None:
        """Test database CLI app is a Typer app."""
        from app.cli.commands.database import app
        import typer

        assert isinstance(app, typer.Typer)


class TestCliUsersCommands:
    """Tests for CLI users commands."""

    def test_users_app_import(self) -> None:
        """Test users CLI app can be imported."""
        from app.cli.commands.users import app

        assert app is not None

    def test_users_app_is_typer(self) -> None:
        """Test users CLI app is a Typer app."""
        from app.cli.commands.users import app
        import typer

        assert isinstance(app, typer.Typer)


class TestCliApikeysCommands:
    """Tests for CLI apikeys commands."""

    def test_apikeys_app_import(self) -> None:
        """Test apikeys CLI app can be imported."""
        from app.cli.commands.apikeys import app

        assert app is not None

    def test_apikeys_app_is_typer(self) -> None:
        """Test apikeys CLI app is a Typer app."""
        from app.cli.commands.apikeys import app
        import typer

        assert isinstance(app, typer.Typer)
