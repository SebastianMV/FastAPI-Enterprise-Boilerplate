# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Storage domain ports.

Tests for storage file and presigned URL structures.
"""

from datetime import UTC, datetime, timedelta

from app.domain.ports.storage import (
    PresignedURL,
    StorageBackend,
    StorageFile,
)


class TestStorageBackend:
    """Tests for StorageBackend enum."""

    def test_local_backend(self) -> None:
        """Test LOCAL backend value."""
        assert StorageBackend.LOCAL.value == "local"

    def test_s3_backend(self) -> None:
        """Test S3 backend value."""
        assert StorageBackend.S3.value == "s3"

    def test_minio_backend(self) -> None:
        """Test MINIO backend value."""
        assert StorageBackend.MINIO.value == "minio"

    def test_is_string_enum(self) -> None:
        """Test that StorageBackend is string enum."""
        assert isinstance(StorageBackend.LOCAL.value, str)

    def test_all_backends_exist(self) -> None:
        """Test all expected backends are defined."""
        expected = {"local", "s3", "minio"}
        actual = {b.value for b in StorageBackend}
        assert actual == expected


class TestStorageFile:
    """Tests for StorageFile dataclass."""

    def test_create_basic_storage_file(self) -> None:
        """Test creating basic storage file."""
        file = StorageFile(
            path="uploads/images/photo.jpg",
            size=12345,
        )

        assert file.path == "uploads/images/photo.jpg"
        assert file.size == 12345

    def test_default_values(self) -> None:
        """Test default values."""
        file = StorageFile(path="test.txt", size=100)

        assert file.content_type is None
        assert file.created_at is None
        assert file.metadata is None
        assert file.etag is None

    def test_with_content_type(self) -> None:
        """Test file with content type."""
        file = StorageFile(
            path="document.pdf",
            size=50000,
            content_type="application/pdf",
        )

        assert file.content_type == "application/pdf"

    def test_with_created_at(self) -> None:
        """Test file with creation timestamp."""
        created = datetime.now(UTC)
        file = StorageFile(
            path="report.xlsx",
            size=25000,
            created_at=created,
        )

        assert file.created_at == created

    def test_with_metadata(self) -> None:
        """Test file with custom metadata."""
        file = StorageFile(
            path="data.json",
            size=1024,
            metadata={
                "uploaded_by": "user123",
                "department": "engineering",
                "version": "2.0",
            },
        )

        assert file.metadata is not None  # Type narrowing
        assert file.metadata["uploaded_by"] == "user123"
        assert file.metadata["department"] == "engineering"

    def test_with_etag(self) -> None:
        """Test file with etag."""
        file = StorageFile(
            path="config.yaml",
            size=512,
            etag="abc123def456",
        )

        assert file.etag == "abc123def456"

    def test_full_storage_file(self) -> None:
        """Test storage file with all fields."""
        created = datetime.now(UTC)

        file = StorageFile(
            path="images/avatar.png",
            size=150000,
            content_type="image/png",
            created_at=created,
            metadata={"user_id": "user_456"},
            etag="xyz789",
        )

        assert file.path == "images/avatar.png"
        assert file.size == 150000
        assert file.content_type == "image/png"
        assert file.created_at == created
        assert file.metadata == {"user_id": "user_456"}
        assert file.etag == "xyz789"


class TestPresignedURL:
    """Tests for PresignedURL dataclass."""

    def test_create_download_url(self) -> None:
        """Test creating download presigned URL."""
        expires = datetime.now(UTC) + timedelta(hours=1)

        url = PresignedURL(
            url="https://storage.example.com/file.pdf?signature=abc",
            method="GET",
            expires_at=expires,
        )

        assert url.url == "https://storage.example.com/file.pdf?signature=abc"
        assert url.method == "GET"
        assert url.expires_at == expires

    def test_create_upload_url(self) -> None:
        """Test creating upload presigned URL."""
        expires = datetime.now(UTC) + timedelta(minutes=15)

        url = PresignedURL(
            url="https://storage.example.com/upload?token=xyz",
            method="PUT",
            expires_at=expires,
            headers={"Content-Type": "application/octet-stream"},
        )

        assert url.method == "PUT"
        assert url.headers is not None  # Type narrowing
        assert url.headers["Content-Type"] == "application/octet-stream"

    def test_with_multiple_headers(self) -> None:
        """Test presigned URL with multiple headers."""
        expires = datetime.now(UTC) + timedelta(minutes=30)

        url = PresignedURL(
            url="https://s3.amazonaws.com/bucket/key",
            method="PUT",
            expires_at=expires,
            headers={
                "Content-Type": "image/jpeg",
                "x-amz-meta-user": "user123",
                "x-amz-acl": "private",
            },
        )
        assert url.headers is not None
        assert len(url.headers) == 3
        assert url.headers["x-amz-acl"] == "private"
