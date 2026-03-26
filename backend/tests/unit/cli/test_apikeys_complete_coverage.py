# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Comprehensive tests for CLI apikeys commands to achieve 100% coverage.
Focuses on the 121 uncovered lines in app/cli/commands/apikeys.py
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestCreateAPIKeyAsync:
    """Tests for create_api_key async implementation."""

    @pytest.mark.asyncio
    async def test_create_api_key_user_not_found(self):
        """Test create API key when user doesn't exist."""
        import typer

        from app.cli.commands.apikeys import _create_api_key

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = None

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.commands.apikeys.console") as mock_console,
            pytest.raises(typer.Exit) as exc_info,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _create_api_key("Test Key", "nonexistent@example.com", [], None)

        assert exc_info.value.exit_code == 1
        mock_console.print.assert_called_once()
        assert "User not found" in str(mock_console.print.call_args)

    @pytest.mark.asyncio
    async def test_create_api_key_success_no_expiration(self):
        """Test successful API key creation without expiration."""
        from app.cli.commands.apikeys import _create_api_key

        user_id = uuid4()
        tenant_id = uuid4()

        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id
        mock_user.email = "user@example.com"

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = mock_user

        mock_api_key_model = MagicMock()
        mock_api_key_model.id = uuid4()
        mock_api_key_model.name = "Test Key"

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "app.infrastructure.auth.jwt_handler.hash_password",
                return_value="hashed_key",
            ),
            patch(
                "app.infrastructure.database.models.api_key.APIKeyModel",
                return_value=mock_api_key_model,
            ),
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _create_api_key("Test Key", "user@example.com", ["users:read"], None)

        # Should have created and saved the key
        mock_session.add.assert_called_once_with(mock_api_key_model)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiration(self):
        """Test API key creation with expiration date."""
        from app.cli.commands.apikeys import _create_api_key

        user_id = uuid4()
        tenant_id = uuid4()

        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = mock_user

        mock_api_key_class = MagicMock()
        mock_api_key_model = MagicMock()
        mock_api_key_class.return_value = mock_api_key_model

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch(
                "app.infrastructure.auth.jwt_handler.hash_password",
                return_value="hashed",
            ),
            patch(
                "app.infrastructure.database.models.api_key.APIKeyModel",
                mock_api_key_class,
            ),
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _create_api_key("Temp Key", "user@example.com", [], 30)

        # Verify APIKeyModel was called with expires_at
        call_kwargs = mock_api_key_class.call_args[1]
        assert call_kwargs["expires_at"] is not None
        assert isinstance(call_kwargs["expires_at"], datetime)


class TestListAPIKeys:
    """Tests for list_api_keys command."""

    @pytest.mark.asyncio
    async def test_list_no_keys_found(self):
        """Test listing when no keys exist."""
        import typer

        from app.cli.commands.apikeys import _list_api_keys

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.commands.apikeys.console") as mock_console,
            pytest.raises(typer.Exit) as exc_info,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _list_api_keys(None, False)

        assert exc_info.value.exit_code == 0
        mock_console.print.assert_called_once()
        assert "No API keys found" in str(mock_console.print.call_args)

    @pytest.mark.asyncio
    async def test_list_active_keys_only(self):
        """Test listing only active keys."""
        from app.cli.commands.apikeys import _list_api_keys

        mock_session = AsyncMock()

        # Create mock API key and user
        mock_api_key = MagicMock()
        mock_api_key.id = uuid4()
        mock_api_key.name = "Active Key"
        mock_api_key.prefix = "abc12345"
        mock_api_key.scopes = ["users:read"]
        mock_api_key.is_active = True
        mock_api_key.expires_at = None
        mock_api_key.last_used_at = None

        mock_user = MagicMock()
        mock_user.email = "user@example.com"

        mock_result = MagicMock()
        mock_result.all.return_value = [(mock_api_key, mock_user)]
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _list_api_keys(None, False)

        # Should have executed query
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_with_user_filter(self):
        """Test listing keys filtered by user email."""
        from app.cli.commands.apikeys import _list_api_keys

        mock_session = AsyncMock()
        mock_result = MagicMock()

        mock_api_key = MagicMock()
        mock_api_key.id = uuid4()
        mock_api_key.name = "User Key"
        mock_api_key.prefix = "xyz98765"
        mock_api_key.scopes = []
        mock_api_key.is_active = True
        mock_api_key.expires_at = None
        mock_api_key.last_used_at = datetime.now(UTC)

        mock_user = MagicMock()
        mock_user.email = "specific@example.com"

        mock_result.all.return_value = [(mock_api_key, mock_user)]
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _list_api_keys("specific@example.com", False)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_include_inactive(self):
        """Test listing including inactive keys."""
        from app.cli.commands.apikeys import _list_api_keys

        mock_session = AsyncMock()
        mock_result = MagicMock()

        mock_api_key = MagicMock()
        mock_api_key.id = uuid4()
        mock_api_key.name = "Inactive Key"
        mock_api_key.prefix = "inactive1"
        mock_api_key.scopes = ["users:read", "users:write", "admin:all"]
        mock_api_key.is_active = False
        mock_api_key.expires_at = None
        mock_api_key.last_used_at = None

        mock_user = MagicMock()
        mock_user.email = "admin@example.com"

        mock_result.all.return_value = [(mock_api_key, mock_user)]
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _list_api_keys(None, True)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_expired_key_warning(self):
        """Test that expired keys show warning status."""
        from app.cli.commands.apikeys import _list_api_keys

        mock_session = AsyncMock()
        mock_result = MagicMock()

        # Expired key
        mock_api_key = MagicMock()
        mock_api_key.id = uuid4()
        mock_api_key.name = "Expired Key"
        mock_api_key.prefix = "expired01"
        mock_api_key.scopes = []
        mock_api_key.is_active = True
        mock_api_key.expires_at = datetime.now(UTC) - timedelta(days=1)
        mock_api_key.last_used_at = None

        mock_user = MagicMock()
        mock_user.email = "user@example.com"

        mock_result.all.return_value = [(mock_api_key, mock_user)]
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _list_api_keys(None, False)

        mock_session.execute.assert_called_once()


