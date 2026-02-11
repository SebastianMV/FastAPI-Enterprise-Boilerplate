# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for audit log endpoints to improve coverage.
Target: app/api/v1/endpoints/audit_logs.py from 44% to 85%+
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.domain.entities.audit_log import AuditAction, AuditLog, AuditResourceType


@pytest.fixture
def mock_audit_logs():
    """Mock audit log entities."""
    tenant_id = uuid4()
    user_id = uuid4()
    return [
        AuditLog(
            id=uuid4(),
            tenant_id=tenant_id,
            timestamp=datetime.now(UTC),
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.USER,
            resource_id=str(uuid4()),
            resource_name="test@example.com",
            actor_id=user_id,
            actor_email="admin@example.com",
            actor_ip="192.168.1.1",
            actor_user_agent="Mozilla/5.0",
            old_value=None,
            new_value={"email": "test@example.com"},
            metadata={"source": "api"},
            reason=None,
        ),
        AuditLog(
            id=uuid4(),
            tenant_id=tenant_id,
            timestamp=datetime.now(UTC),
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.ROLE,
            resource_id=str(uuid4()),
            resource_name="admin",
            actor_id=user_id,
            actor_email="admin@example.com",
            actor_ip="192.168.1.1",
            actor_user_agent="Mozilla/5.0",
            old_value={"name": "user"},
            new_value={"name": "admin"},
            metadata={},
            reason="Permission change",
        ),
    ]


class TestListAuditLogs:
    """Tests for list_audit_logs endpoint."""

    @pytest.mark.asyncio
    async def test_list_audit_logs_success(self, mock_audit_logs):
        """Test listing audit logs successfully."""
        from app.api.v1.endpoints.audit_logs import list_audit_logs

        tenant_id = mock_audit_logs[0].tenant_id
        user_id = uuid4()
        mock_repo = AsyncMock()
        mock_repo.list_by_tenant.return_value = mock_audit_logs
        mock_repo.count_by_tenant.return_value = 2

        result = await list_audit_logs(
            current_user_id=user_id,
            tenant_id=tenant_id,
            skip=0,
            limit=50,
            action=None,
            resource_type=None,
            start_date=None,
            end_date=None,
            repo=mock_repo,
        )

        assert result.total == 2
        assert len(result.items) == 2
        assert result.skip == 0
        assert result.limit == 50

    @pytest.mark.asyncio
    async def test_list_audit_logs_no_tenant(self):
        """Test listing audit logs without tenant context."""
        from app.api.v1.endpoints.audit_logs import list_audit_logs

        user_id = uuid4()
        mock_repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await list_audit_logs(
                current_user_id=user_id,
                tenant_id=None,
                skip=0,
                limit=50,
                action=None,
                resource_type=None,
                start_date=None,
                end_date=None,
                repo=mock_repo,
            )

        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "NO_TENANT" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_list_audit_logs_invalid_action(self):
        """Test listing audit logs with invalid action filter."""
        from app.api.v1.endpoints.audit_logs import list_audit_logs

        tenant_id = uuid4()
        user_id = uuid4()
        mock_repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await list_audit_logs(
                current_user_id=user_id,
                tenant_id=tenant_id,
                skip=0,
                limit=50,
                action="INVALID_ACTION",
                resource_type=None,
                start_date=None,
                end_date=None,
                repo=mock_repo,
            )

        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "INVALID_ACTION" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_list_audit_logs_invalid_resource_type(self):
        """Test listing audit logs with invalid resource type filter."""
        from app.api.v1.endpoints.audit_logs import list_audit_logs

        tenant_id = uuid4()
        user_id = uuid4()
        mock_repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await list_audit_logs(
                current_user_id=user_id,
                tenant_id=tenant_id,
                skip=0,
                limit=50,
                action=None,
                resource_type="INVALID_TYPE",
                start_date=None,
                end_date=None,
                repo=mock_repo,
            )

        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "INVALID_RESOURCE_TYPE" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_list_audit_logs_with_filters(self, mock_audit_logs):
        """Test listing audit logs with date filters."""
        from app.api.v1.endpoints.audit_logs import list_audit_logs

        tenant_id = mock_audit_logs[0].tenant_id
        user_id = uuid4()
        mock_repo = AsyncMock()
        mock_repo.list_by_tenant.return_value = [mock_audit_logs[0]]
        mock_repo.count_by_tenant.return_value = 1

        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 31, tzinfo=UTC)

        result = await list_audit_logs(
            current_user_id=user_id,
            tenant_id=tenant_id,
            skip=0,
            limit=50,
            action="CREATE",
            resource_type="user",
            start_date=start_date,
            end_date=end_date,
            repo=mock_repo,
        )

        assert result.total == 1
        mock_repo.list_by_tenant.assert_awaited_once()


