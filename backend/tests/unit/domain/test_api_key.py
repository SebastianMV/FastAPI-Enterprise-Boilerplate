# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for APIKey domain entity.

Tests for API key functionality including scopes and usage tracking.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.entities.api_key import APIKey


class TestAPIKey:
    """Tests for APIKey entity."""

    def test_create_basic_api_key(self) -> None:
        """Test creating basic API key."""
        tenant_id = uuid4()
        user_id = uuid4()

        api_key = APIKey(
            tenant_id=tenant_id,
            user_id=user_id,
            name="Test API Key",
            prefix="test1234",
            key_hash="hashed_key_value",
        )

        assert api_key.tenant_id == tenant_id
        assert api_key.user_id == user_id
        assert api_key.name == "Test API Key"
        assert api_key.prefix == "test1234"

    def test_default_values(self) -> None:
        """Test default values."""
        api_key = APIKey(tenant_id=uuid4())

        assert api_key.name == ""
        assert api_key.prefix == ""
        assert api_key.key_hash == ""
        assert api_key.scopes == []
        assert api_key.is_active is True
        assert api_key.expires_at is None
        assert api_key.last_used_at is None
        assert api_key.last_used_ip is None
        assert api_key.usage_count == 0
        assert api_key.is_deleted is False
        assert api_key.deleted_at is None

    def test_with_scopes(self) -> None:
        """Test API key with scopes."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["users:read", "users:write", "roles:read"],
        )

        assert len(api_key.scopes) == 3
        assert "users:read" in api_key.scopes

    def test_with_expiration(self) -> None:
        """Test API key with expiration."""
        expires = datetime.now(UTC) + timedelta(days=30)
        api_key = APIKey(
            tenant_id=uuid4(),
            expires_at=expires,
        )

        assert api_key.expires_at == expires


class TestAPIKeyIsExpired:
    """Tests for is_expired property."""

    def test_not_expired_when_no_expiration(self) -> None:
        """Test key is not expired when no expiration set."""
        api_key = APIKey(tenant_id=uuid4(), expires_at=None)

        assert api_key.is_expired is False

    def test_not_expired_when_future_expiration(self) -> None:
        """Test key is not expired when expiration is in future."""
        api_key = APIKey(
            tenant_id=uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )

        assert api_key.is_expired is False

    def test_expired_when_past_expiration(self) -> None:
        """Test key is expired when expiration is in past."""
        api_key = APIKey(
            tenant_id=uuid4(),
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )

        assert api_key.is_expired is True


class TestAPIKeyIsValid:
    """Tests for is_valid property."""

    def test_valid_when_active_and_not_expired(self) -> None:
        """Test key is valid when active and not expired."""
        api_key = APIKey(
            tenant_id=uuid4(),
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )

        assert api_key.is_valid is True

    def test_invalid_when_inactive(self) -> None:
        """Test key is invalid when inactive."""
        api_key = APIKey(
            tenant_id=uuid4(),
            is_active=False,
        )

        assert api_key.is_valid is False

    def test_invalid_when_expired(self) -> None:
        """Test key is invalid when expired."""
        api_key = APIKey(
            tenant_id=uuid4(),
            is_active=True,
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )

        assert api_key.is_valid is False

    def test_invalid_when_inactive_and_expired(self) -> None:
        """Test key is invalid when both inactive and expired."""
        api_key = APIKey(
            tenant_id=uuid4(),
            is_active=False,
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )

        assert api_key.is_valid is False


class TestAPIKeyRecordUsage:
    """Tests for record_usage method."""

    def test_record_usage_updates_timestamp(self) -> None:
        """Test record_usage updates last_used_at."""
        api_key = APIKey(tenant_id=uuid4())

        before = datetime.now(UTC)
        api_key.record_usage()
        after = datetime.now(UTC)

        assert api_key.last_used_at is not None
        assert before <= api_key.last_used_at <= after

    def test_record_usage_stores_ip(self) -> None:
        """Test record_usage stores IP address."""
        api_key = APIKey(tenant_id=uuid4())

        api_key.record_usage(ip_address="192.168.1.100")

        assert api_key.last_used_ip == "192.168.1.100"

    def test_record_usage_increments_count(self) -> None:
        """Test record_usage increments usage count."""
        api_key = APIKey(tenant_id=uuid4())

        api_key.record_usage()
        api_key.record_usage()
        api_key.record_usage()

        assert api_key.usage_count == 3

    def test_record_usage_without_ip(self) -> None:
        """Test record_usage without IP address."""
        api_key = APIKey(tenant_id=uuid4())

        api_key.record_usage()

        assert api_key.last_used_ip is None
        assert api_key.usage_count == 1


class TestAPIKeyHasScope:
    """Tests for has_scope method."""

    def test_has_exact_scope(self) -> None:
        """Test exact scope match."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["users:read", "users:write"],
        )

        assert api_key.has_scope("users:read") is True
        assert api_key.has_scope("users:delete") is False

    def test_wildcard_all_scopes(self) -> None:
        """Test wildcard (*) grants all scopes."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["*"],
        )

        assert api_key.has_scope("users:read") is True
        assert api_key.has_scope("roles:write") is True
        assert api_key.has_scope("anything:whatsoever") is True

    def test_resource_wildcard(self) -> None:
        """Test resource wildcard (users:*) grants all actions."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["users:*"],
        )

        assert api_key.has_scope("users:read") is True
        assert api_key.has_scope("users:write") is True
        assert api_key.has_scope("users:delete") is True
        assert api_key.has_scope("roles:read") is False

    def test_no_scope_match(self) -> None:
        """Test when no scope matches."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["roles:read"],
        )

        assert api_key.has_scope("users:read") is False

    def test_empty_scopes(self) -> None:
        """Test with empty scopes list."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=[],
        )

        assert api_key.has_scope("users:read") is False

    def test_single_part_scope(self) -> None:
        """Test scope without colon separator."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["admin"],
        )

        assert api_key.has_scope("admin") is True
        assert api_key.has_scope("user") is False


class TestAPIKeyHasAnyScope:
    """Tests for has_any_scope method."""

    def test_has_any_scope_one_match(self) -> None:
        """Test has_any_scope with one matching scope."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["users:read"],
        )

        result = api_key.has_any_scope(["users:read", "users:write"])

        assert result is True

    def test_has_any_scope_no_match(self) -> None:
        """Test has_any_scope with no matching scopes."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["roles:read"],
        )

        result = api_key.has_any_scope(["users:read", "users:write"])

        assert result is False

    def test_has_any_scope_empty_list(self) -> None:
        """Test has_any_scope with empty list."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["users:read"],
        )

        result = api_key.has_any_scope([])

        assert result is False


