# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for API Key Handler.

Tests key generation, validation, and authentication logic.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.infrastructure.auth.api_key_handler import (
    API_KEY_PREFIX,
    API_KEY_LENGTH,
    APIKeyHandler,
    generate_api_key,
    validate_api_key_format,
)


class TestAPIKeyGeneration:
    """Tests for API key generation."""

    def test_generate_api_key_returns_tuple(self) -> None:
        """Test that generate_api_key returns a tuple of 3 elements."""
        result = generate_api_key()
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        
    def test_generate_api_key_full_key_format(self) -> None:
        """Test that full key starts with correct prefix."""
        full_key, prefix, key_hash = generate_api_key()
        
        assert full_key.startswith(f"{API_KEY_PREFIX}_")
        
    def test_generate_api_key_prefix_length(self) -> None:
        """Test that prefix has correct length."""
        full_key, prefix, key_hash = generate_api_key()
        
        assert len(prefix) == 8
        
    def test_generate_api_key_hash_is_string(self) -> None:
        """Test that key hash is a non-empty string."""
        full_key, prefix, key_hash = generate_api_key()
        
        assert isinstance(key_hash, str)
        assert len(key_hash) > 0
        
    def test_generate_api_key_uniqueness(self) -> None:
        """Test that each key generation produces unique keys."""
        keys = [generate_api_key()[0] for _ in range(10)]
        
        assert len(set(keys)) == 10

    def test_generate_api_key_prefix_matches_key(self) -> None:
        """Test that prefix matches the random part of the key."""
        full_key, prefix, key_hash = generate_api_key()
        
        # Extract random part from full key
        random_part = full_key[len(API_KEY_PREFIX) + 1:]
        
        # Prefix should be first 8 chars of random part
        assert random_part[:8] == prefix


class TestAPIKeyValidation:
    """Tests for API key format validation."""
    
    def test_validate_empty_key(self) -> None:
        """Test that empty key is invalid."""
        assert validate_api_key_format("") is False
        
    def test_validate_none_key(self) -> None:
        """Test that None key is invalid."""
        assert validate_api_key_format(None) is False  # type: ignore
        
    def test_validate_wrong_prefix(self) -> None:
        """Test that wrong prefix is invalid."""
        assert validate_api_key_format("abc_randomkey12345678901234567890") is False
        
    def test_validate_no_underscore(self) -> None:
        """Test that key without underscore is invalid."""
        assert validate_api_key_format("krsrandomkey12345678901234567890") is False
        
    def test_validate_short_key(self) -> None:
        """Test that short key is invalid."""
        assert validate_api_key_format("krs_short") is False
        
    def test_validate_valid_key(self) -> None:
        """Test that valid key is accepted."""
        full_key, _, _ = generate_api_key()
        assert validate_api_key_format(full_key) is True
        
    def test_validate_minimum_length(self) -> None:
        """Test minimum length requirement."""
        # krs_ + 20 characters minimum
        min_key = f"{API_KEY_PREFIX}_" + "a" * 20
        assert validate_api_key_format(min_key) is True
        
        # Just below minimum
        short_key = f"{API_KEY_PREFIX}_" + "a" * 19
        assert validate_api_key_format(short_key) is False


