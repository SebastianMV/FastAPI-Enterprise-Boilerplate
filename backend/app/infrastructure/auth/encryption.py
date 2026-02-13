# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Symmetric encryption utility for at-rest secrets (MFA, OAuth tokens, etc.).

Uses Fernet (AES-128-CBC + HMAC-SHA256).
When ENCRYPTION_KEY is configured, it is used directly.
Otherwise, a key is derived from JWT_SECRET_KEY (dev convenience only).
"""

import base64

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.infrastructure.observability.logging import get_logger

_logger = get_logger(__name__)


def _derive_fernet_key(secret: str) -> bytes:
    """Derive a 32-byte URL-safe base64-encoded key from an arbitrary secret.

    Uses HKDF (HMAC-based Key Derivation Function) which is the
    recommended approach for deriving encryption keys from secrets.
    """
    from cryptography.hazmat.primitives import hashes as _hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    hkdf = HKDF(
        algorithm=_hashes.SHA256(),
        length=32,
        salt=None,
        info=b"fernet-encryption-key",
    )
    raw = hkdf.derive(secret.encode())
    return base64.urlsafe_b64encode(raw)


def _get_fernet() -> Fernet:
    """Return a Fernet instance keyed to the configured encryption secret."""
    if settings.ENCRYPTION_KEY:
        # Use the dedicated encryption key (preferred in production)
        key = _derive_fernet_key(settings.ENCRYPTION_KEY)
    else:
        # Fallback: derive from JWT secret (dev/test convenience)
        if settings.ENVIRONMENT not in ("development", "testing"):
            raise ValueError("ENCRYPTION_KEY must be set outside development/testing")
        _logger.warning(
            "encryption_key_fallback_to_jwt_secret",
            environment="development",
        )
        key = _derive_fernet_key(settings.JWT_SECRET_KEY)
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a plaintext string.

    Returns a URL-safe base64-encoded ciphertext string.
    """
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt a ciphertext string produced by ``encrypt_value``.

    Raises ``ValueError`` if the ciphertext is invalid or tampered with.
    """
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Failed to decrypt value — invalid or tampered ciphertext"
        ) from exc
