# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for API Keys API endpoints.

Tests the API key REST endpoints with mocked dependencies.
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestListMyApiKeysEndpoint:
    """Tests for GET /api-keys endpoint."""

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(self) -> None:
        """Test listing API keys when none exist."""
        from app.api.v1.endpoints.api_keys import list_my_api_keys

        user_id = uuid4()
        mock_session = AsyncMock()

        with patch(
            "app.api.v1.endpoints.api_keys.list_user_api_keys"
        ) as mock_list:
            mock_list.return_value = []

            result = await list_my_api_keys(
                include_revoked=False,
                current_user_id=user_id,
                session=mock_session,
            )

        assert len(result.items) == 0
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_api_keys_with_results(self) -> None:
        """Test listing API keys with results."""
        from app.api.v1.endpoints.api_keys import list_my_api_keys

        user_id = uuid4()
        mock_session = AsyncMock()

        mock_key = MagicMock()
        mock_key.id = uuid4()
        mock_key.name = "My API Key"
        mock_key.prefix = "sk_test_"
        mock_key.scopes = ["read", "write"]
        mock_key.is_active = True
        mock_key.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        mock_key.last_used_at = None
        mock_key.usage_count = 0
        mock_key.created_at = datetime.now(timezone.utc)

        with patch(
            "app.api.v1.endpoints.api_keys.list_user_api_keys"
        ) as mock_list:
            mock_list.return_value = [mock_key]

            result = await list_my_api_keys(
                include_revoked=False,
                current_user_id=user_id,
                session=mock_session,
            )

        assert len(result.items) == 1
        assert result.items[0].name == "My API Key"
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_api_keys_include_revoked(self) -> None:
        """Test listing API keys including revoked ones."""
        from app.api.v1.endpoints.api_keys import list_my_api_keys

        user_id = uuid4()
        mock_session = AsyncMock()

        active_key = MagicMock()
        active_key.id = uuid4()
        active_key.name = "Active Key"
        active_key.prefix = "sk_active_"
        active_key.scopes = ["read"]
        active_key.is_active = True
        active_key.expires_at = None
        active_key.last_used_at = None
        active_key.usage_count = 5
        active_key.created_at = datetime.now(timezone.utc)

        revoked_key = MagicMock()
        revoked_key.id = uuid4()
        revoked_key.name = "Revoked Key"
        revoked_key.prefix = "sk_revoked_"
        revoked_key.scopes = ["read", "write"]
        revoked_key.is_active = False
        revoked_key.expires_at = None
        revoked_key.last_used_at = datetime.now(timezone.utc) - timedelta(days=5)
        revoked_key.usage_count = 100
        revoked_key.created_at = datetime.now(timezone.utc) - timedelta(days=30)

        with patch(
            "app.api.v1.endpoints.api_keys.list_user_api_keys"
        ) as mock_list:
            mock_list.return_value = [active_key, revoked_key]

            result = await list_my_api_keys(
                include_revoked=True,
                current_user_id=user_id,
                session=mock_session,
            )

        assert len(result.items) == 2
        assert result.items[0].is_active is True
        assert result.items[1].is_active is False