class TestAPIKeyHandler:
    """Tests for APIKeyHandler class."""
    
    @pytest.fixture
    def handler(self) -> APIKeyHandler:
        """Create handler instance."""
        return APIKeyHandler()
    
    def test_generate_api_key(self, handler: APIKeyHandler) -> None:
        """Test handler generate_api_key method."""
        full_key, prefix, key_hash = handler.generate_api_key()
        
        assert full_key.startswith(f"{API_KEY_PREFIX}_")
        assert len(prefix) == 8
        assert len(key_hash) > 0
        
    def test_validate_format_valid(self, handler: APIKeyHandler) -> None:
        """Test handler validate_format with valid key."""
        full_key, _, _ = handler.generate_api_key()
        
        assert handler.validate_format(full_key) is True
        
    def test_validate_format_invalid(self, handler: APIKeyHandler) -> None:
        """Test handler validate_format with invalid key."""
        assert handler.validate_format("invalid") is False
        
    def test_hash_key(self, handler: APIKeyHandler) -> None:
        """Test key hashing."""
        key = "test_key_12345678901234567890"
        hashed = handler.hash_key(key)
        
        assert isinstance(hashed, str)
        assert hashed != key
        
    def test_verify_key_correct(self, handler: APIKeyHandler) -> None:
        """Test key verification with correct key."""
        full_key, _, key_hash = handler.generate_api_key()
        
        assert handler.verify_key(full_key, key_hash) is True
        
    def test_verify_key_incorrect(self, handler: APIKeyHandler) -> None:
        """Test key verification with incorrect key."""
        _, _, key_hash = handler.generate_api_key()
        
        assert handler.verify_key("wrong_key", key_hash) is False
        
    def test_extract_prefix_full_key(self, handler: APIKeyHandler) -> None:
        """Test prefix extraction from full key."""
        full_key, _, _ = handler.generate_api_key()
        
        extracted = handler.extract_prefix(full_key)
        
        assert len(extracted) == 12
        
    def test_extract_prefix_short_key(self, handler: APIKeyHandler) -> None:
        """Test prefix extraction from short key."""
        short_key = "krs_abc"
        
        extracted = handler.extract_prefix(short_key)
        
        assert extracted == short_key


class TestAPIKeyConstants:
    """Tests for API key constants."""
    
    def test_api_key_prefix(self) -> None:
        """Test API key prefix value."""
        assert API_KEY_PREFIX == "krs"
        
    def test_api_key_length(self) -> None:
        """Test API key length value."""
        assert API_KEY_LENGTH == 32


class TestAuthenticateAPIKey:
    """Tests for authenticate_api_key function."""

    @pytest.mark.asyncio
    async def test_authenticate_invalid_format(self) -> None:
        """Test authentication with invalid key format."""
        from app.infrastructure.auth.api_key_handler import authenticate_api_key
        from app.domain.exceptions.base import AuthenticationError
        
        session = AsyncMock()
        
        with pytest.raises(AuthenticationError) as exc_info:
            await authenticate_api_key(session, "invalid_key")
        
        assert "Invalid API key format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_key_not_found(self) -> None:
        """Test authentication when key is not found."""
        from app.infrastructure.auth.api_key_handler import authenticate_api_key
        from app.domain.exceptions.base import AuthenticationError
        
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)
        
        full_key, _, _ = generate_api_key()
        
        with pytest.raises(AuthenticationError) as exc_info:
            await authenticate_api_key(session, full_key)
        
        assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_key_expired(self) -> None:
        """Test authentication with expired key."""
        from app.infrastructure.auth.api_key_handler import authenticate_api_key
        from app.domain.exceptions.base import AuthenticationError
        
        session = AsyncMock()
        full_key, prefix, key_hash = generate_api_key()
        
        # Create mock model with expired key
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.prefix = prefix
        mock_model.key_hash = key_hash
        mock_model.is_active = True
        mock_model.is_deleted = False
        mock_model.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        session.execute = AsyncMock(return_value=mock_result)
        
        with patch("app.infrastructure.auth.api_key_handler.verify_password", return_value=True):
            with pytest.raises(AuthenticationError) as exc_info:
                await authenticate_api_key(session, full_key)
        
        assert "expired" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_key_success(self) -> None:
        """Test successful key authentication."""
        from app.infrastructure.auth.api_key_handler import authenticate_api_key
        
        session = AsyncMock()
        full_key, prefix, key_hash = generate_api_key()
        key_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        
        # Create mock model
        mock_model = MagicMock()
        mock_model.id = key_id
        mock_model.tenant_id = tenant_id
        mock_model.prefix = prefix
        mock_model.key_hash = key_hash
        mock_model.name = "Test Key"
        mock_model.user_id = user_id
        mock_model.scopes = ["read:users"]
        mock_model.is_active = True
        mock_model.is_deleted = False
        mock_model.expires_at = None
        mock_model.last_used_at = None
        mock_model.last_used_ip = None
        mock_model.usage_count = 0
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.updated_at = datetime.now(timezone.utc)
        mock_model.created_by = user_id
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()
        
        with patch("app.infrastructure.auth.api_key_handler.verify_password", return_value=True):
            result = await authenticate_api_key(session, full_key)
        
        assert result.id == key_id
        assert mock_model.usage_count == 1

    @pytest.mark.asyncio
    async def test_authenticate_key_missing_scopes(self) -> None:
        """Test authentication when key lacks required scopes."""
        from app.infrastructure.auth.api_key_handler import authenticate_api_key
        from app.domain.exceptions.base import AuthorizationError
        
        session = AsyncMock()
        full_key, prefix, key_hash = generate_api_key()
        key_id = uuid4()
        
        mock_model = MagicMock()
        mock_model.id = key_id
        mock_model.tenant_id = uuid4()
        mock_model.prefix = prefix
        mock_model.key_hash = key_hash
        mock_model.name = "Test Key"
        mock_model.user_id = uuid4()
        mock_model.scopes = ["read:users"]
        mock_model.is_active = True
        mock_model.is_deleted = False
        mock_model.expires_at = None
        mock_model.last_used_at = None
        mock_model.last_used_ip = None
        mock_model.usage_count = 0
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.updated_at = datetime.now(timezone.utc)
        mock_model.created_by = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()
        
        with patch("app.infrastructure.auth.api_key_handler.verify_password", return_value=True):
            with pytest.raises(AuthorizationError):
                await authenticate_api_key(session, full_key, required_scopes=["admin:write"])


