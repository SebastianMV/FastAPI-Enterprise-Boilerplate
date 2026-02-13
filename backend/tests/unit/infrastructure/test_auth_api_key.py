# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Comprehensive tests for API Key Handler."""

import pytest

from app.infrastructure.auth.api_key_handler import (
    API_KEY_LENGTH,
    API_KEY_PREFIX,
    APIKeyHandler,
    generate_api_key,
    validate_api_key_format,
)


class TestGenerateAPIKey:
    """Tests for API key generation."""

    def test_generate_api_key_format(self):
        """Should generate API key with correct format."""
        full_key, prefix, key_hash = generate_api_key()

        assert full_key.startswith(f"{API_KEY_PREFIX}_")
        assert len(full_key) > len(API_KEY_PREFIX) + 1
        assert isinstance(prefix, str)
        assert isinstance(key_hash, str)

    def test_generate_api_key_uniqueness(self):
        """Should generate unique keys."""
        key1, _, _ = generate_api_key()
        key2, _, _ = generate_api_key()

        assert key1 != key2

    def test_generate_api_key_prefix_extraction(self):
        """Should extract prefix correctly."""
        full_key, prefix, _ = generate_api_key()

        # Prefix should be first 8 chars of the random part (after the prefix separator)
        random_part = full_key.split("_")[1]
        expected_prefix = random_part[:8]
        assert prefix == expected_prefix

    def test_generate_api_key_hash_is_bcrypt(self):
        """Should hash key using SHA-256."""
        _, _, key_hash = generate_api_key()

        # SHA-256 hashes are 64 hex characters
        assert len(key_hash) == 64
        assert all(c in '0123456789abcdef' for c in key_hash)

    def test_generate_api_key_returns_tuple(self):
        """Should return tuple of 3 elements."""
        result = generate_api_key()

        assert isinstance(result, tuple)
        assert len(result) == 3


class TestValidateAPIKeyFormat:
    """Tests for API key format validation."""

    def test_validate_valid_key(self):
        """Should validate correct API key format."""
        key, _, _ = generate_api_key()

        is_valid = validate_api_key_format(key)

        assert is_valid is True

    def test_validate_key_with_correct_prefix(self):
        """Should validate key with correct prefix."""
        # Need minimum 20 chars after prefix_
        valid_key = f"{API_KEY_PREFIX}_abcdef1234567890abcdef"

        is_valid = validate_api_key_format(valid_key)

        assert is_valid is True

    def test_validate_key_with_wrong_prefix(self):
        """Should reject key with wrong prefix."""
        invalid_key = "wrong_abcdef1234567890"

        is_valid = validate_api_key_format(invalid_key)

        assert is_valid is False

    def test_validate_key_without_underscore(self):
        """Should reject key without underscore separator."""
        invalid_key = "krsabcdef1234567890"

        is_valid = validate_api_key_format(invalid_key)

        assert is_valid is False

    def test_validate_empty_key(self):
        """Should reject empty key."""
        is_valid = validate_api_key_format("")

        assert is_valid is False

    def test_validate_too_short_key(self):
        """Should reject too short key."""
        short_key = f"{API_KEY_PREFIX}_abc"

        is_valid = validate_api_key_format(short_key)

        assert is_valid is False

    def test_validate_none_key(self):
        """Should handle None gracefully."""
        # Returns False instead of raising
        is_valid = validate_api_key_format(None)
        assert is_valid is False


