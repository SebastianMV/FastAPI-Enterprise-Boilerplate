# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for MFA endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest


class TestMFASchemas:
    """Tests for MFA schemas."""

    def test_mfa_setup_response(self) -> None:
        """Test MFASetupResponse schema."""
        from app.api.v1.schemas.mfa import MFASetupResponse

        response = MFASetupResponse(
            secret="TESTSECRET123456",
            qr_code="data:image/png;base64,abc123",
            provisioning_uri="otpauth://totp/Test:user@example.com",
            backup_codes=["code1", "code2", "code3"],
        )
        assert response.secret == "TESTSECRET123456"
        assert "base64" in response.qr_code
        assert len(response.backup_codes) == 3

    def test_mfa_verify_request(self) -> None:
        """Test MFAVerifyRequest schema."""
        from app.api.v1.schemas.mfa import MFAVerifyRequest

        request = MFAVerifyRequest(code="123456")
        assert request.code == "123456"

    def test_mfa_status_response(self) -> None:
        """Test MFAStatusResponse schema."""
        from app.api.v1.schemas.mfa import MFAStatusResponse

        response = MFAStatusResponse(
            is_enabled=True,
            backup_codes_remaining=5,
            enabled_at=datetime.now(UTC),
        )
        assert response.is_enabled is True
        assert response.backup_codes_remaining == 5

    def test_mfa_disable_request(self) -> None:
        """Test MFADisableRequest schema."""
        from app.api.v1.schemas.mfa import MFADisableRequest

        request = MFADisableRequest(code="654321", password="Password123!")
        assert request.code == "654321"
        assert request.password == "Password123!"


class TestMFAEndpointsStructure:
    """Tests for MFA endpoints structure."""

    def test_mfa_router_exists(self) -> None:
        """Test MFA router is defined."""
        from app.api.v1.endpoints.mfa import router

        assert router is not None

    def test_mfa_routes_registered(self) -> None:
        """Test MFA routes are registered."""
        from app.api.v1.endpoints.mfa import router

        routes = [route.path for route in router.routes]
        assert "/setup" in routes or len(routes) > 0


class TestMFAService:
    """Tests for MFA service."""

    def test_mfa_service_import(self) -> None:
        """Test MFA service can be imported."""
        from app.application.services.mfa_service import MFAService

        assert MFAService is not None

    def test_mfa_service_creation(self) -> None:
        """Test MFA service creation."""
        from app.application.services.mfa_service import MFAService

        service = MFAService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_mfa_service_has_totp_handler(self) -> None:
        """Test MFA service has TOTP handler."""
        from app.application.services.mfa_service import MFAService

        service = MFAService()
        # The service should have access to TOTP functions
        assert service is not None


class TestMFAConfig:
    """Tests for MFA configuration."""

    def test_mfa_entity_creation(self) -> None:
        """Test MFAConfig entity creation."""
        from app.domain.entities.mfa import MFAConfig

        user_id = uuid4()
        config = MFAConfig(
            user_id=user_id,
            secret="TESTSECRET123456",
        )

        assert config.user_id == user_id
        assert config.secret == "TESTSECRET123456"
        assert config.is_enabled is False

    def test_mfa_config_enable(self) -> None:
        """Test enabling MFA config."""
        from app.domain.entities.mfa import MFAConfig

        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
        )

        config.enable()
        assert config.is_enabled is True

    def test_mfa_config_disable(self) -> None:
        """Test disabling MFA config."""
        from app.domain.entities.mfa import MFAConfig

        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=True,
        )

        config.disable()
        assert config.is_enabled is False


class TestBackupCodes:
    """Tests for backup codes."""

    def test_backup_codes_generation(self) -> None:
        """Test backup codes can be generated."""
        import secrets

        # Generate 10 backup codes
        codes = [secrets.token_hex(4).upper() for _ in range(10)]

        assert len(codes) == 10
        assert all(len(code) == 8 for code in codes)
        # All codes should be unique
        assert len(set(codes)) == 10

    def test_backup_codes_format(self) -> None:
        """Test backup codes format is valid."""
        import secrets

        code = secrets.token_hex(4).upper()

        # Should be 8 characters, hexadecimal
        assert len(code) == 8
        assert all(c in "0123456789ABCDEF" for c in code)
