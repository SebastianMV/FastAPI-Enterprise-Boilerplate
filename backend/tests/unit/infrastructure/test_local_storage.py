# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for Local Storage adapter."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta, UTC
from io import BytesIO
import tempfile
import shutil

from app.infrastructure.storage.local import LocalStorageAdapter
from app.domain.ports.storage import StorageFile, PresignedURL


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def storage(temp_storage_dir):
    """Create LocalStorageAdapter instance."""
    return LocalStorageAdapter(
        base_path=temp_storage_dir,
        base_url="/files",
        secret_key="test-secret-key",
    )


class TestLocalStorageAdapter:
    """Test LocalStorageAdapter functionality."""
    
    def test_backend_name(self, storage: LocalStorageAdapter):
        """Test backend name property."""
        assert storage.backend_name == "local"
    
    @pytest.mark.asyncio
    async def test_upload_bytes(self, storage: LocalStorageAdapter):
        """Test uploading bytes data."""
        data = b"Hello, World!"
        path = "test/file.txt"
        
        result = await storage.upload(data, path)
        
        assert isinstance(result, StorageFile)
        assert result.path == path
        assert result.size == len(data)
        assert result.content_type == "text/plain"
        assert result.etag is not None
    
    @pytest.mark.asyncio
    async def test_upload_file_object(self, storage: LocalStorageAdapter):
        """Test uploading file-like object."""
        data = BytesIO(b"File content")
        path = "uploads/document.pdf"
        
        result = await storage.upload(data, path, content_type="application/pdf")
        
        assert result.path == path
        assert result.size == 12
        assert result.content_type == "application/pdf"
    
    @pytest.mark.asyncio
    async def test_upload_creates_directories(
        self,
        storage: LocalStorageAdapter,
        temp_storage_dir: Path,
    ):
        """Test that upload creates parent directories."""
        path = "level1/level2/level3/file.txt"
        
        await storage.upload(b"test", path)
        
        full_path = temp_storage_dir / path
        assert full_path.exists()
        assert full_path.parent.exists()
    
    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, storage: LocalStorageAdapter):
        """Test uploading with metadata."""
        metadata = {"user_id": "123", "purpose": "avatar"}
        
        result = await storage.upload(b"image data", "avatars/user.jpg", metadata=metadata)
        
        assert result.metadata == metadata
    
    @pytest.mark.asyncio
    async def test_download(self, storage: LocalStorageAdapter):
        """Test downloading file."""
        data = b"Download me!"
        path = "files/download.txt"
        
        await storage.upload(data, path)
        downloaded = await storage.download(path)
        
        assert downloaded == data
    
    @pytest.mark.asyncio
    async def test_download_nonexistent_file(self, storage: LocalStorageAdapter):
        """Test downloading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            await storage.download("nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_delete(self, storage: LocalStorageAdapter):
        """Test deleting file."""
        path = "temp/delete-me.txt"
        await storage.upload(b"temporary", path)
        
        await storage.delete(path)
        
        with pytest.raises(FileNotFoundError):
            await storage.download(path)
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, storage: LocalStorageAdapter):
        """Test deleting nonexistent file (should not raise)."""
        # Should handle gracefully
        await storage.delete("nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_exists(self, storage: LocalStorageAdapter):
        """Test checking file existence."""
        path = "check/exists.txt"
        
        assert not await storage.exists(path)
        
        await storage.upload(b"exists", path)
        
        assert await storage.exists(path)
    
    @pytest.mark.asyncio
    async def test_list_files_empty(self, storage: LocalStorageAdapter):
        """Test listing files in empty directory."""
        files = await storage.list_files("empty/")
        
        assert files == []
    
    @pytest.mark.asyncio
    async def test_list_files(self, storage: LocalStorageAdapter):
        """Test listing files in directory."""
        # Upload test files
        await storage.upload(b"1", "docs/file1.txt")
        await storage.upload(b"2", "docs/file2.txt")
        await storage.upload(b"3", "docs/subdir/file3.txt")
        
        files = await storage.list_files("docs/")
        
        # Should list files (implementation may vary)
        assert len(files) >= 2
    
    @pytest.mark.asyncio
    async def test_get_metadata(self, storage: LocalStorageAdapter):
        """Test getting file metadata."""
        data = b"Information"
        path = "info/file.txt"
        
        await storage.upload(data, path)
        info = await storage.get_metadata(path)
        
        assert isinstance(info, StorageFile)
        assert info.path == path
        assert info.size == len(data)
    
    @pytest.mark.asyncio
    async def test_get_presigned_url_upload(self, storage: LocalStorageAdapter):
        """Test generating presigned URL for upload."""
        path = "uploads/presigned.txt"
        
        presigned = await storage.get_presigned_url(
            path,
            for_upload=True,
            expires_in=3600,
        )
        
        assert isinstance(presigned, PresignedURL)
        # Path will be URL-encoded in the URL
        assert "uploads" in presigned.url and "presigned.txt" in presigned.url
        assert presigned.expires_at > datetime.now(UTC)
    
    @pytest.mark.asyncio
    async def test_get_presigned_url_download(self, storage: LocalStorageAdapter):
        """Test generating presigned URL for download."""
        path = "downloads/file.pdf"
        await storage.upload(b"PDF content", path)
        
        presigned = await storage.get_presigned_url(
            path,
            for_upload=False,
            expires_in=1800,
        )
        
        assert isinstance(presigned, PresignedURL)
        # Path will be URL-encoded in the URL
        assert "downloads" in presigned.url and "file.pdf" in presigned.url
        # Expires in ~30 minutes
        assert presigned.expires_at <= datetime.now(UTC) + timedelta(seconds=1800 + 10)
    
    @pytest.mark.asyncio
    async def test_presigned_url_contains_signature(self, storage: LocalStorageAdapter):
        """Test that presigned URL contains signature."""
        path = "secure/file.txt"
        
        presigned = await storage.get_presigned_url(path, for_upload=False)
        
        # Should contain signature and expiry parameters
        assert "signature=" in presigned.url
        assert "expires=" in presigned.url
    
    def test_path_traversal_protection(self, storage: LocalStorageAdapter, temp_storage_dir):
        """Test that path traversal attacks are prevented."""
        # Path traversal should be blocked and raise ValueError
        with pytest.raises(ValueError, match="Invalid path"):
            storage._get_full_path("../../etc/passwd")
    
    def test_content_type_detection(self, storage: LocalStorageAdapter):
        """Test MIME type detection."""
        assert storage._detect_content_type("file.txt") == "text/plain"
        assert storage._detect_content_type("image.jpg") == "image/jpeg"
        assert storage._detect_content_type("doc.pdf") == "application/pdf"
        assert storage._detect_content_type("unknown.xyz") == "application/octet-stream"
    
    def test_etag_computation(self, storage: LocalStorageAdapter):
        """Test ETag computation."""
        data1 = b"content"
        data2 = b"different"
        
        etag1 = storage._compute_etag(data1)
        etag2 = storage._compute_etag(data2)
        
        assert etag1 != etag2
        assert len(etag1) == 32  # MD5 hash length
    
    @pytest.mark.asyncio
    async def test_stream_upload(self, storage: LocalStorageAdapter):
        """Test streaming upload for large files."""
        # Simulate large file
        large_data = b"x" * (1024 * 1024)  # 1MB
        path = "large/file.bin"
        
        result = await storage.upload(large_data, path)
        
        assert result.size == len(large_data)
        
        # Verify content
        downloaded = await storage.download(path)
        assert downloaded == large_data