class TestAPIKeyHandler:
    """Tests for APIKeyHandler class."""

    @pytest.fixture
    def handler(self):
        """Create APIKeyHandler instance."""
        return APIKeyHandler()

    def test_generate_api_key(self, handler):
        """Should generate API key using handler."""
        full_key, prefix, key_hash = handler.generate_api_key()

        assert full_key is not None
        assert prefix is not None
        assert key_hash is not None

    def test_validate_format(self, handler):
        """Should validate format using handler."""
        key, _, _ = handler.generate_api_key()

        is_valid = handler.validate_format(key)

        assert is_valid is True

    def test_hash_key(self, handler):
        """Should hash key using handler."""
        key = "test_key_12345"

        hashed = handler.hash_key(key)

        assert hashed is not None
        # SHA-256 hashes are 64 hex characters
        assert len(hashed) == 64
        assert all(c in '0123456789abcdef' for c in hashed)

    def test_verify_key_correct(self, handler):
        """Should verify correct key."""
        plain_key = "test_api_key"
        hashed_key = handler.hash_key(plain_key)

        is_valid = handler.verify_key(plain_key, hashed_key)

        assert is_valid is True

    def test_verify_key_incorrect(self, handler):
        """Should reject incorrect key."""
        plain_key = "correct_key"
        wrong_key = "wrong_key"
        hashed_key = handler.hash_key(plain_key)

        is_valid = handler.verify_key(wrong_key, hashed_key)

        assert is_valid is False

    def test_extract_prefix(self, handler):
        """Should extract prefix from full key."""
        key = f"{API_KEY_PREFIX}_abcdef1234567890xyz"

        prefix = handler.extract_prefix(key)

        assert len(prefix) == 12
        assert prefix == key[:12]

    def test_extract_prefix_short_key(self, handler):
        """Should handle short keys."""
        short_key = "abc"

        prefix = handler.extract_prefix(short_key)

        assert prefix == "abc"


class TestAPIKeyConstants:
    """Tests for API key constants."""

    def test_api_key_prefix(self):
        """Should have correct prefix."""
        assert API_KEY_PREFIX == "krs"
        assert isinstance(API_KEY_PREFIX, str)

    def test_api_key_length(self):
        """Should have reasonable length."""
        assert API_KEY_LENGTH > 0
        assert API_KEY_LENGTH == 32


class TestAPIKeyEdgeCases:
    """Edge case tests for API key operations."""

    @pytest.fixture
    def handler(self):
        """Create handler."""
        return APIKeyHandler()

    def test_generate_multiple_keys_are_unique(self, handler):
        """Should generate unique keys every time."""
        keys = [handler.generate_api_key()[0] for _ in range(10)]

        # All keys should be unique
        assert len(keys) == len(set(keys))

    def test_hash_same_key_produces_same_hash(self, handler):
        """Should produce identical hashes (SHA-256 is deterministic)."""
        key = "same_key"

        hash1 = handler.hash_key(key)
        hash2 = handler.hash_key(key)

        assert hash1 == hash2

    def test_verify_key_with_empty_strings(self, handler):
        """Should handle empty strings."""
        hashed = handler.hash_key("key")

        is_valid = handler.verify_key("", hashed)

        assert is_valid is False

    def test_key_contains_url_safe_characters(self):
        """Generated keys should be URL safe."""
        key, _, _ = generate_api_key()

        # Should only contain alphanumeric, underscore, and hyphen
        import string

        allowed = string.ascii_letters + string.digits + "_-"
        assert all(c in allowed for c in key)

    def test_prefix_extraction_consistency(self, handler):
        """Prefix should be consistent with generation."""
        full_key, generated_prefix, _ = handler.generate_api_key()
        extracted_prefix = handler.extract_prefix(full_key)

        # The extracted prefix (first 12 chars) should contain the generated prefix
        assert generated_prefix in extracted_prefix


class TestAPIKeyIntegration:
    """Integration tests for complete API key flow."""

    @pytest.fixture
    def handler(self):
        """Create handler."""
        return APIKeyHandler()

    def test_complete_key_lifecycle(self, handler):
        """Test complete flow: generate -> validate -> hash -> verify."""
        # Generate
        full_key, prefix, key_hash = handler.generate_api_key()

        # Validate format
        assert handler.validate_format(full_key) is True

        # Hash again (simulate storage)
        stored_hash = handler.hash_key(full_key)

        # Verify
        assert handler.verify_key(full_key, stored_hash) is True

    def test_key_verification_after_generation(self, handler):
        """Generated hash should verify original key."""
        full_key, prefix, generated_hash = handler.generate_api_key()

        # The generated hash should verify the full key
        is_valid = handler.verify_key(full_key, generated_hash)

        assert is_valid is True

    def test_different_keys_dont_verify(self, handler):
        """Different keys should not verify each other."""
        key1, _, hash1 = handler.generate_api_key()
        key2, _, hash2 = handler.generate_api_key()

        # Key1 should not verify against hash2
        assert handler.verify_key(key1, hash2) is False
        assert handler.verify_key(key2, hash1) is False
