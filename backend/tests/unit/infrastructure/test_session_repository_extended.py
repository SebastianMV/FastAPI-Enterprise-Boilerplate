# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Session Repository methods.

Tests session management operations.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.entities.session import UserSession
from app.infrastructure.database.repositories.session_repository import (
    SQLAlchemySessionRepository,
)


class TestSessionRepositoryMethods:
    """Tests for session repository methods."""

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating a new session."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        session = UserSession(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            refresh_token_hash="hash123",
            device_name="Test Device",
            device_type="browser",
            browser="Chrome",
            os="Windows",
            ip_address="127.0.0.1",
            is_revoked=False,
            last_activity=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        # Mock model creation
        mock_model = MagicMock()
        mock_model.id = session.id
        mock_model.tenant_id = session.tenant_id
        mock_model.user_id = session.user_id
        mock_model.refresh_token_hash = session.refresh_token_hash
        mock_model.device_name = session.device_name
        mock_model.device_type = session.device_type
        mock_model.browser = session.browser
        mock_model.os = session.os
        mock_model.ip_address = session.ip_address
        mock_model.is_revoked = False
        mock_model.revoked_at = None
        mock_model.last_activity = session.last_activity
        mock_model.created_at = session.created_at

        mock_db_session.refresh = AsyncMock()

        # Execute create
        with patch.object(repo, "_to_entity", return_value=session):
            result = await repo.create(session)

            assert result == session
            mock_db_session.add.assert_called_once()
            mock_db_session.flush.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self):
        """Test getting session by ID when it exists."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        session_id = uuid4()

        # Mock session
        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.user_id = uuid4()
        mock_session.tenant_id = uuid4()
        mock_session.is_revoked = False
        mock_session.refresh_token_hash = "hash123"
        mock_session.device_name = "Test"
        mock_session.last_activity = datetime.now(UTC)
        mock_session.created_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db_session.execute.return_value = mock_result

        session = await repo.get_by_id(session_id)

        assert session is not None
        assert session.id == session_id
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Test getting session by ID when it doesn't exist."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        session_id = uuid4()

        # Mock not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        session = await repo.get_by_id(session_id)

        assert session is None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_sessions_include_revoked(self):
        """Test getting all sessions including revoked ones."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        user_id = uuid4()

        # Mock sessions
        active_session = MagicMock(
            id=uuid4(),
            user_id=user_id,
            is_revoked=False,
            last_activity=datetime.now(UTC),
        )
        revoked_session = MagicMock(
            id=uuid4(),
            user_id=user_id,
            is_revoked=True,
            last_activity=datetime.now(UTC) - timedelta(days=1),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            active_session,
            revoked_session,
        ]
        mock_db_session.execute.return_value = mock_result

        # Call with include_revoked=True
        sessions = await repo.get_user_sessions(user_id, include_revoked=True)

        assert len(sessions) == 2
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_sessions_active_only(self):
        """Test getting only active sessions."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        user_id = uuid4()

        # Mock only active session
        active_session = MagicMock(
            id=uuid4(),
            user_id=user_id,
            is_revoked=False,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [active_session]
        mock_db_session.execute.return_value = mock_result

        sessions = await repo.get_user_sessions(user_id, include_revoked=False)

        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_revoke_all_except_current(self):
        """Test revoking all sessions except current."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        user_id = uuid4()
        current_session_id = uuid4()

        # Mock update result
        mock_result = MagicMock()
        mock_result.rowcount = 3  # 3 other sessions revoked
        mock_db_session.execute.return_value = mock_result

        count = await repo.revoke_all_except(user_id, current_session_id)

        assert count == 3
        mock_db_session.execute.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_all_user_sessions(self):
        """Test revoking all sessions for a user."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        user_id = uuid4()

        # Mock update result
        mock_result = MagicMock()
        mock_result.rowcount = 5  # 5 sessions revoked
        mock_db_session.execute.return_value = mock_result

        count = await repo.revoke_all(user_id)

        assert count == 5
        mock_db_session.execute.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_activity_with_ip(self):
        """Test updating session activity with IP address."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        session_id = uuid4()
        new_ip = "192.168.1.100"

        await repo.update_activity(session_id, ip_address=new_ip)

        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_activity_without_ip(self):
        """Test updating session activity without IP."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        session_id = uuid4()

        await repo.update_activity(session_id, ip_address=None)

        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(self):
        """Test cleaning up old revoked sessions."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        older_than = datetime.now(UTC) - timedelta(days=30)

        # Mock delete result
        mock_result = MagicMock()
        mock_result.rowcount = 10  # 10 old sessions deleted
        mock_db_session.execute.return_value = mock_result

        count = await repo.cleanup_old_sessions(older_than)

        assert count == 10
        mock_db_session.execute.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_token_hash_found(self):
        """Test getting session by token hash."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        token_hash = "abc123"

        # Mock found session
        mock_session = MagicMock(
            id=uuid4(),
            refresh_token_hash=token_hash,
            is_revoked=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db_session.execute.return_value = mock_result

        session = await repo.get_by_token_hash(token_hash)

        assert session is not None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_token_hash_not_found(self):
        """Test getting session by non-existent token hash."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        token_hash = "nonexistent"

        # Mock not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        session = await repo.get_by_token_hash(token_hash)

        assert session is None

    @pytest.mark.asyncio
    async def test_revoke_session_success(self):
        """Test successfully revoking a session."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        session_id = uuid4()

        # Mock successful revoke
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db_session.execute.return_value = mock_result

        success = await repo.revoke(session_id)

        assert success is True
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_session_not_found(self):
        """Test revoking non-existent session."""
        mock_db_session = AsyncMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        session_id = uuid4()

        # Mock not found
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db_session.execute.return_value = mock_result

        success = await repo.revoke(session_id)

        assert success is False


class TestSessionRepositoryConversions:
    """Tests for entity/model conversion methods."""

    def test_to_model_conversion(self):
        """Test converting UserSession entity to model."""
        mock_db_session = MagicMock()
        repo = SQLAlchemySessionRepository(mock_db_session)

        session_entity = UserSession(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            refresh_token_hash="test_hash",
            device_name="iPhone 14",
            device_type="mobile",
            browser="Safari",
            os="iOS",
            ip_address="10.0.0.1",
            is_revoked=False,
            revoked_at=None,
            last_activity=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        # Call _to_model
        model = repo._to_model(session_entity)

        # Verify all fields are correctly mapped
        assert model.id == session_entity.id
        assert model.tenant_id == session_entity.tenant_id
        assert model.user_id == session_entity.user_id
        assert model.refresh_token_hash == session_entity.refresh_token_hash
        assert model.device_name == session_entity.device_name
        assert model.device_type == session_entity.device_type
        assert model.browser == session_entity.browser
        assert model.os == session_entity.os
        assert model.ip_address == session_entity.ip_address
        assert model.is_revoked == session_entity.is_revoked
        assert model.revoked_at == session_entity.revoked_at
        assert model.last_activity == session_entity.last_activity
        assert model.created_at == session_entity.created_at
