# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for roles endpoint tenant validation and permissions auth check."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.entities.role import Role


class TestGetRoleTenantValidation:
    """Test that get_role validates tenant ownership."""

    @pytest.mark.asyncio
    async def test_get_role_cross_tenant_returns_404(self):
        """Accessing a role from a different tenant returns 404."""
        from app.api.v1.endpoints.roles import get_role

        role_id = uuid4()
        tenant_a = uuid4()
        tenant_b = uuid4()

        role = Role(
            id=role_id,
            tenant_id=tenant_a,
            name="Editor",
            description="Can edit",
            permissions=[],
            is_system=False,
        )

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = role
        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_role(
                role_id=role_id,
                current_user_id=uuid4(),
                tenant_id=tenant_b,  # Different tenant
                session=mock_session,
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_role_same_tenant_succeeds(self):
        """Accessing a role from the same tenant succeeds."""
        from app.api.v1.endpoints.roles import get_role

        role_id = uuid4()
        tenant = uuid4()

        role = Role(
            id=role_id,
            tenant_id=tenant,
            name="Viewer",
            description="Read only",
            permissions=[],
            is_system=False,
        )

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = role
        mock_session = AsyncMock()

        result = await get_role(
            role_id=role_id,
            current_user_id=uuid4(),
            tenant_id=tenant,  # Same tenant
            session=mock_session,
            repo=mock_repo,
        )

        assert result.name == "Viewer"


class TestGetUserPermissionsAuth:
    """Test that get_user_permissions requires self or superuser."""

    @pytest.mark.asyncio
    async def test_non_superuser_viewing_other_user_denied(self):
        """Non-superuser cannot view another user's permissions."""
        from app.api.v1.endpoints.roles import get_user_permissions

        viewer_id = uuid4()
        target_id = uuid4()

        mock_session = AsyncMock()
        mock_viewer = MagicMock()
        mock_viewer.is_superuser = False
        mock_session.get.return_value = mock_viewer

        with pytest.raises(HTTPException) as exc_info:
            await get_user_permissions(
                user_id=target_id,
                current_user_id=viewer_id,
                tenant_id=None,
                session=mock_session,
            )

        assert exc_info.value.status_code == 403
