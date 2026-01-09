# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for FastAPI dependency injection utilities.

Tests for authentication and authorization dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import (
    get_current_user_id,
    get_current_tenant_id,
    require_superuser,
    require_permission,
    get_current_user,
    security,
)
from app.domain.exceptions.base import AuthenticationError


class TestSecurity:
    """Tests for security scheme."""

    def test_security_scheme_exists(self) -> None:
        """Test HTTPBearer security scheme is configured."""
        assert security is not None

    def test_security_auto_error_disabled(self) -> None:
        """Test auto_error is disabled for optional auth."""
        assert security.auto_error is False


class TestGetCurrentUserId:
    """Tests for get_current_user_id dependency."""

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self) -> None:
        """Test missing credentials raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(None)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "MISSING_TOKEN"

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id(self) -> None:
        """Test valid token returns user ID."""
        user_id = uuid4()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {"sub": str(user_id)}
            
            result = await get_current_user_id(credentials)
            
            assert result == user_id

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self) -> None:
        """Test invalid token raises 401."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.side_effect = AuthenticationError(
                message="Token expired",
                code="TOKEN_EXPIRED"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(credentials)
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail["code"] == "TOKEN_EXPIRED"


class TestGetCurrentTenantId:
    """Tests for get_current_tenant_id dependency."""

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_none(self) -> None:
        """Test missing credentials returns None."""
        result = await get_current_tenant_id(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_with_tenant_returns_tenant_id(self) -> None:
        """Test valid token with tenant returns tenant ID."""
        tenant_id = uuid4()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {"sub": str(uuid4()), "tenant_id": str(tenant_id)}
            
            result = await get_current_tenant_id(credentials)
            
            assert result == tenant_id

    @pytest.mark.asyncio
    async def test_valid_token_without_tenant_returns_none(self) -> None:
        """Test valid token without tenant returns None."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {"sub": str(uuid4())}
            
            result = await get_current_tenant_id(credentials)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self) -> None:
        """Test invalid token returns None instead of raising."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.side_effect = AuthenticationError("Invalid", "INVALID")
            
            result = await get_current_tenant_id(credentials)
            
            assert result is None


class TestRequireSuperuser:
    """Tests for require_superuser dependency."""

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self) -> None:
        """Test missing credentials raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await require_superuser(None)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_superuser_returns_user_id(self) -> None:
        """Test superuser token returns user ID."""
        user_id = uuid4()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="superuser_token"
        )
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": True
            }
            
            result = await require_superuser(credentials)
            
            assert result == user_id

    @pytest.mark.asyncio
    async def test_non_superuser_raises_403(self) -> None:
        """Test non-superuser raises 403."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="regular_token"
        )
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(uuid4()),
                "is_superuser": False
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await require_superuser(credentials)
            
            assert exc_info.value.status_code == 403
            assert "Superuser" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self) -> None:
        """Test invalid token raises 401."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid"
        )
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.side_effect = AuthenticationError("Expired", "EXPIRED")
            
            with pytest.raises(HTTPException) as exc_info:
                await require_superuser(credentials)
            
            assert exc_info.value.status_code == 401


class TestRequirePermission:
    """Tests for require_permission dependency factory."""

    def test_returns_callable(self) -> None:
        """Test require_permission returns a callable dependency."""
        checker = require_permission("users", "read")
        assert callable(checker)

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self) -> None:
        """Test missing credentials raises 401."""
        checker = require_permission("users", "read")
        mock_session = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(None, mock_session)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_superuser_bypasses_permission_check(self) -> None:
        """Test superuser bypasses permission check."""
        checker = require_permission("users", "delete")
        user_id = uuid4()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="superuser_token"
        )
        mock_session = AsyncMock()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": True
            }
            
            result = await checker(credentials, mock_session)
            
            assert result == user_id

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self) -> None:
        """Test invalid token raises 401."""
        checker = require_permission("users", "read")
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid"
        )
        mock_session = AsyncMock()
        
        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.side_effect = AuthenticationError("Invalid", "INVALID")
            
            with pytest.raises(HTTPException) as exc_info:
                await checker(credentials, mock_session)
            
            assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self) -> None:
        """Test user not found raises 401."""
        user_id = uuid4()
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(user_id, mock_session)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_user_found_returns_user_entity(self) -> None:
        """Test user found returns User domain entity."""
        user_id = uuid4()
        tenant_id = uuid4()
        
        mock_user_model = MagicMock()
        mock_user_model.id = user_id
        mock_user_model.tenant_id = tenant_id
        mock_user_model.email = "test@example.com"
        mock_user_model.password_hash = "hashed"
        mock_user_model.first_name = "John"
        mock_user_model.last_name = "Doe"
        mock_user_model.is_active = True
        mock_user_model.is_superuser = False
        mock_user_model.roles = []
        mock_user_model.last_login = None
        mock_user_model.created_at = None
        mock_user_model.updated_at = None
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_user_model
        
        result = await get_current_user(user_id, mock_session)
        
        assert result.id == user_id
        assert str(result.email) == "test@example.com"
        assert result.first_name == "John"
        assert result.last_name == "Doe"


class TestTypeAliases:
    """Tests for type aliases."""

    def test_type_aliases_exist(self) -> None:
        """Test type aliases are defined."""
        from app.api.deps import (
            CurrentUserId,
            CurrentTenantId,
            CurrentUser,
            SuperuserId,
            DbSession,
        )
        
        assert CurrentUserId is not None
        assert CurrentTenantId is not None
        assert CurrentUser is not None
        assert SuperuserId is not None
        assert DbSession is not None
