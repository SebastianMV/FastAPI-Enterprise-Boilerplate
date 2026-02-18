# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for MFA endpoints and config service.
Covers helper functions in mfa_config_service and endpoint logic in mfa.py.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.entities.mfa import MFAConfig


class TestMFAHelperFunctions:
    """Tests for MFA helper functions in mfa_config_service."""

    @pytest.mark.asyncio
    async def test_get_redis_returns_cache(self):
        """Test _get_redis returns cache from get_cache()."""
        with patch("app.infrastructure.cache.get_cache") as mock_get_cache:
            mock_cache = MagicMock()
            mock_get_cache.return_value = mock_cache

            from app.application.services.mfa_config_service import _get_redis

            result = await _get_redis()

            mock_get_cache.assert_called_once()
            assert result == mock_cache

    def test_mfa_config_to_dict_converts_config(self):
        """Test _mfa_config_to_dict converts MFAConfig to dict."""
        with patch(
            "app.infrastructure.auth.encryption.encrypt_value",
            side_effect=lambda v: f"enc:{v}",
        ):
            from app.application.services.mfa_config_service import (
                _mfa_config_to_dict,
            )

            user_id = uuid4()
            config = MFAConfig(
                user_id=user_id,
                secret="ABCD1234",
                is_enabled=True,
                backup_codes=["code1", "code2"],
            )

            result = _mfa_config_to_dict(config)

            assert result["user_id"] == str(user_id)
            assert result["secret"] == "enc:ABCD1234"
            assert result["is_enabled"] is True
            assert result["backup_codes"] == ["code1", "code2"]

    def test_dict_to_mfa_config_converts_dict(self):
        """Test _dict_to_mfa_config converts dict to MFAConfig."""
        with patch(
            "app.infrastructure.auth.encryption.decrypt_value",
            side_effect=lambda v: v.replace("enc:", ""),
        ):
            from app.application.services.mfa_config_service import (
                _dict_to_mfa_config,
            )

            user_id = uuid4()
            data = {
                "user_id": str(user_id),
                "secret": "enc:EFGH5678",
                "is_enabled": False,
                "backup_codes": ["code3", "code4"],
                "enabled_at": None,
                "last_used_at": None,
            }

            result = _dict_to_mfa_config(data)

            assert result.user_id == user_id
            assert result.secret == "EFGH5678"
            assert result.is_enabled is False
            assert result.backup_codes == ["code3", "code4"]

    def test_dict_to_mfa_config_with_last_used_at(self):
        """Test _dict_to_mfa_config handles last_used_at field."""
        with patch(
            "app.infrastructure.auth.encryption.decrypt_value",
            side_effect=lambda v: v.replace("enc:", ""),
        ):
            from app.application.services.mfa_config_service import (
                _dict_to_mfa_config,
            )

            user_id = uuid4()
            data = {
                "user_id": str(user_id),
                "secret": "enc:ABCD1234",
                "is_enabled": True,
                "backup_codes": [],
                "enabled_at": "2025-01-02T10:00:00+00:00",
                "last_used_at": "2025-01-15T14:30:00+00:00",
            }

            result = _dict_to_mfa_config(data)

            assert result.user_id == user_id
            assert result.is_enabled is True
            assert result.enabled_at is not None
            assert result.last_used_at is not None

    @pytest.mark.asyncio
    async def test_get_mfa_config_returns_none_when_not_found(self):
        """Test get_mfa_config returns None when no config in cache or DB."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "app.application.services.mfa_config_service._get_redis",
                return_value=mock_cache,
            ),
            patch(
                "app.infrastructure.database.connection.async_session_maker",
                return_value=mock_session,
            ),
        ):
            from app.application.services.mfa_config_service import get_mfa_config

            result = await get_mfa_config(str(uuid4()))

            assert result is None

    @pytest.mark.asyncio
    async def test_get_mfa_config_returns_config_from_cache(self):
        """Test get_mfa_config returns MFAConfig from Redis cache."""
        user_id = uuid4()
        config_data = {
            "user_id": str(user_id),
            "secret": "enc:SECRET123",
            "is_enabled": True,
            "backup_codes": [],
            "enabled_at": "2025-01-02T00:00:00+00:00",
            "last_used_at": None,
        }

        mock_cache = AsyncMock()
        mock_cache.get.return_value = json.dumps(config_data)

        with (
            patch(
                "app.application.services.mfa_config_service._get_redis",
                return_value=mock_cache,
            ),
            patch(
                "app.infrastructure.auth.encryption.decrypt_value",
                side_effect=lambda v: v.replace("enc:", ""),
            ),
        ):
            from app.application.services.mfa_config_service import get_mfa_config

            result = await get_mfa_config(str(user_id))

            assert result is not None
            assert result.user_id == user_id
            assert result.secret == "SECRET123"
            assert result.is_enabled is True

    @pytest.mark.asyncio
    async def test_save_mfa_config_persists_to_db_and_cache(self):
        """Test save_mfa_config writes to DB and updates Redis cache."""
        user_id = uuid4()
        config = MFAConfig(
            user_id=user_id,
            secret="SAVESECRET",
            is_enabled=True,
            backup_codes=["backup1"],
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        mock_cache = AsyncMock()

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker",
                return_value=mock_session,
            ),
            patch(
                "app.application.services.mfa_config_service._get_redis",
                return_value=mock_cache,
            ),
            patch(
                "app.infrastructure.auth.encryption.encrypt_value",
                side_effect=lambda v: f"enc:{v}",
            ),
        ):
            from app.application.services.mfa_config_service import save_mfa_config

            await save_mfa_config(config)

            mock_session.add.assert_called_once()
            mock_session.commit.assert_awaited_once()
            mock_cache.set.assert_awaited_once()


class TestMFADisableFlow:
    """Tests for MFA disable endpoint."""

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

        with patch(
            "app.api.v1.endpoints.mfa.get_mfa_config",
            new_callable=AsyncMock,
            return_value=None,
        ):
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

        mock_config = MagicMock()
        mock_config.is_enabled = False

        with patch(
            "app.api.v1.endpoints.mfa.get_mfa_config",
            new_callable=AsyncMock,
            return_value=mock_config,
        ):
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

        mock_config = MFAConfig(user_id=mock_user.id, secret="SECRET", is_enabled=True)

        with patch(
            "app.api.v1.endpoints.mfa.get_mfa_config",
            new_callable=AsyncMock,
            return_value=mock_config,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await disable_mfa(
                    request=request,
                    current_user=mock_user,
                    mfa_service=mock_mfa_service,
                )

            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["code"] == "INVALID_CODE"

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

        mock_config = MFAConfig(user_id=mock_user.id, secret="SECRET", is_enabled=True)

        with (
            patch(
                "app.api.v1.endpoints.mfa.get_mfa_config",
                new_callable=AsyncMock,
                return_value=mock_config,
            ),
            patch(
                "app.api.v1.endpoints.mfa.save_mfa_config",
                new_callable=AsyncMock,
            ) as mock_save,
        ):
            result = await disable_mfa(
                request=request, current_user=mock_user, mfa_service=mock_mfa_service
            )

            assert result.success is True
            mock_save.assert_called_once()