class TestRevokeAPIKey:
    """Tests for revoke_api_key command."""

    @pytest.mark.asyncio
    async def test_revoke_key_not_found(self):
        """Test revoking when key doesn't exist."""
        import typer

        from app.cli.commands.apikeys import _revoke_api_key

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.utils.format_uuid", return_value=None),
            patch("app.cli.commands.apikeys.console") as mock_console,
            pytest.raises(typer.Exit) as exc_info,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _revoke_api_key("nonexistent", False)

        assert exc_info.value.exit_code == 1
        assert "not found" in str(mock_console.print.call_args)

    @pytest.mark.asyncio
    async def test_revoke_already_revoked(self):
        """Test revoking an already revoked key."""
        import typer

        from app.cli.commands.apikeys import _revoke_api_key

        mock_session = AsyncMock()
        mock_api_key = MagicMock()
        mock_api_key.is_active = False
        mock_api_key.name = "Already Revoked"
        mock_api_key.prefix = "revoked01"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.utils.format_uuid", return_value=uuid4()),
            patch("app.cli.commands.apikeys.console") as mock_console,
            pytest.raises(typer.Exit) as exc_info,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _revoke_api_key(str(uuid4()), False)

        assert exc_info.value.exit_code == 0
        assert "already revoked" in str(mock_console.print.call_args)

    @pytest.mark.asyncio
    async def test_revoke_user_cancels(self):
        """Test when user cancels revocation."""
        import typer

        from app.cli.commands.apikeys import _revoke_api_key

        mock_session = AsyncMock()
        mock_api_key = MagicMock()
        mock_api_key.is_active = True
        mock_api_key.name = "Active Key"
        mock_api_key.prefix = "active123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.utils.format_uuid", return_value=uuid4()),
            patch("typer.prompt", return_value="n"),
            pytest.raises(typer.Exit) as exc_info,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _revoke_api_key(str(uuid4()), False)

        assert exc_info.value.exit_code == 0
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_success_with_force(self):
        """Test successful revocation with --force flag."""
        from app.cli.commands.apikeys import _revoke_api_key

        mock_session = AsyncMock()
        mock_api_key = MagicMock()
        mock_api_key.is_active = True
        mock_api_key.name = "Key to Revoke"
        mock_api_key.prefix = "revoke123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.utils.format_uuid", return_value=uuid4()),
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _revoke_api_key(str(uuid4()), force=True)

        assert mock_api_key.is_active == False
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_by_prefix(self):
        """Test revoking by prefix instead of UUID."""
        from app.cli.commands.apikeys import _revoke_api_key

        mock_session = AsyncMock()
        mock_api_key = MagicMock()
        mock_api_key.is_active = True
        mock_api_key.name = "Prefix Key"
        mock_api_key.prefix = "abc12345"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.utils.format_uuid", return_value=None),
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _revoke_api_key("abc12345", force=True)

        assert mock_api_key.is_active == False
        mock_session.commit.assert_called_once()


