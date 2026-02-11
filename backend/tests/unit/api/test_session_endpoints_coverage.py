# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for session endpoints to improve coverage.
Target: app/api/v1/endpoints/sessions.py from 50% to 85%+
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.domain.entities.session import UserSession


@pytest.fixture
def mock_sessions():
    """Mock user sessions."""
    user_id = uuid4()
    tenant_id = uuid4()
    return [
        UserSession(
            id=uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            refresh_token_hash="hash1",
            device_name="Desktop",
            device_type="desktop",
            browser="Chrome",
            os="Windows",
            ip_address="192.168.1.1",
            location="New York, US",
            last_activity=datetime.now(UTC),
            created_at=datetime.now(UTC),
            is_current=False,
            is_revoked=False,
        ),
        UserSession(
            id=uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            refresh_token_hash="hash2",
            device_name="Mobile",
            device_type="mobile",
            browser="Safari",
            os="iOS",
            ip_address="192.168.1.2",
            location="Los Angeles, US",
            last_activity=datetime.now(UTC),
            created_at=datetime.now(UTC),
            is_current=False,
            is_revoked=False,
        ),
    ]


class TestGetCurrentTokenJti:
    """Tests for get_current_token_jti function."""

    def test_get_current_token_jti_no_credentials(self):
        """Test getting JTI with no credentials."""
        from app.api.v1.endpoints.sessions import get_current_token_jti

        result = get_current_token_jti(None)

        assert result is None

    def test_get_current_token_jti_invalid_token(self):
        """Test getting JTI with invalid token."""
        from app.api.v1.endpoints.sessions import get_current_token_jti

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with patch(
            "app.api.v1.endpoints.sessions.validate_access_token"
        ) as mock_validate:
            mock_validate.side_effect = Exception("Invalid token")

            result = get_current_token_jti(credentials)

            assert result is None

    def test_get_current_token_jti_success(self):
        """Test getting JTI successfully."""
        from app.api.v1.endpoints.sessions import get_current_token_jti

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )
        expected_jti = str(uuid4())

        with patch(
            "app.api.v1.endpoints.sessions.validate_access_token"
        ) as mock_validate:
            mock_validate.return_value = {"jti": expected_jti}

            result = get_current_token_jti(credentials)

            assert result == expected_jti


