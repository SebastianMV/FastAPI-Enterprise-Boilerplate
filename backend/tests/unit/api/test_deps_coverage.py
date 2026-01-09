# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for api deps to improve coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import require_permission, get_current_user_id


class TestRequirePermission:
    """Tests for require_permission dependency."""

    @pytest.mark.asyncio
    async def test_require_permission_superuser(self) -> None:
        """Test that superusers bypass permission checks."""
        checker = require_permission("users", "write")
        
        mock_session = AsyncMock()
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        user_id = uuid4()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": True,
            }
            
            result = await checker(
                credentials=mock_credentials,
                session=mock_session,
            )
            
            assert result == user_id

    @pytest.mark.asyncio
    async def test_require_permission_missing_token(self) -> None:
        """Test permission check without token."""
        checker = require_permission("users", "read")
        
        mock_session = AsyncMock()
        
        with pytest.raises(HTTPException) as exc:
            await checker(
                credentials=None,
                session=mock_session,
            )
        
        assert exc.value.status_code == 401
        assert "MISSING_TOKEN" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_require_permission_invalid_token(self) -> None:
        """Test permission check with invalid token."""
        from app.infrastructure.auth.jwt_handler import AuthenticationError
        
        checker = require_permission("users", "read")
        
        mock_session = AsyncMock()
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.side_effect = AuthenticationError(
                code="INVALID_TOKEN",
                message="Invalid token"
            )
            
            with pytest.raises(HTTPException) as exc:
                await checker(
                    credentials=mock_credentials,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_permission_user_not_found(self) -> None:
        """Test permission check when user not found."""
        checker = require_permission("users", "read")
        
        mock_session = AsyncMock()
        mock_session.get.return_value = None  # User not found
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        user_id = uuid4()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": False,
            }
            
            with pytest.raises(HTTPException) as exc:
                await checker(
                    credentials=mock_credentials,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 401
            assert "USER_NOT_FOUND" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_require_permission_user_inactive(self) -> None:
        """Test permission check when user is inactive."""
        checker = require_permission("users", "read")
        
        mock_session = AsyncMock()
        
        mock_user = MagicMock()
        mock_user.is_active = False
        mock_session.get.return_value = mock_user
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        user_id = uuid4()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": False,
            }
            
            with pytest.raises(HTTPException) as exc:
                await checker(
                    credentials=mock_credentials,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 403
            assert "ACCOUNT_DISABLED" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_require_permission_no_roles(self) -> None:
        """Test permission check when user has no roles."""
        checker = require_permission("users", "read")
        
        mock_session = AsyncMock()
        
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.roles = []  # No roles
        mock_session.get.return_value = mock_user
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        user_id = uuid4()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": False,
            }
            
            with pytest.raises(HTTPException) as exc:
                await checker(
                    credentials=mock_credentials,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 403
            assert "Permission denied" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_require_permission_with_permission(self) -> None:
        """Test permission check when user has the permission."""
        checker = require_permission("users", "read")
        
        mock_session = AsyncMock()
        
        role_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.roles = [role_id]
        mock_session.get.return_value = mock_user
        
        # Mock role with permission
        mock_role = MagicMock()
        mock_role.permissions = ["users:read"]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_role]
        mock_session.execute.return_value = mock_result
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        user_id = uuid4()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": False,
            }
            
            result = await checker(
                credentials=mock_credentials,
                session=mock_session,
            )
            
            assert result == user_id

    @pytest.mark.asyncio
    async def test_require_permission_wildcard_resource(self) -> None:
        """Test permission check with wildcard resource permission."""
        checker = require_permission("users", "read")
        
        mock_session = AsyncMock()
        
        role_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.roles = [role_id]
        mock_session.get.return_value = mock_user
        
        # Mock role with wildcard permission
        mock_role = MagicMock()
        mock_role.permissions = ["*:read"]  # All resources, read action
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_role]
        mock_session.execute.return_value = mock_result
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        user_id = uuid4()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": False,
            }
            
            result = await checker(
                credentials=mock_credentials,
                session=mock_session,
            )
            
            assert result == user_id

    @pytest.mark.asyncio
    async def test_require_permission_wildcard_action(self) -> None:
        """Test permission check with wildcard action permission."""
        checker = require_permission("users", "read")
        
        mock_session = AsyncMock()
        
        role_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.roles = [role_id]
        mock_session.get.return_value = mock_user
        
        # Mock role with wildcard permission
        mock_role = MagicMock()
        mock_role.permissions = ["users:*"]  # Users resource, all actions
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_role]
        mock_session.execute.return_value = mock_result
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        user_id = uuid4()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": False,
            }
            
            result = await checker(
                credentials=mock_credentials,
                session=mock_session,
            )
            
            assert result == user_id

    @pytest.mark.asyncio
    async def test_require_permission_full_wildcard(self) -> None:
        """Test permission check with full wildcard permission."""
        checker = require_permission("users", "read")
        
        mock_session = AsyncMock()
        
        role_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.roles = [role_id]
        mock_session.get.return_value = mock_user
        
        # Mock role with full wildcard permission (admin)
        mock_role = MagicMock()
        mock_role.permissions = ["*:*"]  # All resources, all actions
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_role]
        mock_session.execute.return_value = mock_result
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        user_id = uuid4()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": False,
            }
            
            result = await checker(
                credentials=mock_credentials,
                session=mock_session,
            )
            
            assert result == user_id

    @pytest.mark.asyncio
    async def test_require_permission_no_matching_permission(self) -> None:
        """Test permission check when user has roles but no matching permission."""
        checker = require_permission("users", "delete")
        
        mock_session = AsyncMock()
        
        role_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.roles = [role_id]
        mock_session.get.return_value = mock_user
        
        # Mock role without the required permission
        mock_role = MagicMock()
        mock_role.permissions = ["users:read", "users:write"]  # No delete
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_role]
        mock_session.execute.return_value = mock_result
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        user_id = uuid4()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": False,
            }
            
            with pytest.raises(HTTPException) as exc:
                await checker(
                    credentials=mock_credentials,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 403
            assert "Permission denied" in str(exc.value.detail)


class TestGetCurrentUserId:
    """Tests for get_current_user_id dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_id_valid(self) -> None:
        """Test getting current user ID with valid token."""
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        user_id = uuid4()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
            }
            
            result = await get_current_user_id(credentials=mock_credentials)
            
            assert result == user_id

    @pytest.mark.asyncio
    async def test_get_current_user_id_missing_token(self) -> None:
        """Test getting current user ID without token."""
        with pytest.raises(HTTPException) as exc:
            await get_current_user_id(credentials=None)
        
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_token(self) -> None:
        """Test getting current user ID with invalid token."""
        from app.infrastructure.auth.jwt_handler import AuthenticationError
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.side_effect = AuthenticationError(
                code="INVALID_TOKEN",
                message="Invalid token"
            )
            
            with pytest.raises(HTTPException) as exc:
                await get_current_user_id(credentials=mock_credentials)
            
            assert exc.value.status_code == 401