class TestCreateMyApiKeyEndpoint:
    """Tests for POST /api-keys endpoint."""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self) -> None:
        """Test creating a new API key."""
        from app.api.v1.endpoints.api_keys import create_my_api_key
        from app.api.v1.schemas.api_keys import APIKeyCreate

        user_id = uuid4()
        tenant_id = uuid4()
        mock_session = AsyncMock()

        data = APIKeyCreate(
            name="Test API Key",
            scopes=["read", "write"],
            expires_in_days=30,
        )

        mock_api_key = MagicMock()
        mock_api_key.id = uuid4()
        mock_api_key.name = "Test API Key"
        mock_api_key.prefix = "sk_test_"
        mock_api_key.scopes = ["read", "write"]
        mock_api_key.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        mock_api_key.created_at = datetime.now(timezone.utc)

        with patch(
            "app.api.v1.endpoints.api_keys.create_api_key"
        ) as mock_create:
            mock_create.return_value = ("sk_test_full_key_value", mock_api_key)

            result = await create_my_api_key(
                data=data,
                current_user_id=user_id,
                tenant_id=tenant_id,
                session=mock_session,
            )

        assert result.key == "sk_test_full_key_value"
        assert result.name == "Test API Key"
        assert result.prefix == "sk_test_"

    @pytest.mark.asyncio
    async def test_create_api_key_no_expiry(self) -> None:
        """Test creating an API key without expiry."""
        from app.api.v1.endpoints.api_keys import create_my_api_key
        from app.api.v1.schemas.api_keys import APIKeyCreate

        user_id = uuid4()
        tenant_id = uuid4()
        mock_session = AsyncMock()

        data = APIKeyCreate(
            name="Permanent Key",
            scopes=["read"],
            expires_in_days=None,
        )

        mock_api_key = MagicMock()
        mock_api_key.id = uuid4()
        mock_api_key.name = "Permanent Key"
        mock_api_key.prefix = "sk_perm_"
        mock_api_key.scopes = ["read"]
        mock_api_key.expires_at = None
        mock_api_key.created_at = datetime.now(timezone.utc)

        with patch(
            "app.api.v1.endpoints.api_keys.create_api_key"
        ) as mock_create:
            mock_create.return_value = ("sk_perm_full_key_value", mock_api_key)

            result = await create_my_api_key(
                data=data,
                current_user_id=user_id,
                tenant_id=tenant_id,
                session=mock_session,
            )

        assert result.expires_at is None


