# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for MFA endpoints to achieve 100% coverage.
Focuses on 14 uncovered lines in app/api/v1/endpoints/mfa.py
"""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.entities.mfa import MFAConfig


class TestMFAHelperFunctions:
    """Tests for MFA helper functions (lines 42-92)."""

    def test_get_redis_returns_client(self):
        """Test _get_redis returns Redis client from URL."""
        with (
            patch("app.api.v1.endpoints.mfa.settings") as mock_settings,
            patch("app.api.v1.endpoints.mfa.redis.from_url") as mock_from_url,
        ):
            mock_settings.redis_url = "redis://localhost:6379"
            mock_client = MagicMock()
            mock_from_url.return_value = mock_client

            from app.api.v1.endpoints.mfa import _get_redis

            result = _get_redis()

            mock_from_url.assert_called_once_with(
                "redis://localhost:6379", decode_responses=True
            )
            assert result == mock_client

    def test_mfa_config_to_dict_converts_config(self):
        """Test _mfa_config_to_dict converts MFAConfig to dict."""
        from app.api.v1.endpoints.mfa import _mfa_config_to_dict

        user_id = uuid4()
        config_id = uuid4()
        config = MFAConfig(
            id=config_id,
            user_id=user_id,
            secret="ABCD1234",
            is_enabled=True,
            backup_codes=["code1", "code2"],
        )

        result = _mfa_config_to_dict(config)

        assert result["user_id"] == str(user_id)
        assert result["secret"] == "ABCD1234"
        assert result["is_enabled"] == True
        assert result["backup_codes"] == ["code1", "code2"]

    def test_dict_to_mfa_config_converts_dict(self):
        """Test _dict_to_mfa_config converts dict to MFAConfig."""
        from app.api.v1.endpoints.mfa import _dict_to_mfa_config

        user_id = uuid4()
        config_id = uuid4()
        data = {
            "id": str(config_id),
            "user_id": str(user_id),
            "secret": "EFGH5678",
            "is_enabled": False,
            "backup_codes": ["code3", "code4"],
            "created_at": "2025-01-01T00:00:00+00:00",
            "enabled_at": None,
            "last_used_at": None,
        }

        result = _dict_to_mfa_config(data)

        assert result.user_id == user_id
        assert result.secret == "EFGH5678"
        assert result.is_enabled == False
        assert result.backup_codes == ["code3", "code4"]

    def test_dict_to_mfa_config_with_last_used_at(self):
        """Test _dict_to_mfa_config handles last_used_at field."""
        from app.api.v1.endpoints.mfa import _dict_to_mfa_config

        user_id = uuid4()
        config_id = uuid4()
        data = {
            "id": str(config_id),
            "user_id": str(user_id),
            "secret": "ABCD1234",
            "is_enabled": True,
            "backup_codes": [],
            "created_at": "2025-01-01T00:00:00+00:00",
            "enabled_at": "2025-01-02T10:00:00+00:00",
            "last_used_at": "2025-01-15T14:30:00+00:00",
        }

        result = _dict_to_mfa_config(data)

        assert result.user_id == user_id
        assert result.is_enabled == True
        assert result.enabled_at is not None
        assert result.last_used_at is not None

    def test_get_mfa_config_returns_none_when_not_found(self):
        """Test get_mfa_config returns None when no config exists."""
        with patch("app.api.v1.endpoints.mfa._get_redis") as mock_get_redis:
            mock_redis = MagicMock()
            mock_redis.get.return_value = None
            mock_get_redis.return_value = mock_redis

            from app.api.v1.endpoints.mfa import get_mfa_config

            result = get_mfa_config(str(uuid4()))

            assert result is None

    def test_get_mfa_config_returns_config_when_found(self):
        """Test get_mfa_config returns MFAConfig when exists."""
        user_id = uuid4()
        config_id = uuid4()
        config_data = {
            "id": str(config_id),
            "user_id": str(user_id),
            "secret": "SECRET123",
            "is_enabled": True,
            "backup_codes": [],
            "created_at": "2025-01-01T00:00:00+00:00",
            "enabled_at": "2025-01-02T00:00:00+00:00",
            "last_used_at": None,
        }

        with patch("app.api.v1.endpoints.mfa._get_redis") as mock_get_redis:
            mock_redis = MagicMock()
            mock_redis.get.return_value = json.dumps(config_data)
            mock_get_redis.return_value = mock_redis

            from app.api.v1.endpoints.mfa import get_mfa_config

            result = get_mfa_config(str(user_id))

            assert result.user_id == user_id
            assert result.secret == "SECRET123"
            assert result.is_enabled == True

    def test_save_mfa_config_stores_in_redis(self):
        """Test save_mfa_config stores config in Redis with TTL."""
        user_id = uuid4()
        config = MFAConfig(
            user_id=user_id,
            secret="SAVESECRET",
            is_enabled=True,
            backup_codes=["backup1"],
        )

        with patch("app.api.v1.endpoints.mfa._get_redis") as mock_get_redis:
            mock_redis = MagicMock()
            mock_get_redis.return_value = mock_redis

            from app.api.v1.endpoints.mfa import save_mfa_config

            save_mfa_config(config)

            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][0] == f"mfa:config:{user_id}"
            assert call_args[0][1] == 60 * 60 * 24 * 30  # 30 days


class TestMFADisableFlow:
    """Tests for MFA disable endpoint (line 233)."""

    @pytest.mark.asyncio
    async def test_disable_mfa_not_enabled(self):
        """Test disable MFA when MFA not enabled."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.mfa import disable_mfa
        from app.api.v1.schemas.mfa import MFADisableRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_mfa_service = MagicMock()

        request = MFADisableRequest(password="password123", code="123456")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await disable_mfa(
                    request=request,
                    current_user=mock_user,
                    mfa_service=mock_mfa_service,
                )

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_disable_mfa_config_not_enabled_flag(self):
        """Test disable MFA when config exists but is_enabled=False."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.mfa import disable_mfa
        from app.api.v1.schemas.mfa import MFADisableRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_mfa_service = MagicMock()

        request = MFADisableRequest(password="password123", code="123456")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.is_enabled = False
            mock_get_config.return_value = mock_config

            with pytest.raises(HTTPException) as exc_info:
                await disable_mfa(
                    request=request,
                    current_user=mock_user,
                    mfa_service=mock_mfa_service,
                )

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_disable_mfa_invalid_code(self):
        """Test disable MFA with invalid verification code."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.mfa import disable_mfa
        from app.api.v1.schemas.mfa import MFADisableRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.verify_password.return_value = True

        mock_mfa_service = MagicMock()
        mock_mfa_service.disable_mfa.return_value = False

        request = MFADisableRequest(password="password123", code="000000")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_config = MFAConfig(
                user_id=mock_user.id, secret="SECRET", is_enabled=True
            )
            mock_get_config.return_value = mock_config

            with pytest.raises(HTTPException) as exc_info:
                await disable_mfa(
                    request=request,
                    current_user=mock_user,
                    mfa_service=mock_mfa_service,
                )

            assert exc_info.value.status_code == 400
            assert "Invalid verification code" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_disable_mfa_success(self):
        """Test successful MFA disable."""
        from app.api.v1.endpoints.mfa import disable_mfa
        from app.api.v1.schemas.mfa import MFADisableRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.verify_password.return_value = True

        mock_mfa_service = MagicMock()
        mock_mfa_service.disable_mfa.return_value = True

        request = MFADisableRequest(password="correct_password", code="123456")

        with (
            patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config,
            patch("app.api.v1.endpoints.mfa.save_mfa_config") as mock_save,
        ):
            mock_config = MFAConfig(
                user_id=mock_user.id, secret="SECRET", is_enabled=True
            )
            mock_get_config.return_value = mock_config

            result = await disable_mfa(
                request=request, current_user=mock_user, mfa_service=mock_mfa_service
            )

            assert result.success == True
            mock_save.assert_called_once()