class TestCreateAPIKey:
    """Tests for create_api_key function."""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self) -> None:
        """Test successful API key creation."""
        from app.infrastructure.auth.api_key_handler import create_api_key
        
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        
        tenant_id = uuid4()
        user_id = uuid4()
        
        # Mock the model after refresh
        def set_model_attrs(model):
            model.id = uuid4()
            model.created_at = datetime.now(timezone.utc)
            model.updated_at = datetime.now(timezone.utc)
            model.last_used_at = None
            model.last_used_ip = None
            model.usage_count = 0
            model.is_deleted = False
            model.deleted_at = None
        
        session.refresh.side_effect = set_model_attrs
        
        plain_key, api_key = await create_api_key(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            name="Test API Key",
            scopes=["read:users", "write:users"],
            expires_in_days=30,
        )
        
        assert plain_key.startswith(f"{API_KEY_PREFIX}_")
        assert api_key.name == "Test API Key"
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_api_key_no_expiration(self) -> None:
        """Test API key creation without expiration."""
        from app.infrastructure.auth.api_key_handler import create_api_key
        
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        
        def set_model_attrs(model):
            model.id = uuid4()
            model.created_at = datetime.now(timezone.utc)
            model.updated_at = datetime.now(timezone.utc)
            model.last_used_at = None
            model.last_used_ip = None
            model.usage_count = 0
            model.is_deleted = False
            model.deleted_at = None
            model.expires_at = None
        
        session.refresh = AsyncMock(side_effect=set_model_attrs)
        
        tenant_id = uuid4()
        user_id = uuid4()
        
        plain_key, api_key = await create_api_key(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            name="No Expiry Key",
            scopes=["read:users"],
        )
        
        assert api_key.expires_at is None


