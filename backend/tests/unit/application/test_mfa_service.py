# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for MFA (Multi-Factor Authentication) service.

Tests for MFAService and TOTP handler functionality.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.application.services.mfa_service import MFAService, get_mfa_service
from app.domain.entities.mfa import MFAConfig
from app.infrastructure.auth.totp_handler import TOTPHandler, get_totp_handler


class TestMFAConfig:
    """Tests for MFAConfig entity."""

    def test_create_mfa_config(self) -> None:
        """Test creating MFA config."""
        user_id = uuid4()
        config = MFAConfig(
            user_id=user_id,
            secret="JBSWY3DPEHPK3PXP",
            is_enabled=False,
        )

        assert config.user_id == user_id
        assert config.secret == "JBSWY3DPEHPK3PXP"
        assert config.is_enabled is False
        assert config.backup_codes == []

    def test_generate_backup_codes(self) -> None:
        """Test backup code generation."""
        codes = MFAConfig.generate_backup_codes(count=10)

        assert len(codes) == 10
        # All codes should be unique
        assert len(set(codes)) == 10
        # Codes should be 8 hex characters
        for code in codes:
            assert len(code) == 8
            assert code.isalnum()

    def test_use_backup_code_valid(self) -> None:
        """Test using a valid backup code."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="SECRET",
            backup_codes=["ABCD1234", "EFGH5678"],
        )

        result = config.use_backup_code("ABCD1234")

        assert result is True
        assert "ABCD1234" not in config.backup_codes
        assert "EFGH5678" in config.backup_codes

    def test_use_backup_code_invalid(self) -> None:
        """Test using an invalid backup code."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="SECRET",
            backup_codes=["ABCD1234"],
        )

        result = config.use_backup_code("WRONG123")

        assert result is False
        assert "ABCD1234" in config.backup_codes

    def test_enable_mfa(self) -> None:
        """Test enabling MFA."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="SECRET",
            is_enabled=False,
        )

        config.enable()

        assert config.is_enabled is True
        assert config.enabled_at is not None

    def test_disable_mfa(self) -> None:
        """Test disabling MFA."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="SECRET",
            is_enabled=True,
        )

        config.disable()

        assert config.is_enabled is False


