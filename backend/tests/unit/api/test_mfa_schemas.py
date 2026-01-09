# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for MFA endpoint schemas."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.api.v1.schemas.mfa import (
    MFASetupRequest,
    MFAVerifyRequest,
    MFADisableRequest,
    MFALoginRequest,
    MFASetupResponse,
    MFAStatusResponse,
    MFAVerifyResponse,
    MFAEnableResponse,
    MFADisableResponse,
    MFABackupCodesResponse,
    MFARequiredResponse,
)


class TestMFARequestSchemas:
    """Tests for MFA request schemas."""

    def test_mfa_setup_request(self):
        """Test MFA setup request (empty body)."""
        request = MFASetupRequest()
        assert request is not None

    def test_mfa_verify_request_valid_totp(self):
        """Test valid TOTP code verification."""
        request = MFAVerifyRequest(code="123456")
        assert request.code == "123456"

    def test_mfa_verify_request_valid_backup(self):
        """Test valid backup code verification."""
        request = MFAVerifyRequest(code="AB12CD34")
        assert request.code == "AB12CD34"

    def test_mfa_verify_request_with_spaces(self):
        """Test code with spaces."""
        request = MFAVerifyRequest(code="123 456")
        assert request.code == "123 456"

    def test_mfa_verify_request_too_short(self):
        """Test code too short."""
        with pytest.raises(ValidationError):
            MFAVerifyRequest(code="12345")

    def test_mfa_verify_request_too_long(self):
        """Test code too long."""
        with pytest.raises(ValidationError):
            MFAVerifyRequest(code="123456789")

    def test_mfa_verify_request_invalid_chars(self):
        """Test code with invalid characters."""
        with pytest.raises(ValidationError):
            MFAVerifyRequest(code="!@#$%^")

    def test_mfa_disable_request_valid(self):
        """Test valid disable request."""
        request = MFADisableRequest(code="123456", password="mypassword")
        assert request.code == "123456"
        assert request.password == "mypassword"

    def test_mfa_disable_request_invalid_code_format(self):
        """Test disable with non-digit code."""
        with pytest.raises(ValidationError):
            MFADisableRequest(code="ABCDEF", password="pass")

    def test_mfa_disable_request_missing_password(self):
        """Test disable without password."""
        with pytest.raises(ValidationError):
            MFADisableRequest(code="123456")  # type: ignore[call-arg]

    def test_mfa_login_request_valid(self):
        """Test valid MFA login request."""
        request = MFALoginRequest(mfa_token="token123", code="123456")
        assert request.mfa_token == "token123"
        assert request.code == "123456"

    def test_mfa_login_request_missing_token(self):
        """Test login request without token."""
        with pytest.raises(ValidationError):
            MFALoginRequest(code="123456")  # type: ignore[call-arg]


class TestMFAResponseSchemas:
    """Tests for MFA response schemas."""

    def test_mfa_setup_response(self):
        """Test MFA setup response."""
        response = MFASetupResponse(
            secret="JBSWY3DPEHPK3PXP",
            qr_code="data:image/png;base64,iVBORw0...",
            provisioning_uri="otpauth://totp/App:user@example.com?secret=JBSWY3DPEHPK3PXP",
            backup_codes=["CODE1", "CODE2", "CODE3", "CODE4"]
        )
        assert response.secret == "JBSWY3DPEHPK3PXP"
        assert len(response.backup_codes) == 4

    def test_mfa_status_response_enabled(self):
        """Test MFA status when enabled."""
        now = datetime.now(timezone.utc)
        response = MFAStatusResponse(
            is_enabled=True,
            enabled_at=now,
            backup_codes_remaining=8,
            last_used_at=now
        )
        assert response.is_enabled is True
        assert response.backup_codes_remaining == 8

    def test_mfa_status_response_disabled(self):
        """Test MFA status when disabled."""
        response = MFAStatusResponse(
            is_enabled=False,
            backup_codes_remaining=0,
            enabled_at=None,
            last_used_at=None
        )
        assert response.is_enabled is False
        assert response.enabled_at is None

    def test_mfa_verify_response_success(self):
        """Test successful verification response."""
        response = MFAVerifyResponse(
            success=True,
            message="MFA verification successful",
            backup_codes_remaining=7
        )
        assert response.success is True
        assert response.backup_codes_remaining == 7

    def test_mfa_verify_response_defaults(self):
        """Test verify response with defaults."""
        response = MFAVerifyResponse(backup_codes_remaining=None)
        assert response.success is True
        assert response.message == "MFA verification successful"
        assert response.backup_codes_remaining is None

    def test_mfa_enable_response(self):
        """Test enable response."""
        now = datetime.now(timezone.utc)
        response = MFAEnableResponse(
            success=True,
            message="MFA has been enabled",
            enabled_at=now,
            backup_codes_remaining=10
        )
        assert response.success is True
        assert response.backup_codes_remaining == 10

    def test_mfa_disable_response(self):
        """Test disable response."""
        response = MFADisableResponse(
            success=True,
            message="MFA has been disabled"
        )
        assert response.success is True

    def test_mfa_disable_response_defaults(self):
        """Test disable response with defaults."""
        response = MFADisableResponse()
        assert response.success is True
        assert response.message == "MFA has been disabled"

    def test_mfa_backup_codes_response(self):
        """Test backup codes response."""
        codes = ["CODE1", "CODE2", "CODE3", "CODE4", "CODE5"]
        response = MFABackupCodesResponse(backup_codes=codes)
        assert len(response.backup_codes) == 5
        assert response.message == "New backup codes generated. Previous codes are now invalid."

    def test_mfa_required_response(self):
        """Test MFA required response."""
        response = MFARequiredResponse(
            mfa_required=True,
            mfa_token="temp_token_abc123"
        )
        assert response.mfa_required is True
        assert response.mfa_token == "temp_token_abc123"
        assert "MFA verification required" in response.message

    def test_mfa_required_response_defaults(self):
        """Test MFA required defaults."""
        response = MFARequiredResponse(mfa_token="token")
        assert response.mfa_required is True
