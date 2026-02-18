# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Email OTP Handler.

Tests the email-based one-time password generation and verification
functionality used for 2FA without authenticator apps.
"""

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from unittest.mock import AsyncMock, MagicMock, patch

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
    def mock_redis(self) -> AsyncMock:
        """Create a mock async Redis client."""
        redis = AsyncMock()
        redis.ttl = AsyncMock(return_value=0)
        redis.setex = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.delete = AsyncMock(return_value=0)
        return redis

    @pytest.fixture
    def handler(self, mock_redis: AsyncMock) -> EmailOTPHandler:
        """Create an EmailOTPHandler with mocked _get_redis."""
        h = EmailOTPHandler()
        # Patch _get_redis to return our mock
        h._get_redis = AsyncMock(return_value=mock_redis)  # type: ignore[method-assign]
        return h

    # ===========================================
    # Configuration Tests
    # ===========================================

    def test_default_configuration(self, handler: EmailOTPHandler) -> None:
        """Test default configuration values."""
        assert handler.OTP_LENGTH == 6
        assert handler.OTP_EXPIRY_MINUTES == 10
        assert handler.MAX_ATTEMPTS == 3
        assert handler.COOLDOWN_SECONDS == 60

    def test_constructor_no_args(self) -> None:
        """Test EmailOTPHandler can be created without arguments."""
        handler = EmailOTPHandler()
        assert handler is not None

    @pytest.mark.asyncio
    async def test_get_redis_uses_cache_infrastructure(self) -> None:
        """Test _get_redis gets client from cache infrastructure."""
        handler = EmailOTPHandler()
        mock_cache = MagicMock()
        mock_redis_client = AsyncMock()
        mock_cache.get_redis_client.return_value = mock_redis_client

        with patch(
            "app.infrastructure.cache.get_cache",
            return_value=mock_cache,
        ):
            result = await handler._get_redis()

        assert result is mock_redis_client

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

    @pytest.mark.asyncio
    async def test_can_generate_otp_no_cooldown(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test can_generate_otp returns True when no cooldown."""
        mock_redis.ttl.return_value = 0

        can_generate, remaining = await handler.can_generate_otp("user-123")

        assert can_generate is True
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_can_generate_otp_with_cooldown(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test can_generate_otp returns False during cooldown."""
        mock_redis.ttl.return_value = 30

        can_generate, remaining = await handler.can_generate_otp("user-123")

        assert can_generate is False
        assert remaining == 30

    @pytest.mark.asyncio
    async def test_can_generate_otp_expired_cooldown(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test can_generate_otp when cooldown key expired."""
        mock_redis.ttl.return_value = -2  # Key doesn't exist

        can_generate, remaining = await handler.can_generate_otp("user-123")

        assert can_generate is True
        assert remaining == 0

    # ===========================================
    # OTP Generation Tests
    # ===========================================

    @pytest.mark.asyncio
    async def test_generate_otp_success(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test successful OTP generation."""
        mock_redis.ttl.return_value = 0  # No cooldown

        code = await handler.generate_otp("user-123")

        assert code is not None
        assert len(code) == 6
        assert code.isdigit()

        # Verify Redis calls (OTP + cooldown)
        assert mock_redis.setex.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_otp_during_cooldown(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test OTP generation blocked during cooldown."""
        mock_redis.ttl.return_value = 45  # 45 seconds remaining

        code = await handler.generate_otp("user-123")

        assert code is None
        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_otp_custom_expiry(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test OTP generation with custom expiry."""
        mock_redis.ttl.return_value = 0

        code = await handler.generate_otp("user-123", expiry_minutes=5)

        assert code is not None
        # Check the OTP storage call used correct expiry (5 * 60 = 300 seconds)
        otp_call = mock_redis.setex.call_args_list[0]
        assert otp_call[0][1] == 300  # 5 minutes in seconds

    @pytest.mark.asyncio
    async def test_generate_otp_custom_purpose(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test OTP generation with custom purpose."""
        mock_redis.ttl.return_value = 0

        code = await handler.generate_otp("user-123", purpose="password_reset")

        assert code is not None
        otp_call = mock_redis.setex.call_args_list[0]
        key = otp_call[0][0]
        assert "password_reset" in key

    @pytest.mark.asyncio
    async def test_generate_otp_stores_hashed_code(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test OTP generation stores hashed code (not plaintext)."""
        mock_redis.ttl.return_value = 0

        code = await handler.generate_otp("user-123")

        otp_call = mock_redis.setex.call_args_list[0]
        stored_data = json.loads(otp_call[0][2])

        # Should store code_hash, not plaintext code
        assert "code_hash" in stored_data
        assert stored_data["code_hash"] == sha256(code.encode()).hexdigest()
        assert "expires_at" in stored_data
        assert stored_data["attempts"] == 0

    # ===========================================
    # OTP Verification Tests
    # ===========================================

    @pytest.mark.asyncio
    async def test_verify_otp_success(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test successful OTP verification."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        code = "123456"
        otp_data = json.dumps(
            {
                "code_hash": sha256(code.encode()).hexdigest(),
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = await handler.verify_otp("user-123", code)

        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_otp_no_otp_found(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test verification fails when no OTP exists."""
        mock_redis.get.return_value = None

        result = await handler.verify_otp("user-123", "123456")

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_otp_expired(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test verification fails for expired OTP."""
        code = "123456"
        expires_at = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code_hash": sha256(code.encode()).hexdigest(),
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = await handler.verify_otp("user-123", code)

        assert result is False
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_otp_wrong_code(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test verification fails for wrong code."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code_hash": sha256(b"123456").hexdigest(),
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = await handler.verify_otp("user-123", "654321")

        assert result is False
        # Should increment attempts
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_otp_increments_attempts(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test verification increments attempts on failure."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code_hash": sha256(b"123456").hexdigest(),
                "expires_at": expires_at,
                "attempts": 1,
            }
        )
        mock_redis.get.return_value = otp_data

        result = await handler.verify_otp("user-123", "000000")

        assert result is False

        # Check attempts were incremented
        setex_call = mock_redis.setex.call_args
        stored_data = json.loads(setex_call[0][2])
        assert stored_data["attempts"] == 2

    @pytest.mark.asyncio
    async def test_verify_otp_max_attempts_exceeded(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test verification fails when max attempts exceeded."""
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code_hash": sha256(b"123456").hexdigest(),
                "expires_at": expires_at,
                "attempts": 3,  # Max is 3
            }
        )
        mock_redis.get.return_value = otp_data

        result = await handler.verify_otp("user-123", "123456")

        assert result is False
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_otp_without_consume(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test verification without consuming OTP."""
        code = "123456"
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code_hash": sha256(code.encode()).hexdigest(),
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = await handler.verify_otp("user-123", code, consume=False)

        assert result is True
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_otp_strips_whitespace(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test verification strips whitespace from code."""
        code = "123456"
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code_hash": sha256(code.encode()).hexdigest(),
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = await handler.verify_otp("user-123", "  123456  ")

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_otp_custom_purpose(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test verification with custom purpose."""
        code = "123456"
        expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        otp_data = json.dumps(
            {
                "code_hash": sha256(code.encode()).hexdigest(),
                "expires_at": expires_at,
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        await handler.verify_otp("user-123", code, purpose="password_reset")

        mock_redis.get.assert_called_with("email_otp:password_reset:user-123")

    # ===========================================
    # OTP Invalidation Tests
    # ===========================================

    @pytest.mark.asyncio
    async def test_invalidate_otp_success(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test successful OTP invalidation."""
        mock_redis.delete.return_value = 1

        result = await handler.invalidate_otp("user-123")

        assert result is True
        mock_redis.delete.assert_called_with("email_otp:login:user-123")

    @pytest.mark.asyncio
    async def test_invalidate_otp_none_exists(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test invalidation when no OTP exists."""
        mock_redis.delete.return_value = 0

        result = await handler.invalidate_otp("user-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_otp_custom_purpose(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test invalidation with custom purpose."""
        mock_redis.delete.return_value = 1

        await handler.invalidate_otp("user-123", purpose="password_reset")

        mock_redis.delete.assert_called_with("email_otp:password_reset:user-123")

    # ===========================================
    # Remaining Attempts Tests
    # ===========================================

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_full(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test remaining attempts when no attempts made."""
        otp_data = json.dumps(
            {
                "code_hash": sha256(b"123456").hexdigest(),
                "expires_at": datetime.now(UTC).isoformat(),
                "attempts": 0,
            }
        )
        mock_redis.get.return_value = otp_data

        result = await handler.get_remaining_attempts("user-123")

        assert result == 3

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_some_used(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test remaining attempts when some attempts used."""
        otp_data = json.dumps(
            {
                "code_hash": sha256(b"123456").hexdigest(),
                "expires_at": datetime.now(UTC).isoformat(),
                "attempts": 2,
            }
        )
        mock_redis.get.return_value = otp_data

        result = await handler.get_remaining_attempts("user-123")

        assert result == 1

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_none_left(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test remaining attempts when all used."""
        otp_data = json.dumps(
            {
                "code_hash": sha256(b"123456").hexdigest(),
                "expires_at": datetime.now(UTC).isoformat(),
                "attempts": 3,
            }
        )
        mock_redis.get.return_value = otp_data

        result = await handler.get_remaining_attempts("user-123")

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_no_otp(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test remaining attempts when no OTP exists."""
        mock_redis.get.return_value = None

        result = await handler.get_remaining_attempts("user-123")

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_custom_purpose(
        self, handler: EmailOTPHandler, mock_redis: AsyncMock
    ) -> None:
        """Test remaining attempts with custom purpose."""
        otp_data = json.dumps(
            {
                "code_hash": sha256(b"123456").hexdigest(),
                "expires_at": datetime.now(UTC).isoformat(),
                "attempts": 1,
            }
        )
        mock_redis.get.return_value = otp_data

        await handler.get_remaining_attempts("user-123", purpose="password_reset")

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