class TestListSessionsEndpoint:
    """Tests for list_sessions endpoint."""

    @pytest.mark.asyncio
    async def test_list_sessions_success(self, mock_sessions):
        """Test listing sessions successfully."""
        from app.api.v1.endpoints.sessions import list_sessions

        user_id = mock_sessions[0].user_id
        mock_db = AsyncMock()

        with patch(
            "app.api.v1.endpoints.sessions.SQLAlchemySessionRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_user_sessions.return_value = mock_sessions
            mock_repo_class.return_value = mock_repo

            result = await list_sessions(
                user_id=user_id, session=mock_db, request=MagicMock(), credentials=None
            )

            assert result.total == 2
            assert len(result.sessions) == 2


class TestRevokeSessionEndpoint:
    """Tests for revoke_session endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_session_success(self, mock_sessions):
        """Test revoking a session successfully."""
        from app.api.v1.endpoints.sessions import revoke_session

        user_id = mock_sessions[0].user_id
        session_id = mock_sessions[0].id
        mock_db = AsyncMock()

        # Different JTI so we don't hit "cannot revoke current session"
        other_jti = str(uuid4())

        with patch(
            "app.api.v1.endpoints.sessions.SQLAlchemySessionRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_sessions[0]
            mock_repo.revoke.return_value = True
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.sessions.get_current_token_jti"
            ) as mock_get_jti:
                mock_get_jti.return_value = other_jti

                result = await revoke_session(
                    session_id=session_id,
                    user_id=user_id,
                    session=mock_db,
                    credentials=None,
                )

                assert result.message == "Session revoked successfully"

    @pytest.mark.asyncio
    async def test_cannot_revoke_current_session(self, mock_sessions):
        """Test that current session cannot be revoked."""
        from app.api.v1.endpoints.sessions import revoke_session

        user_id = mock_sessions[0].user_id
        session_id = mock_sessions[0].id
        mock_db = AsyncMock()

        # Same JTI as session ID to trigger "current session" check
        with patch(
            "app.api.v1.endpoints.sessions.SQLAlchemySessionRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_sessions[0]
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.sessions.get_current_token_jti"
            ) as mock_get_jti:
                mock_get_jti.return_value = str(session_id)

                with pytest.raises(HTTPException) as exc:
                    await revoke_session(
                        session_id=session_id,
                        user_id=user_id,
                        session=mock_db,
                        credentials=None,
                    )

                assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
                assert "CANNOT_REVOKE_CURRENT" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_session(self):
        """Test revoking a nonexistent session."""
        from app.api.v1.endpoints.sessions import revoke_session

        user_id = uuid4()
        session_id = uuid4()
        mock_db = AsyncMock()

        with patch(
            "app.api.v1.endpoints.sessions.SQLAlchemySessionRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.sessions.get_current_token_jti"
            ) as mock_get_jti:
                mock_get_jti.return_value = str(uuid4())

                with pytest.raises(HTTPException) as exc:
                    await revoke_session(
                        session_id=session_id,
                        user_id=user_id,
                        session=mock_db,
                        credentials=None,
                    )

                assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_revoke_other_users_session(self, mock_sessions):
        """Test revoking another user's session."""
        from app.api.v1.endpoints.sessions import revoke_session

        other_user_id = uuid4()
        session_id = mock_sessions[0].id
        mock_db = AsyncMock()

        with patch(
            "app.api.v1.endpoints.sessions.SQLAlchemySessionRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_sessions[0]
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.sessions.get_current_token_jti"
            ) as mock_get_jti:
                mock_get_jti.return_value = str(uuid4())

                with pytest.raises(HTTPException) as exc:
                    await revoke_session(
                        session_id=session_id,
                        user_id=other_user_id,
                        session=mock_db,
                        credentials=None,
                    )

                assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_revoke_already_revoked_session(self, mock_sessions):
        """Test revoking an already revoked session returns 404."""
        from app.api.v1.endpoints.sessions import revoke_session

        user_id = mock_sessions[0].user_id
        session_id = mock_sessions[0].id
        mock_db = AsyncMock()

        with patch(
            "app.api.v1.endpoints.sessions.SQLAlchemySessionRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_sessions[0]
            mock_repo.revoke.return_value = False  # Already revoked
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.sessions.get_current_token_jti"
            ) as mock_get_jti:
                mock_get_jti.return_value = str(uuid4())

                with pytest.raises(HTTPException) as exc:
                    await revoke_session(
                        session_id=session_id,
                        user_id=user_id,
                        session=mock_db,
                        credentials=None,
                    )

                assert exc.value.status_code == status.HTTP_404_NOT_FOUND


class TestRevokeAllSessionsEndpoint:
    """Tests for revoke_all_sessions endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_all_except_current(self):
        """Test revoking all sessions except current."""
        from app.api.v1.endpoints.sessions import revoke_all_sessions

        user_id = uuid4()
        current_jti = str(uuid4())
        mock_db = AsyncMock()

        with patch(
            "app.api.v1.endpoints.sessions.SQLAlchemySessionRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.revoke_all_except.return_value = 3
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.sessions.get_current_token_jti"
            ) as mock_get_jti:
                mock_get_jti.return_value = current_jti

                result = await revoke_all_sessions(
                    user_id=user_id, session=mock_db, credentials=None
                )

                assert result.revoked_count == 3
                mock_repo.revoke_all_except.assert_awaited_once_with(
                    user_id, UUID(current_jti)
                )

    @pytest.mark.asyncio
    async def test_revoke_all_without_current(self):
        """Test revoking all sessions without current JTI."""
        from app.api.v1.endpoints.sessions import revoke_all_sessions

        user_id = uuid4()
        mock_db = AsyncMock()

        with patch(
            "app.api.v1.endpoints.sessions.SQLAlchemySessionRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.revoke_all.return_value = 5
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.sessions.get_current_token_jti"
            ) as mock_get_jti:
                mock_get_jti.return_value = None

                result = await revoke_all_sessions(
                    user_id=user_id, session=mock_db, credentials=None
                )

                assert result.revoked_count == 5
                mock_repo.revoke_all.assert_awaited_once_with(user_id)

    @pytest.mark.asyncio
    async def test_revoke_all_invalid_uuid_jti(self):
        """Test revoking all with invalid UUID JTI."""
        from app.api.v1.endpoints.sessions import revoke_all_sessions

        user_id = uuid4()
        mock_db = AsyncMock()

        with patch(
            "app.api.v1.endpoints.sessions.SQLAlchemySessionRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.revoke_all.return_value = 5
            mock_repo_class.return_value = mock_repo

            with patch(
                "app.api.v1.endpoints.sessions.get_current_token_jti"
            ) as mock_get_jti:
                mock_get_jti.return_value = "not-a-uuid"

                result = await revoke_all_sessions(
                    user_id=user_id, session=mock_db, credentials=None
                )

                assert result.revoked_count == 5
                mock_repo.revoke_all.assert_awaited_once_with(user_id)
