# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for MFA endpoints to improve coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.api.v1.endpoints.mfa import (
    get_mfa_status,
    setup_mfa,
    verify_mfa_setup,
    disable_mfa,
    regenerate_backup_codes,
    validate_mfa_code,
    get_mfa_config,
    save_mfa_config,
    _mfa_configs,
)
from app.api.v1.schemas.mfa import MFAVerifyRequest, MFADisableRequest
from app.domain.entities.mfa import MFAConfig
from app.domain.entities.user import User
from app.domain.value_objects.email import Email


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = Email("test@example.com")
    user.verify_password = MagicMock(return_value=True)
    return user


@pytest.fixture
def mock_mfa_service() -> MagicMock:
    """Create a mock MFA service."""
    service = MagicMock()
    return service


@pytest.fixture(autouse=True)
def clear_mfa_configs():
    """Clear MFA configs before each test."""
    _mfa_configs.clear()
    yield
    _mfa_configs.clear()


class TestGetMFAStatus:
    """Tests for get_mfa_status endpoint."""

    @pytest.mark.asyncio
    async def test_mfa_status_not_configured(self, mock_user: MagicMock) -> None:
        """Test MFA status when not configured."""
        result = await get_mfa_status(current_user=mock_user)
        
        assert result.is_enabled is False
        assert result.backup_codes_remaining == 0
        assert result.enabled_at is None

    @pytest.mark.asyncio
    async def test_mfa_status_configured_enabled(self, mock_user: MagicMock) -> None:
        """Test MFA status when configured and enabled."""
        config = MFAConfig(
            user_id=mock_user.id,
            secret="TESTSECRET",
            is_enabled=True,
            backup_codes=["code1", "code2", "code3"],
            enabled_at=datetime.now(timezone.utc),
        )
        save_mfa_config(config)
        
        result = await get_mfa_status(current_user=mock_user)
        
        assert result.is_enabled is True
        assert result.backup_codes_remaining == 3
        assert result.enabled_at is not None

    @pytest.mark.asyncio
    async def test_mfa_status_configured_not_enabled(self, mock_user: MagicMock) -> None:
        """Test MFA status when configured but not enabled."""
        config = MFAConfig(
            user_id=mock_user.id,
            secret="TESTSECRET",
            is_enabled=False,
            backup_codes=[],
        )
        save_mfa_config(config)
        
        result = await get_mfa_status(current_user=mock_user)
        
        assert result.is_enabled is False


