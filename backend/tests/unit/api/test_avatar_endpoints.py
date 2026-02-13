# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Integration tests for avatar upload functionality."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.api.v1.endpoints.users import MAX_AVATAR_SIZE, delete_avatar, upload_avatar


class TestUploadAvatarEndpoint:
    """Tests for avatar upload endpoint."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.avatar_url = None
        user.is_active = True
        user.is_superuser = False
        user.created_at = MagicMock()
        user.updated_at = MagicMock()
        user.last_login = None
        user.mark_updated = MagicMock()
        return user

    @pytest.fixture
    def valid_image_file(self):
        """Create a valid mock image file."""
        # Create a minimal valid JPEG header
        jpeg_header = bytes(
            [
                0xFF,
                0xD8,
                0xFF,
                0xE0,
                0x00,
                0x10,
                0x4A,
                0x46,
                0x49,
                0x46,
                0x00,
                0x01,
                0x01,
                0x00,
                0x00,
                0x01,
                0x00,
                0x01,
                0x00,
                0x00,
                0xFF,
                0xDB,
                0x00,
                0x43,
            ]
        )
        content = jpeg_header + b"\x00" * 100

        file = MagicMock(spec=UploadFile)
        file.filename = "avatar.jpg"
        file.content_type = "image/jpeg"
        file.read = AsyncMock(return_value=content)
        return file

    @pytest.mark.asyncio
    async def test_upload_avatar_success(self, mock_user, valid_image_file):
        """Test successful avatar upload."""
        mock_session = AsyncMock()
        user_id = mock_user.id

        # Mock storage
        mock_storage = MagicMock()
        mock_storage_file = MagicMock()
        mock_storage_file.path = f"/storage/avatars/{user_id}/abc123.jpg"
        mock_storage.upload = AsyncMock(return_value=mock_storage_file)

        # Updated user after save
        updated_user = MagicMock()
        updated_user.id = user_id
        updated_user.email = "test@example.com"
        updated_user.first_name = "Test"
        updated_user.last_name = "User"
        updated_user.avatar_url = mock_storage_file.path
        updated_user.is_active = True
        updated_user.is_superuser = False
        updated_user.created_at = MagicMock()
        updated_user.updated_at = MagicMock()
        updated_user.last_login = None

        with (
            patch(
                "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
            ) as mock_repo_cls,
            patch("app.api.v1.endpoints.users.get_storage", return_value=mock_storage),
        ):
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.return_value = updated_user
            mock_repo_cls.return_value = mock_repo

            result = await upload_avatar(
                current_user_id=user_id,
                tenant_id=None,
                session=mock_session,
                file=valid_image_file,
            )

            # Verify storage was called
            mock_storage.upload.assert_called_once()

            # Verify user was updated
            assert mock_user.avatar_url == mock_storage_file.path
            mock_user.mark_updated.assert_called_once_with(by_user=user_id)
            mock_repo.update.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_upload_avatar_invalid_content_type(self, mock_user):
        """Test avatar upload with invalid content type."""
        from fastapi import HTTPException

        mock_session = AsyncMock()

        file = MagicMock(spec=UploadFile)
        file.filename = "document.pdf"
        file.content_type = "application/pdf"
        file.read = AsyncMock(return_value=b"pdf content")

        with pytest.raises(HTTPException) as exc_info:
            await upload_avatar(
                current_user_id=mock_user.id,
                tenant_id=None,
                session=mock_session,
                file=file,
            )

        assert exc_info.value.status_code == 400
        detail = cast("dict[str, Any]", exc_info.value.detail)
        assert detail["code"] == "INVALID_FILE_TYPE"

    @pytest.mark.asyncio
    async def test_upload_avatar_file_too_large(self, mock_user):
        """Test avatar upload with file too large."""
        from fastapi import HTTPException

        mock_session = AsyncMock()

        # Create file larger than MAX_AVATAR_SIZE with valid JPEG header
        large_content = b"\xff\xd8\xff" + b"\x00" * MAX_AVATAR_SIZE

        file = MagicMock(spec=UploadFile)
        file.filename = "large.jpg"
        file.content_type = "image/jpeg"
        file.read = AsyncMock(return_value=large_content)

        with pytest.raises(HTTPException) as exc_info:
            await upload_avatar(
                current_user_id=mock_user.id,
                tenant_id=None,
                session=mock_session,
                file=file,
            )

        assert exc_info.value.status_code == 400
        detail = cast("dict[str, Any]", exc_info.value.detail)
        assert detail["code"] == "FILE_TOO_LARGE"

    @pytest.mark.asyncio
    async def test_upload_avatar_user_not_found(self, valid_image_file):
        """Test avatar upload when user not found."""
        from fastapi import HTTPException

        mock_session = AsyncMock()
        user_id = uuid4()

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await upload_avatar(
                    current_user_id=user_id,
                    tenant_id=None,
                    session=mock_session,
                    file=valid_image_file,
                )

            assert exc_info.value.status_code == 404
            detail = cast("dict[str, Any]", exc_info.value.detail)
            assert detail["code"] == "USER_NOT_FOUND"


class TestDeleteAvatarEndpoint:
    """Tests for avatar delete endpoint."""

    @pytest.fixture
    def mock_user_with_avatar(self):
        """Create a mock user with avatar."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "test@example.com"
        user.avatar_url = "/storage/avatars/user123/avatar.jpg"
        user.mark_updated = MagicMock()
        return user

    @pytest.mark.asyncio
    async def test_delete_avatar_success(self, mock_user_with_avatar):
        """Test successful avatar deletion."""
        mock_session = AsyncMock()
        user_id = mock_user_with_avatar.id

        mock_storage = MagicMock()
        mock_storage.delete = AsyncMock()

        with (
            patch(
                "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
            ) as mock_repo_cls,
            patch("app.api.v1.endpoints.users.get_storage", return_value=mock_storage),
        ):
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user_with_avatar
            mock_repo.update.return_value = mock_user_with_avatar
            mock_repo_cls.return_value = mock_repo

            result = await delete_avatar(
                current_user_id=user_id,
                tenant_id=None,
                session=mock_session,
            )

            assert result.message == "Avatar deleted successfully"
            assert mock_user_with_avatar.avatar_url is None

    @pytest.mark.asyncio
    async def test_delete_avatar_no_avatar(self):
        """Test delete when user has no avatar."""
        from fastapi import HTTPException

        mock_session = AsyncMock()
        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.avatar_url = None

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await delete_avatar(
                    current_user_id=user_id,
                    tenant_id=None,
                    session=mock_session,
                )

            assert exc_info.value.status_code == 400
            detail = cast("dict[str, Any]", exc_info.value.detail)
            assert detail["code"] == "NO_AVATAR"

    @pytest.mark.asyncio
    async def test_delete_avatar_user_not_found(self):
        """Test delete avatar when user not found."""
        from fastapi import HTTPException

        mock_session = AsyncMock()
        user_id = uuid4()

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await delete_avatar(
                    current_user_id=user_id,
                    tenant_id=None,
                    session=mock_session,
                )

            assert exc_info.value.status_code == 404
            detail = cast("dict[str, Any]", exc_info.value.detail)
            assert detail["code"] == "USER_NOT_FOUND"