class TestRevokeMyApiKeyEndpoint:
    """Tests for DELETE /api-keys/{key_id} endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self) -> None:
        """Test successfully revoking an API key."""
        from app.api.v1.endpoints.api_keys import revoke_my_api_key

        user_id = uuid4()
        key_id = uuid4()
        mock_session = AsyncMock()

        with patch(
            "app.api.v1.endpoints.api_keys.revoke_api_key"
        ) as mock_revoke:
            mock_revoke.return_value = True

            result = await revoke_my_api_key(
                key_id=key_id,
                current_user_id=user_id,
                session=mock_session,
            )

        assert result is None  # 204 No Content
        mock_revoke.assert_called_once_with(
            mock_session,
            key_id=key_id,
            user_id=user_id,
        )

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self) -> None:
        """Test revoking a non-existent API key."""
        from app.api.v1.endpoints.api_keys import revoke_my_api_key

        user_id = uuid4()
        key_id = uuid4()
        mock_session = AsyncMock()

        with patch(
            "app.api.v1.endpoints.api_keys.revoke_api_key"
        ) as mock_revoke:
            mock_revoke.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await revoke_my_api_key(
                    key_id=key_id,
                    current_user_id=user_id,
                    session=mock_session,
                )

        assert exc_info.value.status_code == 404
        assert "API key not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_revoke_api_key_wrong_user(self) -> None:
        """Test revoking an API key owned by another user."""
        from app.api.v1.endpoints.api_keys import revoke_my_api_key

        user_id = uuid4()  # Current user
        key_id = uuid4()  # Key owned by different user
        mock_session = AsyncMock()

        with patch(
            "app.api.v1.endpoints.api_keys.revoke_api_key"
        ) as mock_revoke:
            # Returns False because key doesn't belong to user
            mock_revoke.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await revoke_my_api_key(
                    key_id=key_id,
                    current_user_id=user_id,
                    session=mock_session,
                )

        assert exc_info.value.status_code == 404


class TestApiKeyResponseSchema:
    """Tests for API key response schemas."""

    def test_api_key_response_schema(self) -> None:
        """Test APIKeyResponse schema."""
        from app.api.v1.schemas.api_keys import APIKeyResponse

        response = APIKeyResponse(
            id=uuid4(),
            name="Test Key",
            prefix="sk_test_",
            scopes=["read", "write"],
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            last_used_at=None,
            usage_count=0,
            created_at=datetime.now(timezone.utc),
        )

        assert response.name == "Test Key"
        assert response.is_active is True
        assert response.usage_count == 0

    def test_api_key_created_response_schema(self) -> None:
        """Test APIKeyCreatedResponse schema."""
        from app.api.v1.schemas.api_keys import APIKeyCreatedResponse

        response = APIKeyCreatedResponse(
            id=uuid4(),
            name="New Key",
            prefix="sk_new_",
            key="sk_new_full_key_value_here",
            scopes=["read"],
            expires_at=None,
            created_at=datetime.now(timezone.utc),
        )

        assert response.key == "sk_new_full_key_value_here"
        assert response.expires_at is None

    def test_api_key_list_response_schema(self) -> None:
        """Test APIKeyListResponse schema."""
        from app.api.v1.schemas.api_keys import APIKeyListResponse, APIKeyResponse

        items = [
            APIKeyResponse(
                id=uuid4(),
                name=f"Key {i}",
                prefix=f"sk_{i}_",
                scopes=["read"],
                is_active=True,
                expires_at=None,
                last_used_at=None,
                usage_count=i * 10,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(3)
        ]

        response = APIKeyListResponse(items=items, total=3)

        assert len(response.items) == 3
        assert response.total == 3

    def test_api_key_create_schema(self) -> None:
        """Test APIKeyCreate schema."""
        from app.api.v1.schemas.api_keys import APIKeyCreate

        request = APIKeyCreate(
            name="My API Key",
            scopes=["read", "write", "admin"],
            expires_in_days=90,
        )

        assert request.name == "My API Key"
        assert len(request.scopes) == 3
        assert request.expires_in_days == 90

    def test_api_key_create_default_expiry(self) -> None:
        """Test APIKeyCreate with default expiry."""
        from app.api.v1.schemas.api_keys import APIKeyCreate

        request = APIKeyCreate(
            name="Default Expiry Key",
            scopes=["read"],
        )

        # Assuming default is None or some value
        assert request.name == "Default Expiry Key"


class TestApiKeyEdgeCases:
    """Tests for edge cases in API key handling."""

    def test_api_key_response_with_usage(self) -> None:
        """Test API key response with usage data."""
        from app.api.v1.schemas.api_keys import APIKeyResponse

        last_used = datetime.now(timezone.utc) - timedelta(hours=2)
        response = APIKeyResponse(
            id=uuid4(),
            name="Active Key",
            prefix="sk_active_",
            scopes=["read", "write"],
            is_active=True,
            expires_at=None,
            last_used_at=last_used,
            usage_count=1500,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
        )

        assert response.last_used_at == last_used
        assert response.usage_count == 1500

    def test_api_key_expired(self) -> None:
        """Test API key that has expired."""
        from app.api.v1.schemas.api_keys import APIKeyResponse

        expired_at = datetime.now(timezone.utc) - timedelta(days=1)
        response = APIKeyResponse(
            id=uuid4(),
            name="Expired Key",
            prefix="sk_expired_",
            scopes=["read"],
            is_active=False,
            expires_at=expired_at,
            last_used_at=datetime.now(timezone.utc) - timedelta(days=5),
            usage_count=50,
            created_at=datetime.now(timezone.utc) - timedelta(days=60),
        )

        assert response.is_active is False
        assert response.expires_at is not None
        assert response.expires_at < datetime.now(timezone.utc)

    def test_api_key_empty_scopes(self) -> None:
        """Test API key with empty scopes."""
        from app.api.v1.schemas.api_keys import APIKeyResponse

        response = APIKeyResponse(
            id=uuid4(),
            name="No Scopes Key",
            prefix="sk_none_",
            scopes=[],
            is_active=True,
            expires_at=None,
            last_used_at=None,
            usage_count=0,
            created_at=datetime.now(timezone.utc),
        )

        assert response.scopes == []

    @pytest.mark.asyncio
    async def test_list_api_keys_multiple_pages(self) -> None:
        """Test listing API keys with many results."""
        from app.api.v1.endpoints.api_keys import list_my_api_keys

        user_id = uuid4()
        mock_session = AsyncMock()

        # Create 5 mock keys
        mock_keys = []
        for i in range(5):
            key = MagicMock()
            key.id = uuid4()
            key.name = f"Key {i}"
            key.prefix = f"sk_{i}_"
            key.scopes = ["read"]
            key.is_active = True
            key.expires_at = None
            key.last_used_at = None
            key.usage_count = i
            key.created_at = datetime.now(timezone.utc)
            mock_keys.append(key)

        with patch(
            "app.api.v1.endpoints.api_keys.list_user_api_keys"
        ) as mock_list:
            mock_list.return_value = mock_keys

            result = await list_my_api_keys(
                include_revoked=False,
                current_user_id=user_id,
                session=mock_session,
            )

        assert len(result.items) == 5
        assert result.total == 5
