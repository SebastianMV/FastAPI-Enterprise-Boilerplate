# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for MFA endpoints to improve coverage.
Target: app/api/v1/endpoints/mfa.py from 43% to 85%+
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.domain.entities.mfa import MFAConfig
from app.domain.entities.user import User
from app.domain.value_objects.email import Email


@pytest.fixture
def mock_user():
    """Mock user entity."""
    return User(
        id=uuid4(),
        tenant_id=uuid4(),
        email=Email("user@example.com"),
        password_hash="hashed",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def mock_mfa_config(mock_user):
    """Mock MFA config entity."""
    return MFAConfig(
        user_id=mock_user.id,
        secret="JBSWY3DPEHPK3PXP",
        is_enabled=False,
        backup_codes=["123456", "789012", "345678"],
    )


@pytest.fixture
def mock_enabled_mfa_config(mock_user):
    """Mock enabled MFA config."""
    config = MFAConfig(
        user_id=mock_user.id,
        secret="JBSWY3DPEHPK3PXP",
        is_enabled=True,
        backup_codes=["123456", "789012"],
    )
    config.enabled_at = datetime.now(UTC)
    return config


class TestGetMFAStatus:
    """Tests for get_mfa_status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_no_config(self, mock_user):
        """Test getting MFA status when MFA not set up."""
        from app.api.v1.endpoints.mfa import get_mfa_status

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = None

            result = await get_mfa_status(current_user=mock_user)

            assert result.is_enabled is False
            assert result.backup_codes_remaining == 0

    @pytest.mark.asyncio
    async def test_get_status_disabled(self, mock_user, mock_mfa_config):
        """Test getting MFA status when setup but not enabled."""
        from app.api.v1.endpoints.mfa import get_mfa_status

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = mock_mfa_config

            result = await get_mfa_status(current_user=mock_user)

            assert result.is_enabled is False

    @pytest.mark.asyncio
    async def test_get_status_enabled(self, mock_user, mock_enabled_mfa_config):
        """Test getting MFA status when enabled."""
        from app.api.v1.endpoints.mfa import get_mfa_status

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = mock_enabled_mfa_config

            result = await get_mfa_status(current_user=mock_user)

            assert result.is_enabled is True
            assert result.backup_codes_remaining == 2


class TestSetupMFA:
    """Tests for setup_mfa endpoint."""

    @pytest.mark.asyncio
    async def test_setup_mfa_success(self, mock_user, mock_mfa_config):
        """Test successful MFA setup."""
        from app.api.v1.endpoints.mfa import setup_mfa

        mock_service = MagicMock()
        mock_service.setup_mfa.return_value = (
            mock_mfa_config,
            "data:image/png;base64,iVBORw0KG...",
            "otpauth://totp/App:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=App",
        )

        with (
            patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config,
            patch("app.api.v1.endpoints.mfa.save_mfa_config") as mock_save,
        ):
            mock_get_config.return_value = None

            result = await setup_mfa(current_user=mock_user, mfa_service=mock_service)

            assert result.secret == mock_mfa_config.secret
            assert len(result.backup_codes) == 3
            assert mock_save.called

    @pytest.mark.asyncio
    async def test_setup_mfa_already_enabled(self, mock_user, mock_enabled_mfa_config):
        """Test setup when MFA already enabled."""
        from app.api.v1.endpoints.mfa import setup_mfa

        mock_service = MagicMock()

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = mock_enabled_mfa_config

            with pytest.raises(HTTPException) as exc:
                await setup_mfa(current_user=mock_user, mfa_service=mock_service)

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "already enabled" in str(exc.value.detail)


class TestVerifyMFASetup:
    """Tests for verify_mfa_setup endpoint."""

    @pytest.mark.asyncio
    async def test_verify_setup_success(self, mock_user, mock_mfa_config):
        """Test successful MFA verification."""
        from app.api.v1.endpoints.mfa import verify_mfa_setup
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        mock_service.verify_setup_code.return_value = True

        request = MFAVerifyRequest(code="123456")

        with (
            patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config,
            patch("app.api.v1.endpoints.mfa.save_mfa_config") as mock_save,
        ):
            mock_get_config.return_value = mock_mfa_config

            result = await verify_mfa_setup(
                request=request, current_user=mock_user, mfa_service=mock_service
            )

            assert result.success is True
            assert mock_save.called

    @pytest.mark.asyncio
    async def test_verify_setup_no_config(self, mock_user):
        """Test verification when setup not initiated."""
        from app.api.v1.endpoints.mfa import verify_mfa_setup
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        request = MFAVerifyRequest(code="123456")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = None

            with pytest.raises(HTTPException) as exc:
                await verify_mfa_setup(
                    request=request, current_user=mock_user, mfa_service=mock_service
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "not initiated" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_verify_setup_already_enabled(
        self, mock_user, mock_enabled_mfa_config
    ):
        """Test verification when already enabled."""
        from app.api.v1.endpoints.mfa import verify_mfa_setup
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        request = MFAVerifyRequest(code="123456")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = mock_enabled_mfa_config

            with pytest.raises(HTTPException) as exc:
                await verify_mfa_setup(
                    request=request, current_user=mock_user, mfa_service=mock_service
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_verify_setup_invalid_code(self, mock_user, mock_mfa_config):
        """Test verification with invalid code."""
        from app.api.v1.endpoints.mfa import verify_mfa_setup
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        mock_service.verify_setup_code.return_value = False

        request = MFAVerifyRequest(code="000000")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = mock_mfa_config

            with pytest.raises(HTTPException) as exc:
                await verify_mfa_setup(
                    request=request, current_user=mock_user, mfa_service=mock_service
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid verification code" in str(exc.value.detail)


class TestDisableMFA:
    """Tests for disable_mfa endpoint."""

    @pytest.mark.asyncio
    async def test_disable_mfa_success(self, mock_user, mock_enabled_mfa_config):
        """Test successful MFA disable."""
        from app.api.v1.endpoints.mfa import disable_mfa
        from app.api.v1.schemas.mfa import MFADisableRequest

        mock_service = MagicMock()
        mock_service.disable_mfa.return_value = True

        request = MFADisableRequest(password="password", code="123456")

        with (
            patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config,
            patch("app.api.v1.endpoints.mfa.save_mfa_config") as mock_save,
            patch("app.api.v1.endpoints.mfa.verify_password", return_value=True),
        ):
            mock_get_config.return_value = mock_enabled_mfa_config

            result = await disable_mfa(
                request=request, current_user=mock_user, mfa_service=mock_service
            )

            assert result.success is True
            assert mock_save.called

    @pytest.mark.asyncio
    async def test_disable_mfa_invalid_password(
        self, mock_user, mock_enabled_mfa_config
    ):
        """Test disable fails with invalid password."""
        from app.api.v1.endpoints.mfa import disable_mfa
        from app.api.v1.schemas.mfa import MFADisableRequest

        mock_service = MagicMock()
        request = MFADisableRequest(password="wrong_password", code="123456")

        with (
            patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config,
            patch("app.api.v1.endpoints.mfa.verify_password", return_value=False),
        ):
            mock_get_config.return_value = mock_enabled_mfa_config

            with pytest.raises(HTTPException) as exc:
                await disable_mfa(
                    request=request, current_user=mock_user, mfa_service=mock_service
                )

            assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid password" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_disable_mfa_not_enabled(self, mock_user):
        """Test disabling when MFA not enabled."""
        from app.api.v1.endpoints.mfa import disable_mfa
        from app.api.v1.schemas.mfa import MFADisableRequest

        mock_service = MagicMock()
        request = MFADisableRequest(password="password", code="123456")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = None

            with pytest.raises(HTTPException) as exc:
                await disable_mfa(
                    request=request, current_user=mock_user, mfa_service=mock_service
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_disable_mfa_invalid_code(self, mock_user, mock_enabled_mfa_config):
        """Test disabling with invalid code."""
        from app.api.v1.endpoints.mfa import disable_mfa
        from app.api.v1.schemas.mfa import MFADisableRequest

        mock_service = MagicMock()
        mock_service.disable_mfa.return_value = False

        request = MFADisableRequest(password="password", code="000000")

        with (
            patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config,
            patch("app.api.v1.endpoints.mfa.verify_password", return_value=True),
        ):
            mock_get_config.return_value = mock_enabled_mfa_config

            with pytest.raises(HTTPException) as exc:
                await disable_mfa(
                    request=request, current_user=mock_user, mfa_service=mock_service
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid verification code" in str(exc.value.detail)


class TestRegenerateBackupCodes:
    """Tests for regenerate_backup_codes endpoint."""

    @pytest.mark.asyncio
    async def test_regenerate_codes_success(self, mock_user, mock_enabled_mfa_config):
        """Test successful backup code regeneration."""
        from app.api.v1.endpoints.mfa import regenerate_backup_codes
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        mock_service.verify_code.return_value = (True, False)
        mock_service.regenerate_backup_codes.return_value = [
            "111111",
            "222222",
            "333333",
        ]

        request = MFAVerifyRequest(code="123456")

        with (
            patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config,
            patch("app.api.v1.endpoints.mfa.save_mfa_config") as mock_save,
        ):
            mock_get_config.return_value = mock_enabled_mfa_config

            result = await regenerate_backup_codes(
                request=request, current_user=mock_user, mfa_service=mock_service
            )

            assert len(result.backup_codes) == 3
            assert mock_save.called

    @pytest.mark.asyncio
    async def test_regenerate_codes_not_enabled(self, mock_user):
        """Test regeneration when MFA not enabled."""
        from app.api.v1.endpoints.mfa import regenerate_backup_codes
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        request = MFAVerifyRequest(code="123456")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = None

            with pytest.raises(HTTPException) as exc:
                await regenerate_backup_codes(
                    request=request, current_user=mock_user, mfa_service=mock_service
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_regenerate_codes_invalid_code(
        self, mock_user, mock_enabled_mfa_config
    ):
        """Test regeneration with invalid code."""
        from app.api.v1.endpoints.mfa import regenerate_backup_codes
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        mock_service.verify_code.return_value = (False, False)

        request = MFAVerifyRequest(code="000000")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = mock_enabled_mfa_config

            with pytest.raises(HTTPException) as exc:
                await regenerate_backup_codes(
                    request=request, current_user=mock_user, mfa_service=mock_service
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


class TestValidateMFACode:
    """Tests for validate_mfa_code endpoint."""

    @pytest.mark.asyncio
    async def test_validate_code_success(self, mock_user, mock_enabled_mfa_config):
        """Test successful code validation."""
        from app.api.v1.endpoints.mfa import validate_mfa_code
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        mock_service.verify_code.return_value = (True, False)

        request = MFAVerifyRequest(code="123456")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = mock_enabled_mfa_config

            result = await validate_mfa_code(
                request=request, current_user=mock_user, mfa_service=mock_service
            )

            assert result.success is True

    @pytest.mark.asyncio
    async def test_validate_code_backup_used(self, mock_user, mock_enabled_mfa_config):
        """Test validation using backup code."""
        from app.api.v1.endpoints.mfa import validate_mfa_code
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        mock_service.verify_code.return_value = (True, True)

        request = MFAVerifyRequest(code="123456")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = mock_enabled_mfa_config

            result = await validate_mfa_code(
                request=request, current_user=mock_user, mfa_service=mock_service
            )

            assert result.success is True

    @pytest.mark.asyncio
    async def test_validate_code_not_enabled(self, mock_user):
        """Test validation when MFA not enabled."""
        from app.api.v1.endpoints.mfa import validate_mfa_code
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        request = MFAVerifyRequest(code="123456")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = None

            with pytest.raises(HTTPException) as exc:
                await validate_mfa_code(
                    request=request, current_user=mock_user, mfa_service=mock_service
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_validate_code_invalid(self, mock_user, mock_enabled_mfa_config):
        """Test validation with invalid code."""
        from app.api.v1.endpoints.mfa import validate_mfa_code
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        mock_service = MagicMock()
        mock_service.verify_code.return_value = (False, False)

        request = MFAVerifyRequest(code="000000")

        with patch("app.api.v1.endpoints.mfa.get_mfa_config") as mock_get_config:
            mock_get_config.return_value = mock_enabled_mfa_config

            with pytest.raises(HTTPException) as exc:
                await validate_mfa_code(
                    request=request, current_user=mock_user, mfa_service=mock_service
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