class TestAPIKeyInfo:
    """Tests for api_key_info command."""

    @pytest.mark.asyncio
    async def test_info_key_not_found(self):
        """Test info when key doesn't exist."""
        import typer

        from app.cli.commands.apikeys import _api_key_info

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.utils.format_uuid", return_value=uuid4()),
            patch("app.cli.commands.apikeys.console") as mock_console,
            pytest.raises(typer.Exit) as exc_info,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _api_key_info(str(uuid4()))

        assert exc_info.value.exit_code == 1
        assert "not found" in str(mock_console.print.call_args)

    @pytest.mark.asyncio
    async def test_info_active_key(self):
        """Test displaying info for active key."""
        from app.cli.commands.apikeys import _api_key_info

        mock_session = AsyncMock()

        mock_api_key = MagicMock()
        mock_api_key.id = uuid4()
        mock_api_key.name = "Production Key"
        mock_api_key.prefix = "prod1234"
        mock_api_key.tenant_id = uuid4()
        mock_api_key.is_active = True
        mock_api_key.created_at = datetime.now(UTC)
        mock_api_key.expires_at = None
        mock_api_key.scopes = ["users:read", "users:write"]
        mock_api_key.usage_count = 1500
        mock_api_key.last_used_at = datetime.now(UTC)
        mock_api_key.last_used_ip = "192.168.1.1"

        mock_user = MagicMock()
        mock_user.email = "prod@example.com"

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (mock_api_key, mock_user)
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.utils.format_uuid", return_value=uuid4()),
            patch("app.cli.commands.apikeys.console") as mock_console,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _api_key_info(str(uuid4()))

        # Should have printed the key details
        assert mock_console.print.call_count > 10

    @pytest.mark.asyncio
    async def test_info_expired_key(self):
        """Test displaying info for expired key."""
        from app.cli.commands.apikeys import _api_key_info

        mock_session = AsyncMock()

        mock_api_key = MagicMock()
        mock_api_key.id = uuid4()
        mock_api_key.name = "Expired Key"
        mock_api_key.prefix = "expired01"
        mock_api_key.tenant_id = uuid4()
        mock_api_key.is_active = True
        mock_api_key.created_at = datetime.now(UTC) - timedelta(days=60)
        mock_api_key.expires_at = datetime.now(UTC) - timedelta(days=1)
        mock_api_key.scopes = []
        mock_api_key.usage_count = 0
        mock_api_key.last_used_at = None
        mock_api_key.last_used_ip = None

        mock_user = MagicMock()
        mock_user.email = "user@example.com"

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (mock_api_key, mock_user)
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.utils.format_uuid", return_value=uuid4()),
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _api_key_info(str(uuid4()))

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_info_revoked_key(self):
        """Test displaying info for revoked key."""
        from app.cli.commands.apikeys import _api_key_info

        mock_session = AsyncMock()

        mock_api_key = MagicMock()
        mock_api_key.id = uuid4()
        mock_api_key.name = "Revoked Key"
        mock_api_key.prefix = "revoked01"
        mock_api_key.tenant_id = uuid4()
        mock_api_key.is_active = False
        mock_api_key.created_at = datetime.now(UTC)
        mock_api_key.expires_at = None
        mock_api_key.scopes = ["admin:all"]
        mock_api_key.usage_count = 999
        mock_api_key.last_used_at = datetime.now(UTC)
        mock_api_key.last_used_ip = "10.0.0.1"

        mock_user = MagicMock()
        mock_user.email = "admin@example.com"

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (mock_api_key, mock_user)
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.utils.format_uuid", return_value=uuid4()),
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _api_key_info(str(uuid4()))

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_info_by_prefix(self):
        """Test getting info by prefix instead of UUID."""
        from app.cli.commands.apikeys import _api_key_info

        mock_session = AsyncMock()

        mock_api_key = MagicMock()
        mock_api_key.id = uuid4()
        mock_api_key.name = "Prefix Key"
        mock_api_key.prefix = "prefix12"
        mock_api_key.tenant_id = uuid4()
        mock_api_key.is_active = True
        mock_api_key.created_at = datetime.now(UTC)
        mock_api_key.expires_at = None
        mock_api_key.scopes = []
        mock_api_key.usage_count = 42
        mock_api_key.last_used_at = None
        mock_api_key.last_used_ip = None

        mock_user = MagicMock()
        mock_user.email = "user@example.com"

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (mock_api_key, mock_user)
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch("app.cli.utils.format_uuid", return_value=None),
            patch("app.cli.commands.apikeys.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _api_key_info("prefix12")

        mock_session.execute.assert_called_once()