class TestRevokeAPIKey:
    """Tests for revoke_api_key function."""

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self) -> None:
        """Test successful API key revocation."""
        from app.infrastructure.auth.api_key_handler import revoke_api_key
        
        session = AsyncMock()
        key_id = uuid4()
        user_id = uuid4()
        
        mock_model = MagicMock()
        mock_model.id = key_id
        mock_model.is_active = True
        mock_model.is_deleted = False
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()
        
        result = await revoke_api_key(session, key_id, user_id)
        
        assert result is True
        assert mock_model.is_active is False
        assert mock_model.is_deleted is True

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self) -> None:
        """Test revocation when key is not found."""
        from app.infrastructure.auth.api_key_handler import revoke_api_key
        
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        result = await revoke_api_key(session, uuid4(), uuid4())
        
        assert result is False


class TestListUserAPIKeys:
    """Tests for list_user_api_keys function."""

    @pytest.mark.asyncio
    async def test_list_user_api_keys_active_only(self) -> None:
        """Test listing active API keys for user."""
        from app.infrastructure.auth.api_key_handler import list_user_api_keys
        
        session = AsyncMock()
        user_id = uuid4()
        
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.tenant_id = uuid4()
        mock_model.prefix = "abc12345"
        mock_model.key_hash = "hashed"
        mock_model.name = "Test Key"
        mock_model.user_id = user_id
        mock_model.scopes = ["read:users"]
        mock_model.is_active = True
        mock_model.is_deleted = False
        mock_model.expires_at = None
        mock_model.last_used_at = None
        mock_model.last_used_ip = None
        mock_model.usage_count = 0
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.updated_at = datetime.now(timezone.utc)
        mock_model.created_by = user_id
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        session.execute = AsyncMock(return_value=mock_result)
        
        result = await list_user_api_keys(session, user_id)
        
        assert len(result) == 1
        assert result[0].name == "Test Key"

    @pytest.mark.asyncio
    async def test_list_user_api_keys_include_revoked(self) -> None:
        """Test listing API keys including revoked ones."""
        from app.infrastructure.auth.api_key_handler import list_user_api_keys
        
        session = AsyncMock()
        user_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)
        
        result = await list_user_api_keys(session, user_id, include_revoked=True)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_list_user_api_keys_empty(self) -> None:
        """Test listing API keys when user has none."""
        from app.infrastructure.auth.api_key_handler import list_user_api_keys
        
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)
        
        result = await list_user_api_keys(session, uuid4())
        
        assert result == []


class TestModelToEntity:
    """Tests for _model_to_entity function."""

    def test_model_to_entity_conversion(self) -> None:
        """Test model to entity conversion."""
        from app.infrastructure.auth.api_key_handler import _model_to_entity
        
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.tenant_id = uuid4()
        mock_model.prefix = "abc12345"
        mock_model.key_hash = "hashed"
        mock_model.name = "Test Key"
        mock_model.user_id = uuid4()
        mock_model.scopes = ["read:users"]
        mock_model.is_active = True
        mock_model.is_deleted = False
        mock_model.expires_at = None
        mock_model.last_used_at = None
        mock_model.last_used_ip = None
        mock_model.usage_count = 5
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.updated_at = datetime.now(timezone.utc)
        mock_model.created_by = uuid4()
        mock_model.deleted_at = None
        
        entity = _model_to_entity(mock_model)
        
        assert entity.id == mock_model.id
        assert entity.name == mock_model.name
        assert entity.scopes == ["read:users"]
        assert entity.usage_count == 5

    def test_model_to_entity_null_scopes(self) -> None:
        """Test model to entity with null scopes."""
        from app.infrastructure.auth.api_key_handler import _model_to_entity
        
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.tenant_id = uuid4()
        mock_model.prefix = "abc12345"
        mock_model.key_hash = "hashed"
        mock_model.name = "Test Key"
        mock_model.user_id = uuid4()
        mock_model.scopes = None
        mock_model.is_active = True
        mock_model.is_deleted = False
        mock_model.expires_at = None
        mock_model.last_used_at = None
        mock_model.last_used_ip = None
        mock_model.usage_count = 0
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.updated_at = datetime.now(timezone.utc)
        mock_model.created_by = uuid4()
        mock_model.deleted_at = None
        
        entity = _model_to_entity(mock_model)
        
        assert entity.scopes == []
