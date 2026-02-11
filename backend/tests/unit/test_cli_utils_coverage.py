# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for CLI utility functions.

Tests helper functions used by CLI commands.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest


class TestCheckDatabase:
    """Tests for database connectivity check."""

    @pytest.mark.asyncio
    async def test_check_database_success(self):
        """Test successful database connection."""
        from app.cli.utils import check_database

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch(
            "app.infrastructure.database.connection.async_session_maker",
            return_value=mock_session,
        ):
            result = await check_database()

            assert result is True

    @pytest.mark.asyncio
    async def test_check_database_failure(self):
        """Test database connection failure."""
        from app.cli.utils import check_database

        with patch(
            "app.infrastructure.database.connection.async_session_maker",
            side_effect=Exception("DB error"),
        ):
            result = await check_database()

            assert result is False


class TestCheckRedis:
    """Tests for Redis connectivity check."""

    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        """Test successful Redis connection."""
        from app.cli.utils import check_redis

        # Mock redis.Redis instance
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        # Mock get_redis_client to return our mock instance
        with patch(
            "app.infrastructure.cache.redis_client.get_redis_client",
            return_value=mock_redis,
        ):
            result = await check_redis()

            assert result is True
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_redis_failure(self):
        """Test Redis connection failure."""
        from app.cli.utils import check_redis

        # Mock exception during get_redis_client
        with patch(
            "app.infrastructure.cache.redis_client.get_redis_client",
            side_effect=Exception("Redis error"),
        ):
            result = await check_redis()

            assert result is False


class TestFormatUUID:
    """Tests for UUID formatting."""

    def test_format_uuid_valid(self):
        """Test valid UUID string."""
        from app.cli.utils import format_uuid

        uuid_str = "12345678-1234-5678-1234-567812345678"
        result = format_uuid(uuid_str)

        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_format_uuid_invalid(self):
        """Test invalid UUID string."""
        from app.cli.utils import format_uuid

        result = format_uuid("not-a-uuid")

        assert result is None

    def test_format_uuid_empty(self):
        """Test empty string."""
        from app.cli.utils import format_uuid

        result = format_uuid("")

        assert result is None


class TestConfirmAction:
    """Tests for user confirmation."""

    def test_confirm_action_yes_default_true(self):
        """Test confirmation with yes and default=True."""
        from app.cli.utils import confirm_action

        with patch("typer.prompt", return_value="y"):
            result = confirm_action("Proceed?", default=True)

            assert result is True

    def test_confirm_action_no_default_true(self):
        """Test rejection with default=True."""
        from app.cli.utils import confirm_action

        with patch("typer.prompt", return_value="n"):
            result = confirm_action("Proceed?", default=True)

            assert result is False

    def test_confirm_action_yes_default_false(self):
        """Test confirmation with default=False."""
        from app.cli.utils import confirm_action

        with patch("typer.prompt", return_value="yes"):
            result = confirm_action("Proceed?", default=False)

            assert result is True

    def test_confirm_action_enter_default_true(self):
        """Test pressing enter with default=True."""
        from app.cli.utils import confirm_action

        with patch("typer.prompt", return_value="y"):
            result = confirm_action("Proceed?", default=True)

            assert result is True


class TestPrintTable:
    """Tests for table printing."""

    def test_print_table_with_data(self):
        """Test printing table with data."""
        from app.cli.utils import print_table

        headers = ["Name", "Email", "Status"]
        rows = [
            ["Alice", "alice@example.com", "Active"],
            ["Bob", "bob@example.com", "Inactive"],
        ]

        with patch("typer.echo") as mock_echo:
            print_table(headers, rows)

            assert mock_echo.call_count >= 4  # Header, separator, 2 rows

    def test_print_table_empty_rows(self):
        """Test printing table with no rows."""
        from app.cli.utils import print_table

        headers = ["Name", "Email"]
        rows = []

        with patch("typer.echo") as mock_echo:
            print_table(headers, rows)

            mock_echo.assert_called_once_with("No data to display")

    def test_print_table_column_width_calculation(self):
        """Test column width adjustment for long content."""
        from app.cli.utils import print_table

        headers = ["ID", "Description"]
        rows = [
            ["1", "A very long description that exceeds header width"],
        ]

        with patch("typer.echo") as mock_echo:
            print_table(headers, rows)

            assert mock_echo.call_count >= 3


class TestGetOrCreateDefaultTenant:
    """Tests for default tenant creation."""

    @pytest.mark.asyncio
    async def test_get_existing_tenant(self):
        """Test getting existing default tenant."""
        from app.cli.utils import get_or_create_default_tenant
        from app.domain.entities.tenant import Tenant

        tenant_id = UUID("11111111-1111-1111-1111-111111111111")
        mock_tenant = Tenant(
            id=tenant_id,
            name="Existing",
            slug="existing",
            is_active=True,
        )

        mock_repo = MagicMock()
        mock_repo.list = AsyncMock(return_value=[mock_tenant])

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker",
                return_value=mock_session,
            ),
            patch(
                "app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository",
                return_value=mock_repo,
            ),
        ):
            result = await get_or_create_default_tenant()

            assert result == tenant_id
            mock_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_default_tenant(self):
        """Test creating default tenant when none exist."""
        from app.cli.utils import get_or_create_default_tenant
        from app.domain.entities.tenant import Tenant

        new_tenant_id = UUID("22222222-2222-2222-2222-222222222222")
        created_tenant = Tenant(
            id=new_tenant_id,
            name="Default",
            slug="default",
            is_active=True,
        )

        mock_repo = MagicMock()
        mock_repo.list = AsyncMock(return_value=[])
        mock_repo.create = AsyncMock(return_value=created_tenant)

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker",
                return_value=mock_session,
            ),
            patch(
                "app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository",
                return_value=mock_repo,
            ),
        ):
            result = await get_or_create_default_tenant()

            assert result == new_tenant_id
            mock_repo.create.assert_called_once()
            mock_session.commit.assert_called_once()