class TestMFAService:
    """Tests for MFAService."""

    @pytest.fixture
    def mock_totp_handler(self) -> MagicMock:
        """Create mock TOTP handler."""
        handler = MagicMock(spec=TOTPHandler)
        handler.generate_secret.return_value = "TESTSECRET123456"
        handler.verify.return_value = True
        handler.generate_setup_data.return_value = (
            "TESTSECRET123456",
            "otpauth://totp/App:test@example.com?secret=TESTSECRET123456",
            "data:image/png;base64,qrcode...",
        )
        return handler

    @pytest.fixture
    def mfa_service(self, mock_totp_handler: MagicMock) -> MFAService:
        """Create MFA service with mock handler."""
        return MFAService(totp_handler=mock_totp_handler)

    def test_setup_mfa_returns_config(self, mfa_service: MFAService) -> None:
        """Test that MFA setup returns config with QR code."""
        user_id = uuid4()
        email = "test@example.com"

        config, qr_code, uri = mfa_service.setup_mfa(user_id, email)

        assert isinstance(config, MFAConfig)
        assert config.user_id == user_id
        assert config.secret == "TESTSECRET123456"
        assert config.is_enabled is False
        assert len(config.backup_codes) == 10
        assert qr_code == "data:image/png;base64,qrcode..."
        assert "otpauth://" in uri

    def test_verify_code_valid_totp(
        self, mfa_service: MFAService, mock_totp_handler: MagicMock
    ) -> None:
        """Test verifying a valid TOTP code."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=True,
        )
        mock_totp_handler.verify.return_value = True

        is_valid, was_backup = mfa_service.verify_code(config, "123456")

        assert is_valid is True
        assert was_backup is False
        mock_totp_handler.verify.assert_called_once_with("TESTSECRET", "123456")

    def test_verify_code_invalid_totp(
        self, mfa_service: MFAService, mock_totp_handler: MagicMock
    ) -> None:
        """Test verifying an invalid TOTP code."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=True,
        )
        mock_totp_handler.verify.return_value = False

        is_valid, was_backup = mfa_service.verify_code(config, "000000")

        assert is_valid is False
        assert was_backup is False

    def test_verify_code_with_backup_code(
        self, mfa_service: MFAService, mock_totp_handler: MagicMock
    ) -> None:
        """Test verifying with a backup code."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=True,
            backup_codes=["ABCD1234"],
        )
        mock_totp_handler.verify.return_value = False

        is_valid, was_backup = mfa_service.verify_code(config, "ABCD1234")

        assert is_valid is True
        assert was_backup is True
        assert "ABCD1234" not in config.backup_codes

    def test_verify_code_fails_when_disabled(self, mfa_service: MFAService) -> None:
        """Test that verification fails when MFA is disabled."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=False,
        )

        is_valid, was_backup = mfa_service.verify_code(config, "123456")

        assert is_valid is False
        assert was_backup is False

    def test_verify_setup_code_enables_mfa(
        self, mfa_service: MFAService, mock_totp_handler: MagicMock
    ) -> None:
        """Test that verifying setup code enables MFA."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=False,
        )
        mock_totp_handler.verify.return_value = True

        result = mfa_service.verify_setup_code(config, "123456")

        assert result is True
        assert config.is_enabled is True

    def test_verify_setup_code_fails_with_wrong_code(
        self, mfa_service: MFAService, mock_totp_handler: MagicMock
    ) -> None:
        """Test that wrong setup code does not enable MFA."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=False,
        )
        mock_totp_handler.verify.return_value = False

        result = mfa_service.verify_setup_code(config, "000000")

        assert result is False
        assert config.is_enabled is False

    def test_disable_mfa_with_valid_code(
        self, mfa_service: MFAService, mock_totp_handler: MagicMock
    ) -> None:
        """Test disabling MFA with valid TOTP code."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=True,
        )
        mock_totp_handler.verify.return_value = True

        result = mfa_service.disable_mfa(config, "123456")

        assert result is True
        assert config.is_enabled is False

    def test_disable_mfa_fails_with_invalid_code(
        self, mfa_service: MFAService, mock_totp_handler: MagicMock
    ) -> None:
        """Test that MFA cannot be disabled with invalid code."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=True,
        )
        mock_totp_handler.verify.return_value = False

        result = mfa_service.disable_mfa(config, "000000")

        assert result is False
        assert config.is_enabled is True

    def test_get_remaining_backup_codes(self, mfa_service: MFAService) -> None:
        """Test getting remaining backup code count."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            backup_codes=["CODE1", "CODE2", "CODE3"],
        )

        count = mfa_service.get_remaining_backup_codes(config)

        assert count == 3


class TestTOTPHandler:
    """Tests for TOTP handler."""

    @pytest.fixture
    def totp_handler(self) -> TOTPHandler:
        """Create TOTP handler instance."""
        return TOTPHandler(issuer="TestApp")

    def test_generate_secret_format(self, totp_handler: TOTPHandler) -> None:
        """Test that generated secret is valid base32."""
        secret = totp_handler.generate_secret()

        # Should be base32 encoded (only A-Z and 2-7)
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)
        assert len(secret) == 32

    def test_generate_secret_unique(self, totp_handler: TOTPHandler) -> None:
        """Test that generated secrets are unique."""
        secrets = {totp_handler.generate_secret() for _ in range(10)}

        assert len(secrets) == 10

    def test_verify_valid_code(self, totp_handler: TOTPHandler) -> None:
        """Test verifying a valid TOTP code."""
        secret = totp_handler.generate_secret()
        current_code = totp_handler.get_current_code(secret)

        result = totp_handler.verify(secret, current_code)

        assert result is True

    def test_verify_invalid_code(self, totp_handler: TOTPHandler) -> None:
        """Test verifying an invalid TOTP code."""
        secret = totp_handler.generate_secret()

        result = totp_handler.verify(secret, "000000")

        assert result is False

    def test_verify_empty_code(self, totp_handler: TOTPHandler) -> None:
        """Test verifying empty code."""
        result = totp_handler.verify("SECRET", "")

        assert result is False

    def test_verify_code_wrong_length(self, totp_handler: TOTPHandler) -> None:
        """Test verifying code with wrong length."""
        result = totp_handler.verify("SECRET", "12345")  # 5 digits

        assert result is False

    def test_get_provisioning_uri(self, totp_handler: TOTPHandler) -> None:
        """Test provisioning URI generation."""
        secret = "JBSWY3DPEHPK3PXP"

        uri = totp_handler.get_provisioning_uri(secret, "user@example.com")

        assert uri.startswith("otpauth://totp/")
        assert "secret=JBSWY3DPEHPK3PXP" in uri
        assert "issuer=TestApp" in uri

    def test_generate_qr_code_base64(self, totp_handler: TOTPHandler) -> None:
        """Test QR code generation as base64."""
        qr_code = totp_handler.generate_qr_code(
            "JBSWY3DPEHPK3PXP",
            "user@example.com",
            as_base64=True,
        )

        assert isinstance(qr_code, str)
        assert qr_code.startswith("data:image/png;base64,")

    def test_generate_qr_code_bytes(self, totp_handler: TOTPHandler) -> None:
        """Test QR code generation as bytes."""
        qr_code = totp_handler.generate_qr_code(
            "JBSWY3DPEHPK3PXP",
            "user@example.com",
            as_base64=False,
        )

        assert isinstance(qr_code, bytes)
        # PNG magic bytes
        assert qr_code[:8] == b"\x89PNG\r\n\x1a\n"

    def test_generate_setup_data(self, totp_handler: TOTPHandler) -> None:
        """Test complete setup data generation."""
        secret, uri, qr_code = totp_handler.generate_setup_data("user@example.com")

        assert len(secret) == 32
        assert uri.startswith("otpauth://totp/")
        assert isinstance(qr_code, str)
        assert "base64" in qr_code


class TestSingletons:
    """Tests for singleton instances."""

    def test_get_totp_handler_singleton(self) -> None:
        """Test that get_totp_handler returns same instance."""
        handler1 = get_totp_handler()
        handler2 = get_totp_handler()

        assert handler1 is handler2

    def test_get_mfa_service_singleton(self) -> None:
        """Test that get_mfa_service returns same instance."""
        service1 = get_mfa_service()
        service2 = get_mfa_service()

        assert service1 is service2


class TestMFAServiceMissingCoverage:
    """Tests for MFAService methods with missing coverage."""

    @pytest.fixture
    def mock_totp_handler(self) -> MagicMock:
        """Create mock TOTP handler."""
        handler = MagicMock(spec=TOTPHandler)
        handler.generate_secret.return_value = "TESTSECRET123456"
        handler.verify.return_value = True
        return handler

    @pytest.fixture
    def mfa_service(self, mock_totp_handler: MagicMock) -> MFAService:
        """Create MFA service with mock handler."""
        return MFAService(totp_handler=mock_totp_handler)

    def test_verify_setup_code_returns_false_when_already_enabled(
        self, mfa_service: MFAService, mock_totp_handler: MagicMock
    ) -> None:
        """Test that verify_setup_code returns False when MFA is already enabled."""
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=True,  # Already enabled
        )

        result = mfa_service.verify_setup_code(config, "123456")

        assert result is False
        # Verify method wasn't even called since is_enabled check fails first
        mock_totp_handler.verify.assert_not_called()

    def test_regenerate_backup_codes_returns_new_codes(
        self, mfa_service: MFAService
    ) -> None:
        """Test that regenerate_backup_codes returns new backup codes."""
        old_codes = ["OLD12345", "OLD67890"]
        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET",
            is_enabled=True,
            backup_codes=old_codes.copy(),
        )

        new_codes = mfa_service.regenerate_backup_codes(config)

        assert len(new_codes) == 10
        # New codes should be different from old ones
        for old_code in old_codes:
            assert old_code not in new_codes
        # Config should have the new codes
        assert config.backup_codes == new_codes
