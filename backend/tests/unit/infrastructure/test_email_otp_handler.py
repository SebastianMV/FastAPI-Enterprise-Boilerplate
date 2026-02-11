# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Email OTP Handler.

Tests the email-based one-time password generation and verification
functionality used for 2FA without authenticator apps.
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.auth.email_otp_handler import (
    EmailOTPHandler,
    OTPData,
    get_email_otp_handler,
)


class TestOTPData:
    """Tests for OTPData namedtuple."""

    def test_otp_data_creation(self) -> None:
        """Test OTPData can be created with required fields."""
        expires = datetime.now(UTC) + timedelta(minutes=10)
        otp = OTPData(code="123456", expires_at=expires, attempts=0)

        assert otp.code == "123456"
        assert otp.expires_at == expires
        assert otp.attempts == 0

    def test_otp_data_immutable(self) -> None:
        """Test OTPData is immutable (namedtuple)."""
        otp = OTPData(code="123456", expires_at=datetime.now(UTC), attempts=0)

        with pytest.raises(AttributeError):
            otp.code = "654321"  # type: ignore


class TestEmailOTPHandler:
    """Tests for EmailOTPHandler class."""

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        """Create a mock Redis client."""
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_redis: MagicMock) -> EmailOTPHandler:
        """Create an EmailOTPHandler with mocked Redis."""
        return EmailOTPHandler(redis_client=mock_redis)

    # ===========================================
    # Configuration Tests
    # ===========================================

    def test_default_configuration(self, handler: EmailOTPHandler) -> None:
        """Test default configuration values."""
        assert handler.OTP_LENGTH == 6
        assert handler.OTP_EXPIRY_MINUTES == 10
        assert handler.MAX_ATTEMPTS == 3
        assert handler.COOLDOWN_SECONDS == 60

    def test_redis_client_injection(self, mock_redis: MagicMock) -> None:
        """Test Redis client can be injected."""
        handler = EmailOTPHandler(redis_client=mock_redis)
        assert handler._redis is mock_redis

    def test_get_redis_returns_injected_client(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test _get_redis returns injected client."""
        result = handler._get_redis()
        assert result is mock_redis

    @patch("app.infrastructure.auth.email_otp_handler.redis")
    @patch("app.infrastructure.auth.email_otp_handler.settings")
    def test_get_redis_creates_connection_when_no_client(
        self, mock_settings: MagicMock, mock_redis_module: MagicMock
    ) -> None:
        """Test _get_redis creates connection when no client injected."""
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_redis_module.from_url.return_value = MagicMock()

        handler = EmailOTPHandler()  # No redis_client
        result = handler._get_redis()

        mock_redis_module.from_url.assert_called_once_with(
            "redis://localhost:6379/0", decode_responses=True
        )

    # ===========================================
    # Code Generation Tests
    # ===========================================

    def test_generate_code_length(self, handler: EmailOTPHandler) -> None:
        """Test generated code has correct length."""
        code = handler._generate_code()
        assert len(code) == 6

    def test_generate_code_numeric(self, handler: EmailOTPHandler) -> None:
        """Test generated code is all numeric."""
        code = handler._generate_code()
        assert code.isdigit()

    def test_generate_code_randomness(self, handler: EmailOTPHandler) -> None:
        """Test generated codes are random (statistically)."""
        codes = {handler._generate_code() for _ in range(100)}
        # With 6 digits, we expect most codes to be unique
        assert len(codes) > 90

    # ===========================================
    # Key Generation Tests
    # ===========================================

    def test_get_key_default_purpose(self, handler: EmailOTPHandler) -> None:
        """Test key generation with default purpose."""
        key = handler._get_key("user-123")
        assert key == "email_otp:login:user-123"

    def test_get_key_custom_purpose(self, handler: EmailOTPHandler) -> None:
        """Test key generation with custom purpose."""
        key = handler._get_key("user-123", purpose="password_reset")
        assert key == "email_otp:password_reset:user-123"

    def test_get_cooldown_key(self, handler: EmailOTPHandler) -> None:
        """Test cooldown key generation."""
        key = handler._get_cooldown_key("user-123")
        assert key == "email_otp:cooldown:user-123"

    # ===========================================
    # Cooldown Tests
    # ===========================================

    def test_can_generate_otp_no_cooldown(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test can_generate_otp returns True when no cooldown."""
        mock_redis.ttl.return_value = 0

        can_generate, remaining = handler.can_generate_otp("user-123")

        assert can_generate is True
        assert remaining == 0

    def test_can_generate_otp_with_cooldown(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test can_generate_otp returns False during cooldown."""
        mock_redis.ttl.return_value = 30

        can_generate, remaining = handler.can_generate_otp("user-123")

        assert can_generate is False
        assert remaining == 30

    def test_can_generate_otp_expired_cooldown(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test can_generate_otp when cooldown key expired."""
        mock_redis.ttl.return_value = -2  # Key doesn't exist

        can_generate, remaining = handler.can_generate_otp("user-123")

        assert can_generate is True
        assert remaining == 0

    # ===========================================
    # OTP Generation Tests
    # ===========================================

    def test_generate_otp_success(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test successful OTP generation."""
        mock_redis.ttl.return_value = 0  # No cooldown

        code = handler.generate_otp("user-123")

        assert code is not None
        assert len(code) == 6
        assert code.isdigit()

        # Verify Redis calls
        assert mock_redis.setex.call_count == 2  # OTP + cooldown

    def test_generate_otp_during_cooldown(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test OTP generation blocked during cooldown."""
        mock_redis.ttl.return_value = 45  # 45 seconds remaining

        code = handler.generate_otp("user-123")

        assert code is None
        mock_redis.setex.assert_not_called()

    def test_generate_otp_custom_expiry(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test OTP generation with custom expiry."""
        mock_redis.ttl.return_value = 0

        code = handler.generate_otp("user-123", expiry_minutes=5)

        assert code is not None
        # Check the OTP storage call used correct expiry (5 * 60 = 300 seconds)
        otp_call = mock_redis.setex.call_args_list[0]
        assert otp_call[0][1] == 300  # 5 minutes in seconds

    def test_generate_otp_custom_purpose(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test OTP generation with custom purpose."""
        mock_redis.ttl.return_value = 0

        code = handler.generate_otp("user-123", purpose="password_reset")

        assert code is not None
        otp_call = mock_redis.setex.call_args_list[0]
        key = otp_call[0][0]
        assert "password_reset" in key

    def test_generate_otp_stores_correct_data(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test OTP generation stores correct data structure."""
        mock_redis.ttl.return_value = 0

        code = handler.generate_otp("user-123")

        otp_call = mock_redis.setex.call_args_list[0]
        stored_data = json.loads(otp_call[0][2])

        assert stored_data["code"] == code
        assert "expires_at" in stored_data
        assert stored_data["attempts"] == 0

    # ===========================================
    # OTP Verification Tests
    # ===========================================

    def test_verify_otp_success(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test successful OTP verification."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = handler.verify_otp("user-123", "123456")

        assert result is True
        mock_redis.delete.assert_called_once()

    def test_verify_otp_no_otp_found(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test verification fails when no OTP exists."""
        mock_redis.get.return_value = None

        result = handler.verify_otp("user-123", "123456")

        assert result is False

    def test_verify_otp_expired(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test verification fails for expired OTP."""
        expires_at = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = handler.verify_otp("user-123", "123456")

        assert result is False
        mock_redis.delete.assert_called_once()

    def test_verify_otp_wrong_code(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test verification fails for wrong code."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = handler.verify_otp("user-123", "654321")

        assert result is False
        # Should increment attempts
        mock_redis.setex.assert_called_once()

    def test_verify_otp_increments_attempts(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test verification increments attempts on failure."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": expires_at,
                "attempts": 1,
            }
        )
        mock_redis.get.return_value = otp_data

        result = handler.verify_otp("user-123", "000000")

        assert result is False

        # Check attempts were incremented
        setex_call = mock_redis.setex.call_args
        stored_data = json.loads(setex_call[0][2])
        assert stored_data["attempts"] == 2

    def test_verify_otp_max_attempts_exceeded(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test verification fails when max attempts exceeded."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": expires_at,
                "attempts": 3,  # Max is 3
            }
        )
        mock_redis.get.return_value = otp_data

        result = handler.verify_otp("user-123", "123456")

        assert result is False
        mock_redis.delete.assert_called_once()

    def test_verify_otp_without_consume(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test verification without consuming OTP."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = handler.verify_otp("user-123", "123456", consume=False)

        assert result is True
        mock_redis.delete.assert_not_called()

    def test_verify_otp_strips_whitespace(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test verification strips whitespace from code."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = handler.verify_otp("user-123", "  123456  ")

        assert result is True

    def test_verify_otp_custom_purpose(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test verification with custom purpose."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        handler.verify_otp("user-123", "123456", purpose="password_reset")

        mock_redis.get.assert_called_with("email_otp:password_reset:user-123")

    # ===========================================
    # OTP Invalidation Tests
    # ===========================================

    def test_invalidate_otp_success(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test successful OTP invalidation."""
        mock_redis.delete.return_value = 1

        result = handler.invalidate_otp("user-123")

        assert result is True
        mock_redis.delete.assert_called_with("email_otp:login:user-123")

    def test_invalidate_otp_none_exists(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test invalidation when no OTP exists."""
        mock_redis.delete.return_value = 0

        result = handler.invalidate_otp("user-123")

        assert result is False

    def test_invalidate_otp_custom_purpose(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test invalidation with custom purpose."""
        mock_redis.delete.return_value = 1

        handler.invalidate_otp("user-123", purpose="password_reset")

        mock_redis.delete.assert_called_with("email_otp:password_reset:user-123")

    # ===========================================
    # Remaining Attempts Tests
    # ===========================================

    def test_get_remaining_attempts_full(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test remaining attempts when no attempts made."""
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": datetime.now(UTC).isoformat(),
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = handler.get_remaining_attempts("user-123")

        assert result == 3

    def test_get_remaining_attempts_some_used(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test remaining attempts when some attempts used."""
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": datetime.now(UTC).isoformat(),
                "attempts": 2,
            }
        )
        mock_redis.get.return_value = otp_data

        result = handler.get_remaining_attempts("user-123")

        assert result == 1

    def test_get_remaining_attempts_none_left(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test remaining attempts when all used."""
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": datetime.now(UTC).isoformat(),
                "attempts": 3,
            }
        )
        mock_redis.get.return_value = otp_data

        result = handler.get_remaining_attempts("user-123")

        assert result == 0

    def test_get_remaining_attempts_no_otp(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test remaining attempts when no OTP exists."""
        mock_redis.get.return_value = None

        result = handler.get_remaining_attempts("user-123")

        assert result == 0

    def test_get_remaining_attempts_custom_purpose(
        self, handler: EmailOTPHandler, mock_redis: MagicMock
    ) -> None:
        """Test remaining attempts with custom purpose."""
        otp_data = json.dumps(
            {
                "code": "123456",
                "expires_at": datetime.now(UTC).isoformat(),
                "attempts": 1,
            }
        )
        mock_redis.get.return_value = otp_data

        handler.get_remaining_attempts("user-123", purpose="password_reset")

        mock_redis.get.assert_called_with("email_otp:password_reset:user-123")


class TestGetEmailOTPHandler:
    """Tests for the singleton getter function."""

    def test_get_email_otp_handler_returns_instance(self) -> None:
        """Test get_email_otp_handler returns an instance."""
        handler = get_email_otp_handler()
        assert isinstance(handler, EmailOTPHandler)

    def test_get_email_otp_handler_singleton(self) -> None:
        """Test get_email_otp_handler returns same instance."""
        handler1 = get_email_otp_handler()
        handler2 = get_email_otp_handler()
        assert handler1 is handler2
