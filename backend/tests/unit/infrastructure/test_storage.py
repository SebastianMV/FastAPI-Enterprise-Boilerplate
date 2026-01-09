# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for local storage adapter.

Tests for LocalStorageAdapter file operations.
"""

import tempfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.infrastructure.storage.local import LocalStorageAdapter


class TestLocalStorageAdapter:
    """Tests for LocalStorageAdapter."""

    @pytest.fixture
    def temp_storage_dir(self) -> Iterator[Path]:
        """Create a temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def storage(self, temp_storage_dir: Path) -> LocalStorageAdapter:
        """Create storage adapter with temp directory."""
        return LocalStorageAdapter(
            base_path=temp_storage_dir,
            base_url="/files",
            secret_key="test-secret-key",
        )

    def test_backend_name(self, storage: LocalStorageAdapter) -> None:
        """Test backend name property."""
        assert storage.backend_name == "local"

    def test_creates_base_directory(self) -> None:
        """Test that base directory is created if not exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "new_storage"
            assert not new_dir.exists()
            
            storage = LocalStorageAdapter(base_path=new_dir)
            
            assert new_dir.exists()

    def test_get_full_path_basic(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test getting full path for a file."""
        full_path = storage._get_full_path("uploads/file.txt")
        expected = temp_storage_dir / "uploads" / "file.txt"
        
        assert full_path == expected

    def test_get_full_path_prevents_traversal(
        self, storage: LocalStorageAdapter
    ) -> None:
        """Test that path traversal attacks are prevented."""
        with pytest.raises(ValueError):
            storage._get_full_path("../../../etc/passwd")

    def test_get_full_path_strips_leading_slash(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test that leading slash is stripped."""
        full_path = storage._get_full_path("/uploads/file.txt")
        expected = temp_storage_dir / "uploads" / "file.txt"
        
        assert full_path == expected

    def test_detect_content_type_known_extensions(
        self, storage: LocalStorageAdapter
    ) -> None:
        """Test MIME type detection for known extensions."""
        tests = [
            ("file.pdf", "application/pdf"),
            ("file.txt", "text/plain"),
            ("file.html", "text/html"),
            ("image.png", "image/png"),
            ("image.jpg", "image/jpeg"),
            ("data.json", "application/json"),
        ]
        
        for filename, expected_type in tests:
            result = storage._detect_content_type(filename)
            assert result == expected_type, f"Failed for {filename}"

    def test_detect_content_type_unknown_extension(
        self, storage: LocalStorageAdapter
    ) -> None:
        """Test MIME type detection for unknown extension."""
        result = storage._detect_content_type("file.unknownext")
        assert result == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_upload_creates_directories(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test that upload creates parent directories."""
        data = b"Hello, World!"
        path = "deep/nested/path/file.txt"
        
        file = await storage.upload(data, path)
        
        assert file.path == path
        assert (temp_storage_dir / path).exists()
        assert (temp_storage_dir / path).read_bytes() == data

    @pytest.mark.asyncio
    async def test_upload_returns_storage_file(
        self, storage: LocalStorageAdapter
    ) -> None:
        """Test that upload returns correct StorageFile."""
        data = b"Test content"
        path = "test.txt"
        
        file = await storage.upload(data, path)
        
        assert file.path == path
        assert file.size == len(data)
        assert file.content_type == "text/plain"
        assert file.etag is not None

    @pytest.mark.asyncio
    async def test_download_returns_content(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test downloading file content."""
        # Create a file first
        content = b"File content to download"
        path = "download_test.txt"
        (temp_storage_dir / path).write_bytes(content)
        
        result = await storage.download(path)
        
        assert result == content

    @pytest.mark.asyncio
    async def test_download_nonexistent_file(
        self, storage: LocalStorageAdapter
    ) -> None:
        """Test downloading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            await storage.download("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_delete_file(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test deleting a file."""
        path = "to_delete.txt"
        (temp_storage_dir / path).write_bytes(b"Delete me")
        
        result = await storage.delete(path)
        
        assert result is True
        assert not (temp_storage_dir / path).exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(
        self, storage: LocalStorageAdapter
    ) -> None:
        """Test deleting non-existent file returns False."""
        result = await storage.delete("nonexistent.txt")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test exists returns True for existing file."""
        path = "existing.txt"
        (temp_storage_dir / path).write_bytes(b"I exist")
        
        result = await storage.exists(path)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(
        self, storage: LocalStorageAdapter
    ) -> None:
        """Test exists returns False for non-existing file."""
        result = await storage.exists("nonexistent.txt")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_metadata(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test getting file metadata."""
        content = b"File for info"
        path = "info_test.txt"
        (temp_storage_dir / path).write_bytes(content)
        
        info = await storage.get_metadata(path)
        
        assert info is not None
        assert info.path == path
        assert info.size == len(content)
        assert info.content_type == "text/plain"

    @pytest.mark.asyncio
    async def test_get_metadata_nonexistent(
        self, storage: LocalStorageAdapter
    ) -> None:
        """Test getting metadata for non-existent file."""
        info = await storage.get_metadata("nonexistent.txt")
        assert info is None

    @pytest.mark.asyncio
    async def test_list_files(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test listing files in a directory."""
        # Create some files
        (temp_storage_dir / "dir").mkdir()
        (temp_storage_dir / "dir" / "file1.txt").write_bytes(b"1")
        (temp_storage_dir / "dir" / "file2.txt").write_bytes(b"2")
        (temp_storage_dir / "dir" / "file3.pdf").write_bytes(b"3")
        
        files = await storage.list_files("dir")
        
        assert len(files) == 3
        paths = [f.path for f in files]
        assert "dir/file1.txt" in paths
        assert "dir/file2.txt" in paths
        assert "dir/file3.pdf" in paths

    @pytest.mark.asyncio
    async def test_list_with_prefix(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test listing files with prefix filter."""
        (temp_storage_dir / "reports").mkdir()
        (temp_storage_dir / "reports" / "report_1.pdf").write_bytes(b"1")
        (temp_storage_dir / "reports" / "report_2.pdf").write_bytes(b"2")
        (temp_storage_dir / "other").mkdir()
        (temp_storage_dir / "other" / "other.pdf").write_bytes(b"3")
        
        # list_files takes prefix as first positional argument
        files = await storage.list_files("reports")
        
        # Should only return files in the "reports" directory
        assert len(files) == 2
        paths = [f.path for f in files]
        assert any("report_1.pdf" in p for p in paths)
        assert any("report_2.pdf" in p for p in paths)

    @pytest.mark.asyncio
    async def test_copy_file(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test copying a file."""
        source = "source.txt"
        dest = "dest.txt"
        content = b"Copy me"
        
        (temp_storage_dir / source).write_bytes(content)
        
        file = await storage.copy(source, dest)
        
        assert file is not None
        assert file.path == dest
        assert (temp_storage_dir / dest).read_bytes() == content
        # Source should still exist
        assert (temp_storage_dir / source).exists()

    @pytest.mark.asyncio
    async def test_move_file(
        self, storage: LocalStorageAdapter, temp_storage_dir: Path
    ) -> None:
        """Test moving a file."""
        source = "source_move.txt"
        dest = "dest_move.txt"
        content = b"Move me"
        
        (temp_storage_dir / source).write_bytes(content)
        
        file = await storage.move(source, dest)
        
        assert file is not None
        assert file.path == dest
        assert (temp_storage_dir / dest).read_bytes() == content
        # Source should NOT exist
        assert not (temp_storage_dir / source).exists()


class TestLocalStoragePresignedURLs:
    """Tests for presigned URL functionality."""

    @pytest.fixture
    def storage(self) -> Iterator[LocalStorageAdapter]:
        """Create storage adapter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LocalStorageAdapter(
                base_path=Path(tmpdir),
                base_url="http://localhost:8000/files",
                secret_key="test-secret-key-for-signing",
            )

    @pytest.mark.asyncio
    async def test_generate_presigned_url(
        self, storage: LocalStorageAdapter
    ) -> None:
        """Test generating presigned URL."""
        presigned = await storage.get_presigned_url(
            path="uploads/file.pdf",
            expires_in=3600,
        )
        
        assert presigned is not None
        assert presigned.url.startswith("http://localhost:8000/files")
        assert presigned.expires_at is not None

    @pytest.mark.asyncio
    async def test_presigned_url_contains_path(
        self, storage: LocalStorageAdapter
    ) -> None:
        """Test that presigned URL contains file path."""
        presigned = await storage.get_presigned_url(
            path="my/file.txt",
            expires_in=60,
        )
        
        assert "my/file.txt" in presigned.url or "my%2Ffile.txt" in presigned.url

class TestStorageFactory:
    """Tests for storage factory function."""

    def test_get_storage_returns_local_by_default(self) -> None:
        """Test get_storage returns LocalStorageAdapter when no S3 config."""
        from app.infrastructure.storage import _create_local_storage
        from app.infrastructure.storage.local import LocalStorageAdapter
        
        storage = _create_local_storage()
        
        assert isinstance(storage, LocalStorageAdapter)

    def test_storage_backend_enum_values(self) -> None:
        """Test StorageBackend enum values exist."""
        from app.domain.ports.storage import StorageBackend
        
        assert StorageBackend.LOCAL.value == "local"
        assert StorageBackend.S3.value == "s3"
        assert StorageBackend.MINIO.value == "minio"

    def test_local_storage_backend_name(self) -> None:
        """Test local storage has correct backend name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorageAdapter(base_path=Path(tmpdir))
            
            assert storage.backend_name == "local"


class TestGetStorage:
    """Tests for get_storage factory function."""

    def test_get_storage_auto_local_fallback(self) -> None:
        """Test auto mode falls back to local when S3 not configured."""
        from app.infrastructure.storage import get_storage
        from app.infrastructure.storage.local import LocalStorageAdapter
        
        get_storage.cache_clear()
        
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = "auto"
            mock_settings.S3_BUCKET = None
            
            storage = get_storage()
        
        assert isinstance(storage, LocalStorageAdapter)
        get_storage.cache_clear()

    def test_get_storage_explicit_local(self) -> None:
        """Test explicit local backend selection."""
        from app.infrastructure.storage import get_storage
        from app.infrastructure.storage.local import LocalStorageAdapter
        
        get_storage.cache_clear()
        
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = "local"
            
            storage = get_storage()
        
        assert isinstance(storage, LocalStorageAdapter)
        get_storage.cache_clear()


class TestS3StorageFactory:
    """Tests for S3 storage factory."""

    def test_create_s3_storage_falls_back_without_bucket(self) -> None:
        """Test S3 falls back to local when bucket not configured."""
        from app.infrastructure.storage import _create_s3_storage
        from app.infrastructure.storage.local import LocalStorageAdapter
        
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.S3_BUCKET = None
            
            storage = _create_s3_storage()
        
        assert isinstance(storage, LocalStorageAdapter)


class TestMinioStorageFactory:
    """Tests for MinIO storage factory."""

    def test_create_minio_falls_back_without_config(self) -> None:
        """Test MinIO falls back to local without config."""
        from app.infrastructure.storage import _create_minio_storage
        from app.infrastructure.storage.local import LocalStorageAdapter
        
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.MINIO_BUCKET = None
            mock_settings.MINIO_ENDPOINT = None
            
            storage = _create_minio_storage()
        
        assert isinstance(storage, LocalStorageAdapter)

    def test_create_minio_falls_back_without_bucket(self) -> None:
        """Test MinIO falls back to local without bucket."""
        from app.infrastructure.storage import _create_minio_storage
        from app.infrastructure.storage.local import LocalStorageAdapter
        
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.MINIO_BUCKET = None
            mock_settings.MINIO_ENDPOINT = "http://localhost:9000"
            
            storage = _create_minio_storage()
        
        assert isinstance(storage, LocalStorageAdapter)

    def test_create_minio_falls_back_without_endpoint(self) -> None:
        """Test MinIO falls back to local without endpoint."""
        from app.infrastructure.storage import _create_minio_storage
        from app.infrastructure.storage.local import LocalStorageAdapter
        
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.MINIO_BUCKET = "my-bucket"
            mock_settings.MINIO_ENDPOINT = None
            
            storage = _create_minio_storage()
        
        assert isinstance(storage, LocalStorageAdapter)
