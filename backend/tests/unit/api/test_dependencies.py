# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Tests for API dependencies module."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.exceptions.base import AuthenticationError


def _make_mock_request():
    """Create mock request for dependency injection tests."""

    class _State:
        pass

    mock_req = MagicMock()
    mock_req.cookies = {}
    mock_req.state = _State()
    return mock_req


class TestGetCurrentUserId:
    """Tests for get_current_user_id dependency."""

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self) -> None:
        """Test missing credentials raises 401."""
        from fastapi import HTTPException

        from app.api.deps import get_current_user_id

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(credentials=None, request=_make_mock_request())

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "MISSING_TOKEN"

    @pytest.mark.asyncio
    async def test_valid_credentials_returns_user_id(self) -> None:
        """Test valid credentials returns user ID."""
        from app.api.deps import get_current_user_id

        user_id = uuid4()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {"sub": str(user_id)}
            result = await get_current_user_id(
                credentials=mock_credentials, request=_make_mock_request()
            )

        assert result == user_id

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self) -> None:
        """Test invalid token raises 401."""
        from fastapi import HTTPException

        from app.api.deps import get_current_user_id

        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"

        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.side_effect = AuthenticationError(
                "INVALID_TOKEN", "Token is invalid"
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(
                    credentials=mock_credentials, request=_make_mock_request()
                )

        assert exc_info.value.status_code == 401


class TestGetCurrentTenantId:
    """Tests for get_current_tenant_id dependency."""

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_none(self) -> None:
        """Test missing credentials returns None."""
        from app.api.deps import get_current_tenant_id

        result = await get_current_tenant_id(
            credentials=None, request=_make_mock_request()
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_valid_credentials_with_tenant_returns_tenant_id(self) -> None:
        """Test valid credentials with tenant returns tenant ID."""
        from app.api.deps import get_current_tenant_id

        tenant_id = uuid4()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {"tenant_id": str(tenant_id)}
            result = await get_current_tenant_id(
                credentials=mock_credentials, request=_make_mock_request()
            )

        assert result == tenant_id

    @pytest.mark.asyncio
    async def test_valid_credentials_without_tenant_returns_none(self) -> None:
        """Test valid credentials without tenant returns None."""
        from app.api.deps import get_current_tenant_id

        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {"sub": str(uuid4())}
            result = await get_current_tenant_id(
                credentials=mock_credentials, request=_make_mock_request()
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self) -> None:
        """Test invalid token returns None."""
        from app.api.deps import get_current_tenant_id

        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"

        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.side_effect = AuthenticationError(
                "INVALID_TOKEN", "Token is invalid"
            )
            result = await get_current_tenant_id(
                credentials=mock_credentials, request=_make_mock_request()
            )

        assert result is None


class TestRequireSuperuser:
    """Tests for require_superuser dependency."""

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self) -> None:
        """Test missing credentials raises 401."""
        from fastapi import HTTPException

        from app.api.deps import require_superuser

        with pytest.raises(HTTPException) as exc_info:
            await require_superuser(
                credentials=None,
                request=_make_mock_request(),
                session=AsyncMock(),
            )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_non_superuser_raises_403(self) -> None:
        """Test non-superuser raises 403."""
        from fastapi import HTTPException

        from app.api.deps import require_superuser

        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"
        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_session.get.return_value = mock_user

        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(uuid4()),
                "is_superuser": False,
            }

            with pytest.raises(HTTPException) as exc_info:
                await require_superuser(
                    credentials=mock_credentials,
                    request=_make_mock_request(),
                    session=mock_session,
                )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_superuser_returns_user_id(self) -> None:
        """Test superuser returns user ID."""
        from app.api.deps import require_superuser

        user_id = uuid4()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"
        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.is_superuser = True
        mock_session.get.return_value = mock_user

        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": True,
            }
            result = await require_superuser(
                credentials=mock_credentials,
                request=_make_mock_request(),
                session=mock_session,
            )

        assert result == user_id


class TestRequirePermission:
    """Tests for require_permission dependency factory."""

    def test_require_permission_creates_callable(self) -> None:
        """Test require_permission creates callable."""
        from app.api.deps import require_permission

        checker = require_permission("users", "read")

        assert callable(checker)

    @pytest.mark.asyncio
    async def test_permission_checker_missing_credentials_raises_401(self) -> None:
        """Test permission checker with missing credentials raises 401."""
        from fastapi import HTTPException

        from app.api.deps import require_permission

        checker = require_permission("users", "read")

        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await checker(
                credentials=None,
                request=_make_mock_request(),
                session=mock_session,
            )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_permission_checker_superuser_returns_user_id(self) -> None:
        """Test permission checker with superuser returns user ID."""
        from app.api.deps import require_permission

        checker = require_permission("users", "read")

        user_id = uuid4()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"
        mock_session = AsyncMock()

        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.is_superuser = True
        mock_session.get.return_value = mock_user

        with patch("app.api.deps.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "is_superuser": True,
            }
            result = await checker(
                credentials=mock_credentials,
                request=_make_mock_request(),
                session=mock_session,
            )

        assert result == user_id


class TestSecurityScheme:
    """Tests for security scheme."""

    def test_security_scheme_exists(self) -> None:
        """Test security scheme is defined."""
        from app.api.deps import security

        assert security is not None

    def test_security_scheme_no_auto_error(self) -> None:
        """Test security scheme has auto_error False."""
        from app.api.deps import security

        # HTTPBearer with auto_error=False
        assert security.auto_error is False


class TestTypeAnnotations:
    """Tests for type annotation helpers."""

    def test_current_user_id_type(self) -> None:
        """Test CurrentUserId type alias exists."""
        from app.api.deps import CurrentUserId

        assert CurrentUserId is not None

    def test_current_tenant_id_type(self) -> None:
        """Test CurrentTenantId type alias exists."""
        from app.api.deps import CurrentTenantId

        assert CurrentTenantId is not None

    def test_superuser_id_type(self) -> None:
        """Test SuperuserId type alias exists."""
        from app.api.deps import SuperuserId

        assert SuperuserId is not None

    def test_db_session_type(self) -> None:
        """Test DbSession type alias exists."""
        from app.api.deps import DbSession

        assert DbSession is not None
