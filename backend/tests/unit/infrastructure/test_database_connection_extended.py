# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Additional tests for database connection and RLS functionality."""

from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.connection import (
    set_tenant_context,
    get_db_context,
    get_db_session,
)


class TestSetTenantContext:
    """Tests for set_tenant_context function."""

    @pytest.mark.asyncio
    async def test_set_tenant_context_with_valid_uuid(self):
        """Should set tenant context with valid UUID."""
        session = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        
        await set_tenant_context(session, tenant_id)
        
        session.execute.assert_called_once()
        # Get the actual call and extract the SQL
        call_args = session.execute.call_args
        sql_text = str(call_args[0][0])  # First positional argument is the TextClause
        assert str(tenant_id) in sql_text
        assert "app.current_tenant_id" in sql_text

    @pytest.mark.asyncio
    async def test_set_tenant_context_with_none_resets(self):
        """Should reset tenant context when None."""
        session = AsyncMock(spec=AsyncSession)
        
        await set_tenant_context(session, None)
        
        session.execute.assert_called_once()
        # Get the actual call and extract the SQL
        call_args = session.execute.call_args
        sql_text = str(call_args[0][0])  # First positional argument is the TextClause
        assert "RESET" in sql_text
        assert "app.current_tenant_id" in sql_text


class TestGetDbContext:
    """Tests for get_db_context context manager."""

    @pytest.mark.asyncio
    async def test_get_db_context_without_tenant(self):
        """Should create session context without tenant."""
        with patch('app.infrastructure.database.connection.async_session_maker') as mock_maker:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None
            
            async with get_db_context() as session:
                assert session == mock_session
            
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_context_with_tenant(self):
        """Should create session context with tenant."""
        tenant_id = uuid4()
        
        with patch('app.infrastructure.database.connection.async_session_maker') as mock_maker, \
             patch('app.infrastructure.database.connection.set_tenant_context', new_callable=AsyncMock) as mock_set_tenant:
            
            mock_session = AsyncMock(spec=AsyncSession)
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None
            
            async with get_db_context(tenant_id) as session:
                assert session == mock_session
            
            mock_set_tenant.assert_called_once_with(mock_session, tenant_id)
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_context_rollback_on_exception(self):
        """Should rollback on exception."""
        with patch('app.infrastructure.database.connection.async_session_maker') as mock_maker:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None
            
            with pytest.raises(ValueError):
                async with get_db_context() as session:
                    raise ValueError("Test error")
            
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()


class TestGetDbSession:
    """Tests for get_db_session dependency."""

    @pytest.mark.asyncio
    async def test_get_db_session_with_tenant_from_middleware(self):
        """Should get session with tenant from middleware."""
        tenant_id = uuid4()
        
        with patch('app.infrastructure.database.connection.async_session_maker') as mock_maker, \
             patch('app.middleware.tenant.get_current_tenant_id', return_value=tenant_id), \
             patch('app.infrastructure.database.connection.set_tenant_context', new_callable=AsyncMock) as mock_set_tenant:
            
            mock_session = AsyncMock(spec=AsyncSession)
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None
            
            # Consume the entire generator to trigger commit
            gen = get_db_session()
            session = await gen.__anext__()
            assert session == mock_session
            
            # Exit the generator normally to trigger commit
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
            
            mock_set_tenant.assert_called_once_with(mock_session, tenant_id)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_session_without_tenant(self):
        """Should get session without tenant when not set."""
        with patch('app.infrastructure.database.connection.async_session_maker') as mock_maker, \
             patch('app.middleware.tenant.get_current_tenant_id', return_value=None):
            
            mock_session = AsyncMock(spec=AsyncSession)
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None
            
            # Consume the entire generator to trigger commit
            gen = get_db_session()
            session = await gen.__anext__()
            assert session == mock_session
            
            # Exit the generator normally to trigger commit
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
            
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_session_rollback_on_exception(self):
        """Should rollback session on exception."""
        with patch('app.infrastructure.database.connection.async_session_maker') as mock_maker, \
             patch('app.middleware.tenant.get_current_tenant_id', return_value=None):
            
            mock_session = AsyncMock(spec=AsyncSession)
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None
            
            gen = get_db_session()
            session = await gen.__anext__()
            
            # Simulate exception during request
            with pytest.raises(ValueError):
                await gen.athrow(ValueError("Test error"))
            
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
