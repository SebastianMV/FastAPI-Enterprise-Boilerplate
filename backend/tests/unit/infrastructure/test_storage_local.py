# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Comprehensive tests for Local Storage Adapter."""

import shutil
import tempfile
from pathlib import Path

import pytest

from app.infrastructure.storage.local import LocalStorageAdapter


class TestLocalStorageAdapter:
    """Tests for LocalStorageAdapter."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def adapter(self, temp_dir):
        """Create a LocalStorageAdapter instance."""
        return LocalStorageAdapter(
            base_path=temp_dir, base_url="/files", secret_key="test-secret-key"
        )

    def test_init_creates_base_directory(self, temp_dir):
        """Should create base directory if it doesn't exist."""
        new_dir = temp_dir / "new_storage"
        assert not new_dir.exists()

        adapter = LocalStorageAdapter(base_path=new_dir)
        assert new_dir.exists()

    def test_init_with_default_path(self):
        """Should use default path when none provided."""
        adapter = LocalStorageAdapter()
        assert adapter._base_path is not None
        assert adapter._base_path.exists()

    def test_backend_name(self, adapter):
        """Should return correct backend name."""
        assert adapter.backend_name == "local"

    def test_get_full_path(self, adapter, temp_dir):
        """Should construct full path correctly."""
        full_path = adapter._get_full_path("uploads/file.txt")
        expected = temp_dir / "uploads" / "file.txt"
        assert full_path == expected

    def test_get_full_path_prevents_directory_traversal(self, adapter):
        """Should prevent directory traversal attacks."""
        with pytest.raises(ValueError, match="Path traversal"):
            adapter._get_full_path("../../etc/passwd")

    def test_get_full_path_normalizes_leading_slash(self, adapter, temp_dir):
        """Should handle leading slashes."""
        full_path = adapter._get_full_path("/uploads/file.txt")
        expected = temp_dir / "uploads" / "file.txt"
        assert full_path == expected

    def test_detect_content_type_pdf(self, adapter):
        """Should detect PDF content type."""
        content_type = adapter._detect_content_type("document.pdf")
        assert content_type == "application/pdf"

    def test_detect_content_type_image(self, adapter):
        """Should detect image content types."""
        assert adapter._detect_content_type("photo.jpg") in ["image/jpeg", "image/jpg"]
        assert adapter._detect_content_type("photo.png") == "image/png"

    def test_detect_content_type_unknown(self, adapter):
        """Should return default for unknown types."""
        content_type = adapter._detect_content_type("file.unknown")
        assert content_type == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_upload_creates_directories(self, adapter, temp_dir):
        """Should create parent directories when uploading."""
        data = b"test content"
        path = "folder/subfolder/file.txt"

        await adapter.upload(data, path)

        full_path = temp_dir / "folder" / "subfolder" / "file.txt"
        assert full_path.exists()
        assert full_path.read_bytes() == data

    @pytest.mark.asyncio
    async def test_upload_with_content_type(self, adapter, temp_dir):
        """Should upload file with content type."""
        data = b"test content"
        path = "file.txt"

        result = await adapter.upload(data, path, content_type="text/plain")

        assert result.path == path
        assert result.content_type == "text/plain"

    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, adapter, temp_dir):
        """Should upload file with metadata."""
        data = b"test content"
        path = "file.txt"
        metadata = {"user_id": "123", "upload_date": "2026-01-21"}

        result = await adapter.upload(data, path, metadata=metadata)

        assert result.metadata == metadata

    @pytest.mark.asyncio
    async def test_download_existing_file(self, adapter, temp_dir):
        """Should download existing file."""
        content = b"test download content"
        file_path = temp_dir / "test.txt"
        file_path.write_bytes(content)

        result = await adapter.download("test.txt")

        assert result == content

    @pytest.mark.asyncio
    async def test_download_nonexistent_file(self, adapter):
        """Should raise error for nonexistent file."""
        with pytest.raises((FileNotFoundError, OSError)):
            await adapter.download("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_delete_existing_file(self, adapter, temp_dir):
        """Should delete existing file."""
        file_path = temp_dir / "to_delete.txt"
        file_path.write_text("content")

        await adapter.delete("to_delete.txt")

        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, adapter):
        """Should not raise error when deleting nonexistent file."""
        # Should not raise exception
        await adapter.delete("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing(self, adapter, temp_dir):
        """Should return True for existing file."""
        file_path = temp_dir / "exists.txt"
        file_path.write_text("content")

        result = await adapter.exists("exists.txt")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_nonexistent(self, adapter):
        """Should return False for nonexistent file."""
        result = await adapter.exists("nonexistent.txt")
        assert result is False

    # Note: get_info is replaced by get_metadata in this implementation

    @pytest.mark.asyncio
    async def test_list_files_in_directory(self, adapter, temp_dir):
        """Should list files in a directory."""
        # Create test files
        (temp_dir / "uploads").mkdir()
        (temp_dir / "uploads" / "file1.txt").write_text("content1")
        (temp_dir / "uploads" / "file2.txt").write_text("content2")

        # list_files returns a list, not async iterator
        files = await adapter.list_files("uploads/")

        assert len(files) == 2
        paths = [f.path for f in files]
        # Check that files are found (path format may vary)
        assert any("file1.txt" in p for p in paths)
        assert any("file2.txt" in p for p in paths)

    @pytest.mark.asyncio
    async def test_list_files_empty_directory(self, adapter, temp_dir):
        """Should return empty list for empty directory."""
        (temp_dir / "empty").mkdir()

        files = await adapter.list_files("empty/")

        assert len(files) == 0

    @pytest.mark.asyncio
    async def test_get_presigned_url_for_download(self, adapter):
        """Should generate presigned URL for download."""
        url = await adapter.get_presigned_url(
            "test.txt", for_upload=False, expires_in=3600
        )

        assert url.url is not None
        assert url.method == "GET"
        assert url.expires_at is not None

    @pytest.mark.asyncio
    async def test_get_presigned_url_for_upload(self, adapter):
        """Should generate presigned URL for upload."""
        url = await adapter.get_presigned_url(
            "upload.txt", for_upload=True, expires_in=900
        )

        assert url.url is not None
        assert url.method == "PUT"  # Local adapter uses PUT for uploads
        assert url.expires_at is not None

    # Note: stream_upload method doesn't exist - use upload() with BytesIO instead

    @pytest.mark.asyncio
    async def test_download_stream(self, adapter, temp_dir):
        """Should download file via streaming."""
        content = b"streaming download content"
        file_path = temp_dir / "download_stream.txt"
        file_path.write_bytes(content)

        chunks = []
        async for chunk in adapter.download_stream("download_stream.txt"):
            chunks.append(chunk)

        downloaded = b"".join(chunks)
        assert downloaded == content

    # Note: _calculate_size and _verify_signature methods don't exist

    def test_sign_url(self, adapter):
        """Should sign URL with HMAC."""
        from datetime import UTC, datetime

        path = "test.txt"
        expires_at = datetime.fromtimestamp(1234567890, tz=UTC)

        signature = adapter._sign_url(path, expires_at)

        assert isinstance(signature, str)
        assert len(signature) > 0


class TestLocalStorageEdgeCases:
    """Edge case tests for LocalStorageAdapter."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def adapter(self, temp_dir):
        """Create adapter instance."""
        return LocalStorageAdapter(base_path=temp_dir)

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, adapter):
        """Should handle empty file upload."""
        result = await adapter.upload(b"", "empty.txt")
        assert result.size == 0

    @pytest.mark.asyncio
    async def test_upload_large_path(self, adapter):
        """Should handle deep directory structures."""
        long_path = "/".join([f"folder{i}" for i in range(10)]) + "/file.txt"

        result = await adapter.upload(b"content", long_path)
        assert result.path == long_path

    @pytest.mark.asyncio
    async def test_concurrent_uploads(self, adapter):
        """Should handle concurrent uploads."""
        import asyncio

        async def upload_file(i):
            return await adapter.upload(f"content {i}".encode(), f"file{i}.txt")

        results = await asyncio.gather(*[upload_file(i) for i in range(5)])
        assert len(results) == 5
