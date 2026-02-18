# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Email OTP Handler for 2FA.

Provides email-based one-time password generation and verification
as an alternative to TOTP for users without authenticator apps.
"""

import json
import secrets
import string
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import NamedTuple

from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class OTPData(NamedTuple):
    """OTP verification data."""

    code: str
    expires_at: datetime
    attempts: int


class EmailOTPHandler:
    """
    Handler for email-based OTP generation and verification.

    Features:
    - 6-digit numeric OTP codes
    - Configurable expiration (default 10 minutes)
    - Rate limiting (max 3 attempts per OTP)
    - Secure storage in Redis (async)

    Usage:
        handler = EmailOTPHandler()

        # Generate and send OTP
        code = await handler.generate_otp(user_id="user-123")
        await email_service.send_otp_email(email, code)

        # Verify OTP
        is_valid = await handler.verify_otp(user_id="user-123", code="123456")
    """

    # Configuration
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    MAX_ATTEMPTS = 3
    COOLDOWN_SECONDS = 60  # Between OTP generations

    async def _get_redis(
        self,
    ) -> object:  # redis.Redis — import avoided to keep dependency optional
        """Get async Redis connection via application cache infrastructure."""
        from app.infrastructure.cache import get_cache

        cache = get_cache()
        return cache.get_redis_client()

    def _generate_code(self) -> str:
        """Generate a secure 6-digit OTP code."""
        return "".join(secrets.choice(string.digits) for _ in range(self.OTP_LENGTH))

    def _get_key(self, user_id: str, purpose: str = "login") -> str:
        """Get Redis key for OTP storage."""
        return f"email_otp:{purpose}:{user_id}"

    def _get_cooldown_key(self, user_id: str) -> str:
        """Get Redis key for cooldown tracking."""
        return f"email_otp:cooldown:{user_id}"

    async def can_generate_otp(self, user_id: str) -> tuple[bool, int]:
        """
        Check if user can request a new OTP (cooldown check).

        Args:
            user_id: The user's ID

        Returns:
            Tuple of (can_generate, seconds_remaining)
        """
        r = await self._get_redis()
        cooldown_key = self._get_cooldown_key(user_id)
        ttl = await r.ttl(cooldown_key)

        if ttl and ttl > 0:
            return False, ttl
        return True, 0

    async def generate_otp(
        self,
        user_id: str,
        purpose: str = "login",
        expiry_minutes: int | None = None,
    ) -> str | None:
        """
        Generate a new OTP for the user.

        Args:
            user_id: The user's ID
            purpose: OTP purpose (login, password_reset, etc.)
            expiry_minutes: Custom expiry time in minutes

        Returns:
            The generated OTP code, or None if on cooldown
        """
        r = await self._get_redis()

        # Check cooldown
        can_generate, remaining = await self.can_generate_otp(user_id)
        if not can_generate:
            logger.warning(
                "otp_generation_blocked",
                user_id=user_id,
                cooldown_remaining=remaining,
            )
            return None

        # Generate OTP
        code = self._generate_code()
        expiry = expiry_minutes or self.OTP_EXPIRY_MINUTES
        expires_at = datetime.now(UTC) + timedelta(minutes=expiry)

        # Store OTP data (hash the code for at-rest security)
        key = self._get_key(user_id, purpose)
        otp_data = {
            "code_hash": sha256(code.encode()).hexdigest(),
            "expires_at": expires_at.isoformat(),
            "attempts": 0,
        }

        await r.setex(key, expiry * 60, json.dumps(otp_data))

        # Set cooldown
        cooldown_key = self._get_cooldown_key(user_id)
        await r.setex(cooldown_key, self.COOLDOWN_SECONDS, "1")

        logger.info("otp_generated", user_id=user_id, purpose=purpose)
        return code

    async def verify_otp(
        self,
        user_id: str,
        code: str,
        purpose: str = "login",
        consume: bool = True,
    ) -> bool:
        """
        Verify an OTP code.

        Args:
            user_id: The user's ID
            code: The OTP code to verify
            purpose: OTP purpose
            consume: Whether to invalidate the OTP after successful verification

        Returns:
            True if the OTP is valid
        """
        r = await self._get_redis()
        key = self._get_key(user_id, purpose)

        # Get stored OTP
        data = await r.get(key)
        if not data:
            logger.warning("otp_not_found", user_id=user_id)
            return False

        otp_data = json.loads(str(data))

        # Check expiration
        expires_at = datetime.fromisoformat(otp_data["expires_at"])
        if datetime.now(UTC) > expires_at:
            await r.delete(key)
            logger.warning("otp_expired", user_id=user_id)
            return False

        # Check attempts
        attempts = otp_data.get("attempts", 0)
        if attempts >= self.MAX_ATTEMPTS:
            await r.delete(key)
            logger.warning("otp_max_attempts_exceeded", user_id=user_id)
            return False

        # Verify code (timing-safe comparison against stored hash)
        import hmac as _hmac

        code = code.strip()
        code_hash = sha256(code.encode()).hexdigest()
        if not _hmac.compare_digest(code_hash, otp_data["code_hash"]):
            # Increment attempts
            otp_data["attempts"] = attempts + 1
            await r.setex(
                key,
                int((expires_at - datetime.now(UTC)).total_seconds()),
                json.dumps(otp_data),
            )
            logger.warning(
                "otp_invalid_attempt",
                attempt=attempts + 1,
                max_attempts=self.MAX_ATTEMPTS,
                user_id=user_id,
            )
            return False

        # Valid OTP
        if consume:
            await r.delete(key)
            logger.info("otp_verified", user_id=user_id)

        return True

    async def invalidate_otp(self, user_id: str, purpose: str = "login") -> bool:
        """
        Invalidate any pending OTP for the user.

        Args:
            user_id: The user's ID
            purpose: OTP purpose

        Returns:
            True if an OTP was invalidated
        """
        r = await self._get_redis()
        key = self._get_key(user_id, purpose)
        deleted = await r.delete(key)
        return bool(deleted)

    async def get_remaining_attempts(self, user_id: str, purpose: str = "login") -> int:
        """
        Get remaining verification attempts for current OTP.

        Args:
            user_id: The user's ID
            purpose: OTP purpose

        Returns:
            Number of remaining attempts, or 0 if no OTP exists
        """
        r = await self._get_redis()
        key = self._get_key(user_id, purpose)

        data = await r.get(key)
        if not data:
            return 0

        otp_data = json.loads(str(data))
        attempts = otp_data.get("attempts", 0)
        return max(0, self.MAX_ATTEMPTS - attempts)


# Singleton instance
_email_otp_handler: EmailOTPHandler | None = None


def get_email_otp_handler() -> EmailOTPHandler:
    """Get the singleton Email OTP handler instance."""
    global _email_otp_handler
    if _email_otp_handler is None:
        _email_otp_handler = EmailOTPHandler()
    return _email_otp_handler
