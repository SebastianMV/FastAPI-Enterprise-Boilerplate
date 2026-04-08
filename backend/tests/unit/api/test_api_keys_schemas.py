# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Unit tests for API Keys endpoint schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.api_keys import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyListResponse,
    APIKeyResponse,
)


class TestAPIKeyCreate:
    """Tests for APIKeyCreate schema."""

    def test_api_key_create_minimal(self):
        """Test API key creation with minimal fields."""
        api_key = APIKeyCreate(name="My API Key")
        assert api_key.name == "My API Key"
        assert api_key.scopes == []
        assert api_key.expires_in_days is None

    def test_api_key_create_with_scopes(self):
        """Test API key creation with scopes."""
        api_key = APIKeyCreate(
            name="Read Only Key", scopes=["users:read", "roles:read"]
        )
        assert len(api_key.scopes) == 2
        assert "users:read" in api_key.scopes

    def test_api_key_create_with_expiration(self):
        """Test API key creation with expiration."""
        api_key = APIKeyCreate(name="Temporary Key", expires_in_days=30)
        assert api_key.expires_in_days == 30

    def test_api_key_create_full(self):
        """Test API key creation with all fields."""
        api_key = APIKeyCreate(
            name="Full Config Key",
            scopes=["users:*", "roles:*", "tenants:read"],
            expires_in_days=90,
        )
        assert api_key.name == "Full Config Key"
        assert len(api_key.scopes) == 3
        assert api_key.expires_in_days == 90

    def test_api_key_create_name_required(self):
        """Test that name is required."""
        with pytest.raises(ValidationError):
            APIKeyCreate(scopes=["users:read"])  # type: ignore[call-arg]

    def test_api_key_create_name_min_length(self):
        """Test name minimum length."""
        with pytest.raises(ValidationError):
            APIKeyCreate(name="")

    def test_api_key_create_name_max_length(self):
        """Test name maximum length."""
        with pytest.raises(ValidationError):
            APIKeyCreate(name="x" * 256)

    def test_api_key_create_expires_min(self):
        """Test expiration minimum days."""
        with pytest.raises(ValidationError):
            APIKeyCreate(name="Key", expires_in_days=0)

    def test_api_key_create_expires_max(self):
        """Test expiration maximum days."""
        with pytest.raises(ValidationError):
            APIKeyCreate(name="Key", expires_in_days=366)

    def test_api_key_create_valid_expiration_range(self):
        """Test valid expiration range."""
        # Minimum valid
        key_min = APIKeyCreate(name="Min", expires_in_days=1)
        assert key_min.expires_in_days == 1

        # Maximum valid
        key_max = APIKeyCreate(name="Max", expires_in_days=365)
        assert key_max.expires_in_days == 365


class TestAPIKeyResponse:
    """Tests for APIKeyResponse schema."""

    def test_api_key_response_valid(self):
        """Test valid API key response."""
        now = datetime.now(UTC)
        response = APIKeyResponse(
            id=uuid4(),
            name="Production Key",
            prefix="pk_live_",
            scopes=["users:read"],
            is_active=True,
            expires_at=None,
            last_used_at=None,
            usage_count=0,
            created_at=now,
        )
        assert response.name == "Production Key"
        assert response.is_active is True
        assert response.usage_count == 0

    def test_api_key_response_with_usage(self):
        """Test API key response with usage data."""
        now = datetime.now(UTC)
        response = APIKeyResponse(
            id=uuid4(),
            name="Active Key",
            prefix="pk_test_",
            scopes=["*"],
            is_active=True,
            expires_at=now,
            last_used_at=now,
            usage_count=1500,
            created_at=now,
        )
        assert response.usage_count == 1500
        assert response.last_used_at == now

    def test_api_key_response_revoked(self):
        """Test revoked API key response."""
        now = datetime.now(UTC)
        response = APIKeyResponse(
            id=uuid4(),
            name="Revoked Key",
            prefix="pk_old_",
            scopes=[],
            is_active=False,
            usage_count=100,
            created_at=now,
        )
        assert response.is_active is False


class TestAPIKeyCreatedResponse:
    """Tests for APIKeyCreatedResponse schema."""

    def test_api_key_created_response(self):
        """Test newly created API key response."""
        now = datetime.now(UTC)
        response = APIKeyCreatedResponse(
            id=uuid4(),
            name="New Key",
            prefix="pk_live_",
            key="pk_live_abc123xyz789",
            scopes=["users:read", "roles:read"],
            expires_at=None,
            created_at=now,
        )
        assert response.key == "pk_live_abc123xyz789"
        assert (
            response.warning == "Store this key securely. It will not be shown again."
        )

    def test_api_key_created_response_with_expiration(self):
        """Test created key with expiration."""
        now = datetime.now(UTC)
        response = APIKeyCreatedResponse(
            id=uuid4(),
            name="Temp Key",
            prefix="pk_test_",
            key="pk_test_tempkey123",
            scopes=[],
            expires_at=now,
            created_at=now,
        )
        assert response.expires_at == now

    def test_api_key_created_response_custom_warning(self):
        """Test created key with custom warning."""
        now = datetime.now(UTC)
        response = APIKeyCreatedResponse(
            id=uuid4(),
            name="Key",
            prefix="pk_",
            key="pk_key",
            scopes=[],
            created_at=now,
            warning="Custom warning message",
        )
        assert response.warning == "Custom warning message"


class TestAPIKeyListResponse:
    """Tests for APIKeyListResponse schema."""

    def test_api_key_list_response(self):
        """Test API key list response."""
        now = datetime.now(UTC)
        response = APIKeyListResponse(
            items=[
                APIKeyResponse(
                    id=uuid4(),
                    name="Key 1",
                    prefix="pk_",
                    scopes=[],
                    is_active=True,
                    usage_count=0,
                    created_at=now,
                ),
                APIKeyResponse(
                    id=uuid4(),
                    name="Key 2",
                    prefix="pk_",
                    scopes=["users:read"],
                    is_active=False,
                    usage_count=50,
                    created_at=now,
                ),
            ],
            total=2,
        )
        assert len(response.items) == 2
        assert response.total == 2

    def test_api_key_list_response_empty(self):
        """Test empty API key list."""
        response = APIKeyListResponse(items=[], total=0)
        assert len(response.items) == 0
        assert response.total == 0

    def test_api_key_list_response_mixed_status(self):
        """Test list with mixed active/revoked keys."""
        now = datetime.now(UTC)
        active_key = APIKeyResponse(
            id=uuid4(),
            name="Active",
            prefix="pk_",
            scopes=[],
            is_active=True,
            usage_count=0,
            created_at=now,
        )
        revoked_key = APIKeyResponse(
            id=uuid4(),
            name="Revoked",
            prefix="pk_",
            scopes=[],
            is_active=False,
            usage_count=100,
            created_at=now,
        )
        response = APIKeyListResponse(items=[active_key, revoked_key], total=2)

        active_count = sum(1 for k in response.items if k.is_active)
        revoked_count = sum(1 for k in response.items if not k.is_active)

        assert active_count == 1
        assert revoked_count == 1
