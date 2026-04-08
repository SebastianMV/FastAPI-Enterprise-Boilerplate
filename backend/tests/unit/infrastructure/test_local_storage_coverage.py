# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Additional coverage tests for Local Storage adapter.

Tests download_stream, presigned URLs, copy/move, metadata.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import aiofiles
import pytest


class TestLocalStorageDownloadStream:
    """Tests for download_stream method."""

    @pytest.mark.asyncio
    async def test_download_stream_yields_chunks(self, tmp_path: Path):
        """Test downloading file as stream yields chunks."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)
        test_content = b"A" * 10000  # 10KB file

        # Upload file
        await storage.upload(data=test_content, path="large.bin")

        # Download as stream
        chunks = []
        async for chunk in storage.download_stream("large.bin"):
            chunks.append(chunk)

        # Verify all chunks received
        result = b"".join(chunks)
        assert result == test_content
        assert len(chunks) >= 1  # Should have at least one chunk

    @pytest.mark.asyncio
    async def test_download_stream_nonexistent_file(self, tmp_path: Path):
        """Test download_stream raises error for nonexistent file."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)

        with pytest.raises(FileNotFoundError, match="File not found"):
            async for _ in storage.download_stream("nonexistent.txt"):
                pass


class TestLocalStoragePresignedURL:
    """Tests for presigned URL generation."""

    @pytest.mark.asyncio
    async def test_get_presigned_url_for_download(self, tmp_path: Path):
        """Test generating presigned URL for download."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path, base_url="/files")

        presigned = await storage.get_presigned_url("test.txt", expires_in=3600)

        assert presigned.method == "GET"
        assert "/test.txt" in presigned.url
        assert "expires=" in presigned.url
        assert "signature=" in presigned.url
        assert presigned.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_get_presigned_url_for_upload(self, tmp_path: Path):
        """Test generating presigned URL for upload."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)

        presigned = await storage.get_presigned_url(
            "upload.jpg",
            for_upload=True,
            content_type="image/jpeg",
        )

        assert presigned.method == "PUT"
        assert presigned.headers is not None
        assert presigned.headers["Content-Type"] == "image/jpeg"


class TestLocalStorageCopyMove:
    """Tests for copy and move operations."""

    @pytest.mark.asyncio
    async def test_copy_file_creates_duplicate(self, tmp_path: Path):
        """Test copying file creates duplicate."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)

        # Upload source
        await storage.upload(data=b"source content", path="source.txt")

        # Copy
        result = await storage.copy("source.txt", "copy.txt")

        # Verify both exist
        assert await storage.exists("source.txt")
        assert await storage.exists("copy.txt")
        assert result.path == "copy.txt"

        # Verify content
        source_content = await storage.download("source.txt")
        copy_content = await storage.download("copy.txt")
        assert source_content == copy_content

    @pytest.mark.asyncio
    async def test_copy_nonexistent_file_raises(self, tmp_path: Path):
        """Test copying nonexistent file raises error."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)

        with pytest.raises(FileNotFoundError, match="Source file not found"):
            await storage.copy("nonexistent.txt", "dest.txt")

    @pytest.mark.asyncio
    async def test_move_file_removes_source(self, tmp_path: Path):
        """Test moving file removes source."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)

        # Upload source
        await storage.upload(data=b"move me", path="source.txt")

        # Move
        result = await storage.move("source.txt", "moved.txt")

        # Verify source removed and dest exists
        assert not await storage.exists("source.txt")
        assert await storage.exists("moved.txt")
        assert result.path == "moved.txt"


class TestLocalStorageMetadata:
    """Tests for metadata operations."""

    @pytest.mark.asyncio
    async def test_get_metadata_with_custom_meta(self, tmp_path: Path):
        """Test retrieving metadata with custom .meta file."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)

        # Upload file
        await storage.upload(data=b"test", path="test.txt")

        # Create custom metadata file
        file_path = tmp_path / "test.txt"
        meta_path = file_path.with_suffix(".txt.meta")
        meta_data = {"custom": "data", "tags": ["test"]}

        async with aiofiles.open(meta_path, "w") as f:
            await f.write(json.dumps(meta_data))

        # Get metadata
        metadata = await storage.get_metadata("test.txt")

        assert metadata is not None
        assert metadata.path == "test.txt"

    @pytest.mark.asyncio
    async def test_get_metadata_nonexistent_returns_none(self, tmp_path: Path):
        """Test get_metadata returns None for nonexistent file."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)

        metadata = await storage.get_metadata("nonexistent.txt")

        assert metadata is None

    @pytest.mark.asyncio
    async def test_delete_removes_metadata_file(self, tmp_path: Path):
        """Test deleting file also removes .meta file."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)

        # Upload file
        await storage.upload(data=b"test", path="test.txt")

        # Create .meta file
        file_path = tmp_path / "test.txt"
        meta_path = file_path.with_suffix(".txt.meta")
        async with aiofiles.open(meta_path, "w") as f:
            await f.write("{}")

        # Delete
        await storage.delete("test.txt")

        # Verify both removed
        assert not file_path.exists()
        assert not meta_path.exists()


class TestLocalStorageListFiles:
    """Tests for list_files method."""

    @pytest.mark.asyncio
    async def test_list_files_skips_meta_files(self, tmp_path: Path):
        """Test listing files skips .meta files."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)

        # Upload files
        await storage.upload(data=b"1", path="file1.txt")
        await storage.upload(data=b"2", path="file2.txt")

        # Create .meta files
        (tmp_path / "file1.txt.meta").write_text("{}")
        (tmp_path / "file2.txt.meta").write_text("{}")

        # List files
        files = await storage.list_files(prefix="")

        # Should only return actual files, not .meta
        assert len(files) == 2
        assert all(not f.path.endswith(".meta") for f in files)

    @pytest.mark.asyncio
    async def test_list_files_with_limit_stops_early(self, tmp_path: Path):
        """Test list_files respects limit."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        storage = LocalStorageAdapter(base_path=tmp_path)

        # Upload 5 files
        for i in range(5):
            await storage.upload(data=f"{i}".encode(), path=f"file{i}.txt")

        # List with limit
        files = await storage.list_files(prefix="", limit=3)

        assert len(files) == 3


class TestLocalStorageInitialization:
    """Tests for initialization edge cases."""

    @pytest.mark.asyncio
    async def test_init_with_none_secret_key_uses_default(self, tmp_path: Path):
        """Test initialization without secret_key uses settings default."""
        from app.infrastructure.storage.local import LocalStorageAdapter

        # Should use settings.JWT_SECRET_KEY
        storage = LocalStorageAdapter(base_path=tmp_path, secret_key=None)

        # Verify it can generate presigned URLs (requires secret key)
        presigned = await storage.get_presigned_url("test.txt")
        assert "signature=" in presigned.url