class TestAPIKeyHasAllScopes:
    """Tests for has_all_scopes method."""

    def test_has_all_scopes_all_match(self) -> None:
        """Test has_all_scopes when all scopes match."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["users:read", "users:write", "roles:read"],
        )

        result = api_key.has_all_scopes(["users:read", "users:write"])

        assert result is True

    def test_has_all_scopes_partial_match(self) -> None:
        """Test has_all_scopes with partial match."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["users:read"],
        )

        result = api_key.has_all_scopes(["users:read", "users:write"])

        assert result is False

    def test_has_all_scopes_empty_list(self) -> None:
        """Test has_all_scopes with empty list."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["users:read"],
        )

        result = api_key.has_all_scopes([])

        assert result is True

    def test_has_all_scopes_with_wildcard(self) -> None:
        """Test has_all_scopes with wildcard scope."""
        api_key = APIKey(
            tenant_id=uuid4(),
            scopes=["*"],
        )

        result = api_key.has_all_scopes(["users:read", "roles:write", "admin"])

        assert result is True


class TestAPIKeyRevoke:
    """Tests for revoke method."""

    def test_revoke_deactivates_key(self) -> None:
        """Test revoke deactivates the key."""
        api_key = APIKey(
            tenant_id=uuid4(),
            is_active=True,
        )

        api_key.revoke()

        assert api_key.is_active is False

    def test_revoke_makes_key_invalid(self) -> None:
        """Test revoke makes key invalid."""
        api_key = APIKey(
            tenant_id=uuid4(),
            is_active=True,
        )

        assert api_key.is_valid is True

        api_key.revoke()

        assert api_key.is_valid is False

    def test_revoke_already_revoked(self) -> None:
        """Test revoking already revoked key."""
        api_key = APIKey(
            tenant_id=uuid4(),
            is_active=False,
        )

        # Should not raise error
        api_key.revoke()

        assert api_key.is_active is False
