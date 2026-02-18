# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for API key authentication."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities.api_key import APIKey
from app.infrastructure.auth.api_key_handler import APIKeyHandler


class TestAPIKeyEntity:
    """Tests for APIKey entity."""

    def test_create_api_key(self):
        """Should create API key with valid data."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Key",
            prefix="krs_abc123",
            key_hash="hashed_value",
            scopes=["read:users", "write:users"],
            is_active=True,
            last_used_at=None,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            created_at=datetime.now(UTC),
        )

        assert key.name == "Test Key"
        assert key.is_active is True
        assert len(key.scopes) == 2

    def test_has_scope_exact_match(self):
        """Should match exact scope."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Key",
            prefix="krs_abc123",
            key_hash="hashed_value",
            scopes=["read:users", "write:users"],
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert key.has_scope("read:users") is True
        assert key.has_scope("write:users") is True
        assert key.has_scope("delete:users") is False

    def test_has_scope_wildcard(self):
        """Should match wildcard scope."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Admin Key",
            prefix="krs_admin",
            key_hash="hashed_value",
            scopes=["*"],
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert key.has_scope("read:users") is True
        assert key.has_scope("write:tenants") is True
        assert key.has_scope("any:scope") is True

    def test_has_scope_resource_wildcard(self):
        """Should match resource-specific wildcard."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Users Manager",
            prefix="krs_users",
            key_hash="hashed_value",
            scopes=["users:*"],
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert key.has_scope("users:read") is True
        assert key.has_scope("users:write") is True
        assert key.has_scope("tenants:read") is False

    def test_is_expired(self):
        """Should correctly identify expired keys."""
        # Non-expired key
        active_key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Active Key",
            prefix="krs_active",
            key_hash="hashed_value",
            scopes=["read:users"],
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            created_at=datetime.now(UTC),
        )
        assert active_key.is_expired is False

        # Expired key
        expired_key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Expired Key",
            prefix="krs_expired",
            key_hash="hashed_value",
            scopes=["read:users"],
            is_active=True,
            expires_at=datetime.now(UTC) - timedelta(days=1),
            created_at=datetime.now(UTC),
        )
        assert expired_key.is_expired is True

        # No expiration (never expires)
        permanent_key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Permanent Key",
            prefix="krs_perm",
            key_hash="hashed_value",
            scopes=["read:users"],
            is_active=True,
            expires_at=None,
            created_at=datetime.now(UTC),
        )
        assert permanent_key.is_expired is False


class TestAPIKeyHandler:
    """Tests for API key handler."""

    @pytest.fixture
    def handler(self):
        """Create API key handler."""
        return APIKeyHandler()

    def test_generate_api_key_format(self, handler):
        """Generated key should have correct format."""
        full_key, prefix, key_hash = handler.generate_api_key()

        # Check format: krs_<base64 urlsafe chars>
        assert full_key.startswith("krs_")
        # token_urlsafe(32) generates ~43 chars, so total is ~47
        assert len(full_key) > 40

        # Prefix is first 8 chars of the random part
        assert len(prefix) == 8

        # Hash should be SHA-256 format (64 hex characters)
        assert len(key_hash) == 64
        assert all(c in "0123456789abcdef" for c in key_hash)

    def test_generate_unique_keys(self, handler):
        """Generated keys should be unique."""
        keys = [handler.generate_api_key()[0] for _ in range(10)]
        assert len(set(keys)) == 10

    def test_verify_key(self, handler):
        """Should verify correct key."""
        full_key, _, key_hash = handler.generate_api_key()

        assert handler.verify_key(full_key, key_hash) is True
        assert handler.verify_key("wrong_key", key_hash) is False

    def test_hash_key(self, handler):
        """Should hash key deterministically with SHA-256."""
        key = "krs_test1234567890123456789012"

        hash1 = handler.hash_key(key)
        hash2 = handler.hash_key(key)

        # SHA-256 is deterministic — same input produces same hash
        assert hash1 == hash2

        # Should verify
        assert handler.verify_key(key, hash1) is True

    def test_extract_prefix(self, handler):
        """Should extract prefix correctly."""
        key = "krs_abcdef123456789012345678901234"
        prefix = handler.extract_prefix(key)

        assert prefix == "krs_abcdef12"
        assert len(prefix) == 12

    def test_extract_prefix_short_key(self, handler):
        """Should handle short keys."""
        key = "krs_abc"
        prefix = handler.extract_prefix(key)

        # Should return full key if shorter than prefix length
        assert prefix == key

    def test_validate_format_valid_key(self, handler):
        """Should validate correct key format."""
        full_key, _, _ = handler.generate_api_key()
        assert handler.validate_format(full_key) is True

    def test_validate_format_wrong_prefix(self, handler):
        """Should reject key with wrong prefix."""
        assert handler.validate_format("wrong_prefix123456789012345678901234") is False

    def test_validate_format_empty_key(self, handler):
        """Should reject empty key."""
        assert handler.validate_format("") is False
        assert handler.validate_format(None) is False  # type: ignore

    def test_validate_format_short_key(self, handler):
        """Should reject too short key."""
        assert handler.validate_format("krs_short") is False

    def test_validate_format_no_underscore(self, handler):
        """Should reject key without underscore."""
        assert handler.validate_format("krsabcdefghijklmnopqrstuvwxyz12345") is False


class TestAPIKeyScopes:
    """Additional tests for API key scope handling."""

    def test_has_all_scopes_exact_match(self):
        """Test has_all_scopes with exact matches."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            prefix="krs_test",
            key_hash="hash",
            scopes=["read:users", "write:users", "read:roles"],
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert key.has_all_scopes(["read:users"]) is True
        assert key.has_all_scopes(["read:users", "write:users"]) is True
        assert key.has_all_scopes(["delete:users"]) is False

    def test_has_all_scopes_with_wildcard(self):
        """Test has_all_scopes with wildcard."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Admin",
            prefix="krs_admin",
            key_hash="hash",
            scopes=["*"],
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert key.has_all_scopes(["read:users"]) is True
        assert key.has_all_scopes(["write:users", "delete:roles"]) is True
        assert key.has_all_scopes(["anything:at:all"]) is True

    def test_has_all_scopes_empty_required(self):
        """Test has_all_scopes with empty required list."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            prefix="krs_test",
            key_hash="hash",
            scopes=["read:users"],
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert key.has_all_scopes([]) is True

    def test_api_key_is_valid(self):
        """Test is_valid property checks active and not expired."""
        # Active, not expired
        valid_key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Valid",
            prefix="krs_valid",
            key_hash="hash",
            scopes=["*"],
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            created_at=datetime.now(UTC),
        )
        assert valid_key.is_valid is True

        # Inactive
        inactive_key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Inactive",
            prefix="krs_inactive",
            key_hash="hash",
            scopes=["*"],
            is_active=False,
            created_at=datetime.now(UTC),
        )
        assert inactive_key.is_valid is False

    def test_api_key_usage_tracking(self):
        """Test API key tracks usage count."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            name="Tracked",
            prefix="krs_track",
            key_hash="hash",
            scopes=["read:users"],
            is_active=True,
            usage_count=42,
            created_at=datetime.now(UTC),
        )

        assert key.usage_count == 42