class TestSetupMFA:
    """Tests for setup_mfa endpoint."""

    @pytest.mark.asyncio
    async def test_setup_mfa_success(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test successful MFA setup."""
        new_config = MFAConfig(
            user_id=mock_user.id,
            secret="NEWSECRET",
            is_enabled=False,
            backup_codes=["backup1", "backup2"],
        )
        mock_mfa_service.setup_mfa.return_value = (
            new_config,
            "data:image/png;base64,qrcode",
            "otpauth://totp/...",
        )
        
        result = await setup_mfa(current_user=mock_user, mfa_service=mock_mfa_service)
        
        assert result.secret == "NEWSECRET"
        assert result.qr_code is not None
        assert result.provisioning_uri is not None
        assert len(result.backup_codes) == 2

    @pytest.mark.asyncio
    async def test_setup_mfa_already_enabled(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test MFA setup when already enabled."""
        existing_config = MFAConfig(
            user_id=mock_user.id,
            secret="EXISTINGSECRET",
            is_enabled=True,
            backup_codes=[],
            enabled_at=datetime.now(timezone.utc),
        )
        save_mfa_config(existing_config)
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await setup_mfa(current_user=mock_user, mfa_service=mock_mfa_service)
        
        assert exc.value.status_code == 400
        assert "already enabled" in exc.value.detail.lower()


class TestVerifyMFASetup:
    """Tests for verify_mfa_setup endpoint."""

    @pytest.mark.asyncio
    async def test_verify_mfa_no_setup(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test verify MFA when setup not initiated."""
        request = MFAVerifyRequest(code="123456")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await verify_mfa_setup(
                request=request,
                current_user=mock_user,
                mfa_service=mock_mfa_service,
            )
        
        assert exc.value.status_code == 400
        assert "not initiated" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_mfa_already_enabled(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test verify MFA when already enabled."""
        existing_config = MFAConfig(
            user_id=mock_user.id,
            secret="SECRET",
            is_enabled=True,
            backup_codes=[],
            enabled_at=datetime.now(timezone.utc),
        )
        save_mfa_config(existing_config)
        
        request = MFAVerifyRequest(code="123456")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await verify_mfa_setup(
                request=request,
                current_user=mock_user,
                mfa_service=mock_mfa_service,
            )
        
        assert exc.value.status_code == 400
        assert "already enabled" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_mfa_invalid_code(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test verify MFA with invalid code."""
        pending_config = MFAConfig(
            user_id=mock_user.id,
            secret="SECRET",
            is_enabled=False,
            backup_codes=[],
        )
        save_mfa_config(pending_config)
        
        mock_mfa_service.verify_setup_code.return_value = False
        
        request = MFAVerifyRequest(code="000000")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await verify_mfa_setup(
                request=request,
                current_user=mock_user,
                mfa_service=mock_mfa_service,
            )
        
        assert exc.value.status_code == 400
        assert "invalid" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_mfa_success(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test successful MFA verification."""
        pending_config = MFAConfig(
            user_id=mock_user.id,
            secret="SECRET",
            is_enabled=False,
            backup_codes=["code1", "code2"],
        )
        save_mfa_config(pending_config)
        
        mock_mfa_service.verify_setup_code.return_value = True
        
        request = MFAVerifyRequest(code="123456")
        
        result = await verify_mfa_setup(
            request=request,
            current_user=mock_user,
            mfa_service=mock_mfa_service,
        )
        
        assert result.success is True
        assert "enabled" in result.message.lower()


class TestDisableMFA:
    """Tests for disable_mfa endpoint."""

    @pytest.mark.asyncio
    async def test_disable_mfa_not_enabled(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test disable MFA when not enabled."""
        request = MFADisableRequest(code="123456", password="password")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await disable_mfa(
                request=request,
                current_user=mock_user,
                mfa_service=mock_mfa_service,
            )
        
        assert exc.value.status_code == 400
        assert "not enabled" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_disable_mfa_invalid_code(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test disable MFA with invalid code."""
        config = MFAConfig(
            user_id=mock_user.id,
            secret="SECRET",
            is_enabled=True,
            backup_codes=[],
            enabled_at=datetime.now(timezone.utc),
        )
        save_mfa_config(config)
        
        mock_mfa_service.disable_mfa.return_value = False
        
        request = MFADisableRequest(code="000000", password="password")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await disable_mfa(
                request=request,
                current_user=mock_user,
                mfa_service=mock_mfa_service,
            )
        
        assert exc.value.status_code == 400
        assert "invalid" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_disable_mfa_success(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test successful MFA disable."""
        config = MFAConfig(
            user_id=mock_user.id,
            secret="SECRET",
            is_enabled=True,
            backup_codes=[],
            enabled_at=datetime.now(timezone.utc),
        )
        save_mfa_config(config)
        
        mock_mfa_service.disable_mfa.return_value = True
        
        request = MFADisableRequest(code="123456", password="password")
        
        result = await disable_mfa(
            request=request,
            current_user=mock_user,
            mfa_service=mock_mfa_service,
        )
        
        assert result.success is True
        assert "disabled" in result.message.lower()


class TestRegenerateBackupCodes:
    """Tests for regenerate_backup_codes endpoint."""

    @pytest.mark.asyncio
    async def test_regenerate_mfa_not_enabled(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test regenerate backup codes when MFA not enabled."""
        request = MFAVerifyRequest(code="123456")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await regenerate_backup_codes(
                request=request,
                current_user=mock_user,
                mfa_service=mock_mfa_service,
            )
        
        assert exc.value.status_code == 400
        assert "not enabled" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_regenerate_invalid_code(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test regenerate backup codes with invalid code."""
        config = MFAConfig(
            user_id=mock_user.id,
            secret="SECRET",
            is_enabled=True,
            backup_codes=["old1", "old2"],
            enabled_at=datetime.now(timezone.utc),
        )
        save_mfa_config(config)
        
        mock_mfa_service.verify_code.return_value = (False, False)
        
        request = MFAVerifyRequest(code="000000")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await regenerate_backup_codes(
                request=request,
                current_user=mock_user,
                mfa_service=mock_mfa_service,
            )
        
        assert exc.value.status_code == 400
        assert "invalid" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_regenerate_success(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test successful backup code regeneration."""
        config = MFAConfig(
            user_id=mock_user.id,
            secret="SECRET",
            is_enabled=True,
            backup_codes=["old1", "old2"],
            enabled_at=datetime.now(timezone.utc),
        )
        save_mfa_config(config)
        
        mock_mfa_service.verify_code.return_value = (True, False)
        mock_mfa_service.regenerate_backup_codes.return_value = ["new1", "new2", "new3"]
        
        request = MFAVerifyRequest(code="123456")
        
        result = await regenerate_backup_codes(
            request=request,
            current_user=mock_user,
            mfa_service=mock_mfa_service,
        )
        
        # Check response structure
        assert result is not None
        assert hasattr(result, 'backup_codes') or hasattr(result, 'message')


class TestValidateMFACode:
    """Tests for validate_mfa_code endpoint."""

    @pytest.mark.asyncio
    async def test_validate_mfa_not_enabled(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test validate code when MFA not enabled."""
        request = MFAVerifyRequest(code="123456")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await validate_mfa_code(
                request=request,
                current_user=mock_user,
                mfa_service=mock_mfa_service,
            )
        
        assert exc.value.status_code == 400
        assert "not enabled" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_invalid_code(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test validate with invalid code."""
        config = MFAConfig(
            user_id=mock_user.id,
            secret="SECRET",
            is_enabled=True,
            backup_codes=[],
            enabled_at=datetime.now(timezone.utc),
        )
        save_mfa_config(config)
        
        mock_mfa_service.verify_code.return_value = (False, False)
        
        request = MFAVerifyRequest(code="000000")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await validate_mfa_code(
                request=request,
                current_user=mock_user,
                mfa_service=mock_mfa_service,
            )
        
        assert exc.value.status_code == 400
        assert "invalid" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_success_totp(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test successful TOTP code validation."""
        config = MFAConfig(
            user_id=mock_user.id,
            secret="SECRET",
            is_enabled=True,
            backup_codes=["backup1"],
            enabled_at=datetime.now(timezone.utc),
        )
        save_mfa_config(config)
        
        mock_mfa_service.verify_code.return_value = (True, False)  # Not backup
        
        request = MFAVerifyRequest(code="123456")
        
        result = await validate_mfa_code(
            request=request,
            current_user=mock_user,
            mfa_service=mock_mfa_service,
        )
        
        assert result.success is True
        assert result.backup_codes_remaining is None

    @pytest.mark.asyncio
    async def test_validate_success_backup_code(
        self, mock_user: MagicMock, mock_mfa_service: MagicMock
    ) -> None:
        """Test successful backup code validation."""
        config = MFAConfig(
            user_id=mock_user.id,
            secret="SECRET",
            is_enabled=True,
            backup_codes=["ABC123", "DEF456"],
            enabled_at=datetime.now(timezone.utc),
        )
        save_mfa_config(config)
        
        mock_mfa_service.verify_code.return_value = (True, True)  # Was backup
        
        request = MFAVerifyRequest(code="ABC123")  # Use valid format
        
        result = await validate_mfa_code(
            request=request,
            current_user=mock_user,
            mfa_service=mock_mfa_service,
        )
        
        assert result.success is True


class TestMFAConfigHelpers:
    """Tests for MFA config helper functions."""

    def test_get_mfa_config_not_found(self) -> None:
        """Test get MFA config when not found."""
        result = get_mfa_config("nonexistent")
        assert result is None

    def test_save_and_get_mfa_config(self) -> None:
        """Test save and retrieve MFA config."""
        user_id = uuid4()
        config = MFAConfig(
            user_id=user_id,
            secret="SECRET",
            is_enabled=True,
            backup_codes=["code1"],
        )
        
        save_mfa_config(config)
        
        retrieved = get_mfa_config(str(user_id))
        assert retrieved is not None
        assert retrieved.secret == "SECRET"
