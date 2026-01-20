# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for CLI utility functions."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import UUID, uuid4

from app.cli.utils import (
    check_database,
    check_redis,
    format_uuid,
    confirm_action,
    print_table,
    get_or_create_default_tenant,
)


class TestCheckDatabase:
    """Test database connectivity check."""
    
    @pytest.mark.asyncio
    async def test_check_database_success(self):
        """Test successful database connection."""
        with patch("app.infrastructure.database.connection.async_session_maker") as mock_maker:
            mock_session = MagicMock()
            mock_session.execute = AsyncMock()
            mock_maker.return_value.__aenter__.return_value = mock_session
            
            result = await check_database()
            
            assert result is True
            mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_database_failure(self):
        """Test failed database connection."""
        with patch("app.infrastructure.database.connection.async_session_maker") as mock_maker:
            mock_maker.side_effect = Exception("Connection failed")
            
            result = await check_database()
            
            assert result is False


class TestCheckRedis:
    """Test Redis connectivity check."""
    
    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        """Test successful Redis connection."""
        # Mock the redis_client module since it doesn't exist
        mock_redis_client_module = MagicMock()
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis_client_module.get_redis_client = AsyncMock(return_value=mock_redis)
        
        import sys
        with patch.dict(sys.modules, {"app.infrastructure.cache.redis_client": mock_redis_client_module}):
            result = await check_redis()
            
            assert result is True
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_redis_failure(self):
        """Test failed Redis connection."""
        # Mock the redis_client module to raise exception
        mock_redis_client_module = MagicMock()
        mock_redis_client_module.get_redis_client = AsyncMock(side_effect=Exception("Connection failed"))
        
        import sys
        with patch.dict(sys.modules, {"app.infrastructure.cache.redis_client": mock_redis_client_module}):
            result = await check_redis()
            
            assert result is False


class TestFormatUUID:
    """Test UUID formatting and validation."""
    
    def test_format_valid_uuid(self):
        """Test formatting valid UUID string."""
        uuid_obj = uuid4()
        uuid_str = str(uuid_obj)
        
        result = format_uuid(uuid_str)
        
        assert isinstance(result, UUID)
        assert result == uuid_obj
    
    def test_format_invalid_uuid(self):
        """Test formatting invalid UUID string."""
        result = format_uuid("not-a-uuid")
        
        assert result is None
    
    def test_format_uuid_with_different_formats(self):
        """Test UUID with different formats."""
        uuid_obj = uuid4()
        
        # Standard format
        result1 = format_uuid(str(uuid_obj))
        assert result1 == uuid_obj
        
        # Without hyphens
        result2 = format_uuid(uuid_obj.hex)
        assert result2 == uuid_obj


class TestConfirmAction:
    """Test user confirmation prompts."""
    
    @patch("typer.prompt")
    def test_confirm_action_yes(self, mock_prompt: MagicMock):
        """Test confirmation with yes response."""
        mock_prompt.return_value = "y"
        
        result = confirm_action("Are you sure?")
        
        assert result is True
        mock_prompt.assert_called_once()
    
    @patch("typer.prompt")
    def test_confirm_action_no(self, mock_prompt: MagicMock):
        """Test confirmation with no response."""
        mock_prompt.return_value = "n"
        
        result = confirm_action("Are you sure?")
        
        assert result is False
    
    @patch("typer.prompt")
    def test_confirm_action_default_true(self, mock_prompt: MagicMock):
        """Test confirmation with default=True."""
        mock_prompt.return_value = "y"
        
        result = confirm_action("Continue?", default=True)
        
        assert result is True
        # Should show [Y/n] suffix
        call_args = mock_prompt.call_args[0][0]
        assert "[Y/n]" in call_args
    
    @patch("typer.prompt")
    def test_confirm_action_default_false(self, mock_prompt: MagicMock):
        """Test confirmation with default=False."""
        mock_prompt.return_value = "n"
        
        result = confirm_action("Continue?", default=False)
        
        assert result is False
        # Should show [y/N] suffix
        call_args = mock_prompt.call_args[0][0]
        assert "[y/N]" in call_args
    
    @patch("typer.prompt")
    def test_confirm_action_yes_variations(self, mock_prompt: MagicMock):
        """Test that 'yes' and 'YES' work."""
        for response in ["yes", "YES", "Yes"]:
            mock_prompt.return_value = response
            result = confirm_action("Sure?")
            assert result is True


class TestPrintTable:
    """Test table printing utility."""
    
    @patch("typer.echo")
    def test_print_table_with_data(self, mock_echo: MagicMock):
        """Test printing table with data."""
        headers = ["Name", "Email", "Status"]
        rows = [
            ["John Doe", "john@example.com", "active"],
            ["Jane Smith", "jane@example.com", "inactive"],
        ]
        
        print_table(headers, rows)
        
        # Should print header, separator, and rows
        assert mock_echo.call_count >= 4
    
    @patch("typer.echo")
    def test_print_table_empty(self, mock_echo: MagicMock):
        """Test printing empty table."""
        headers = ["Name", "Email"]
        rows = []
        
        print_table(headers, rows)
        
        # Should print "No data to display"
        mock_echo.assert_called_once_with("No data to display")
    
    @patch("typer.echo")
    def test_print_table_column_alignment(self, mock_echo: MagicMock):
        """Test that columns are properly aligned."""
        headers = ["Short", "Very Long Header"]
        rows = [
            ["A", "B"],
            ["Long value", "C"],
        ]
        
        print_table(headers, rows)
        
        # Should adjust column widths
        calls = [call[0][0] for call in mock_echo.call_args_list]
        # All rows should have same length (aligned)
        assert len(set(len(row) for row in calls if "|" in row)) <= 1


class TestGetOrCreateDefaultTenant:
    """Test default tenant creation."""
    
    @pytest.mark.asyncio
    async def test_get_existing_tenant(self, db_session, sample_tenant):
        """Test getting existing tenant."""
        with patch("app.infrastructure.database.connection.async_session_maker") as mock_maker:
            mock_maker.return_value.__aenter__.return_value = db_session
            
            tenant_id = await get_or_create_default_tenant()
            
            assert isinstance(tenant_id, UUID)
            assert tenant_id == sample_tenant.id
    
    @pytest.mark.asyncio
    async def test_create_default_tenant(self, db_session):
        """Test creating default tenant when none exists."""
        with patch("app.infrastructure.database.connection.async_session_maker") as mock_maker:
            mock_session = MagicMock()
            mock_session.commit = AsyncMock()
            
            # Mock empty tenant list
            mock_repo = MagicMock()
            mock_repo.list = AsyncMock(return_value=[])
            
            # Mock tenant creation
            from app.domain.entities.tenant import Tenant
            new_tenant = Tenant(
                id=uuid4(),
                name="Default",
                slug="default",
                is_active=True,
            )
            mock_repo.create = AsyncMock(return_value=new_tenant)
            
            mock_maker.return_value.__aenter__.return_value = mock_session
            
            with patch("app.infrastructure.database.repositories.tenant_repository.SQLAlchemyTenantRepository", return_value=mock_repo):
                tenant_id = await get_or_create_default_tenant()
                
                assert isinstance(tenant_id, UUID)
                assert tenant_id == new_tenant.id
                mock_repo.create.assert_called_once()
                mock_session.commit.assert_called_once()