class TestGetMyActivity:
    """Tests for get_my_activity endpoint."""

    @pytest.mark.asyncio
    async def test_get_my_activity_success(self, mock_audit_logs):
        """Test getting user's own activity."""
        from app.api.v1.endpoints.audit_logs import get_my_activity

        user_id = mock_audit_logs[0].actor_id
        mock_repo = AsyncMock()
        mock_repo.list_by_actor.return_value = mock_audit_logs

        result = await get_my_activity(
            current_user_id=user_id,
            skip=0,
            limit=50,
            start_date=None,
            end_date=None,
            repo=mock_repo,
        )

        assert len(result.items) == 2
        mock_repo.list_by_actor.assert_awaited_once_with(
            actor_id=user_id,
            limit=50,
            offset=0,
            start_date=None,
            end_date=None,
        )


class TestGetRecentLogins:
    """Tests for get_recent_logins endpoint."""

    @pytest.mark.asyncio
    async def test_get_recent_logins_success(self, mock_audit_logs):
        """Test getting recent login attempts."""
        from app.api.v1.endpoints.audit_logs import get_recent_logins

        tenant_id = mock_audit_logs[0].tenant_id
        user_id = uuid4()
        mock_repo = AsyncMock()
        mock_repo.list_recent_logins.return_value = mock_audit_logs

        result = await get_recent_logins(
            current_user_id=user_id,
            tenant_id=tenant_id,
            limit=50,
            include_failed=True,
            repo=mock_repo,
        )

        assert len(result.items) == 2
        mock_repo.list_recent_logins.assert_awaited_once_with(
            tenant_id=tenant_id,
            limit=50,
            include_failed=True,
        )


class TestGetResourceHistory:
    """Tests for get_resource_history endpoint."""

    @pytest.mark.asyncio
    async def test_get_resource_history_success(self, mock_audit_logs):
        """Test getting resource history."""
        from app.api.v1.endpoints.audit_logs import get_resource_history

        user_id = uuid4()
        resource_id = str(uuid4())
        mock_repo = AsyncMock()
        mock_repo.list_by_resource.return_value = mock_audit_logs

        result = await get_resource_history(
            resource_type="user",
            resource_id=resource_id,
            current_user_id=user_id,
            skip=0,
            limit=50,
            repo=mock_repo,
        )

        assert len(result.items) == 2
        mock_repo.list_by_resource.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_resource_history_invalid_type(self):
        """Test getting resource history with invalid type."""
        from app.api.v1.endpoints.audit_logs import get_resource_history

        user_id = uuid4()
        resource_id = str(uuid4())
        mock_repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await get_resource_history(
                resource_type="INVALID",
                resource_id=resource_id,
                current_user_id=user_id,
                skip=0,
                limit=50,
                repo=mock_repo,
            )

        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "INVALID_RESOURCE_TYPE" in str(exc.value.detail)


class TestGetAuditLog:
    """Tests for get_audit_log endpoint."""

    @pytest.mark.asyncio
    async def test_get_audit_log_success(self, mock_audit_logs):
        """Test getting specific audit log by ID."""
        from app.api.v1.endpoints.audit_logs import get_audit_log

        audit_log = mock_audit_logs[0]
        user_id = uuid4()
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = audit_log

        result = await get_audit_log(
            audit_id=audit_log.id,
            current_user_id=user_id,
            repo=mock_repo,
        )

        assert result.id == audit_log.id
        assert result.action == audit_log.action.value

    @pytest.mark.asyncio
    async def test_get_audit_log_not_found(self):
        """Test getting non-existent audit log."""
        from app.api.v1.endpoints.audit_logs import get_audit_log

        audit_id = uuid4()
        user_id = uuid4()
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await get_audit_log(
                audit_id=audit_id,
                current_user_id=user_id,
                repo=mock_repo,
            )

        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
        assert "NOT_FOUND" in str(exc.value.detail)


class TestListActions:
    """Tests for list_actions endpoint."""

    @pytest.mark.asyncio
    async def test_list_actions(self):
        """Test listing available audit actions."""
        from app.api.v1.endpoints.audit_logs import list_actions

        user_id = uuid4()

        result = await list_actions(current_user_id=user_id)

        assert isinstance(result, list)
        assert len(result) > 0
        assert "CREATE" in result
        assert "UPDATE" in result
        assert "DELETE" in result


class TestListResourceTypes:
    """Tests for list_resource_types endpoint."""

    @pytest.mark.asyncio
    async def test_list_resource_types(self):
        """Test listing available resource types."""
        from app.api.v1.endpoints.audit_logs import list_resource_types

        user_id = uuid4()

        result = await list_resource_types(current_user_id=user_id)

        assert isinstance(result, list)
        assert len(result) > 0
        assert "user" in result
        assert "role" in result
