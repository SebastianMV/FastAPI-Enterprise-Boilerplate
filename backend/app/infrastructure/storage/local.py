# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Local filesystem storage adapter.

This is the default/fallback storage adapter that stores files
on the local filesystem. Perfect for development and simple deployments.
"""

import asyncio
import base64
import hashlib
import hmac
import mimetypes
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote

import aiofiles  # type: ignore[import-untyped]
import aiofiles.os  # type: ignore[import-untyped]

from app.config import settings
from app.domain.ports.storage import (
    PresignedURL,
    StorageFile,
    StoragePort,
)


class LocalStorageAdapter(StoragePort):
    """
    Local filesystem storage adapter.

    Stores files on the local filesystem, perfect for:
    - Development environments
    - Simple single-server deployments
    - Testing without external dependencies

    Features:
    - Automatic directory creation
    - MIME type detection
    - Simulated presigned URLs (for API compatibility)
    - Streaming support for large files

    Usage:
        storage = LocalStorageAdapter(base_path=Path("./storage"))
        await storage.upload(data, "uploads/file.pdf")
    """

    CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming

    def __init__(
        self,
        base_path: Path | str | None = None,
        base_url: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """
        Initialize the local storage adapter.

        Args:
            base_path: Base directory for file storage.
                      Defaults to ./storage in the project root.
            base_url: Base URL for generating file URLs.
                     Defaults to /files (served by FastAPI).
            secret_key: Secret for signing presigned URLs.
                       Defaults to JWT_SECRET_KEY from settings.
        """
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent.parent / "storage"

        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

        self._base_url = base_url or "/files"
        self._secret_key = (
            secret_key
            or hashlib.sha256(
                f"storage-signing:{settings.JWT_SECRET_KEY}".encode()
            ).hexdigest()
        )

    @property
    def backend_name(self) -> str:
        """Get the name of this storage backend."""
        return "local"

    def _get_full_path(self, path: str) -> Path:
        """Get the full filesystem path for a storage path."""
        # Prevent directory traversal attacks
        clean_path = Path(path).as_posix().lstrip("/")
        full_path = self._base_path / clean_path

        # Ensure the path is within base_path
        try:
            full_path.resolve().relative_to(self._base_path.resolve())
        except ValueError:
            raise ValueError("Path traversal detected") from None

        return full_path

    def _detect_content_type(self, path: str) -> str:
        """Detect MIME type from file extension."""
        content_type, _ = mimetypes.guess_type(path)
        return content_type or "application/octet-stream"

    def _compute_etag(self, data: bytes) -> str:
        """Compute ETag (MD5 hash) for file content."""
        return hashlib.md5(data, usedforsecurity=False).hexdigest()

    async def upload(
        self,
        data: bytes | BinaryIO,
        path: str,
        *,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> StorageFile:
        """Upload a file to local storage."""
        full_path = self._get_full_path(path)

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle bytes or file-like object
        if isinstance(data, (bytes, bytearray, memoryview)):
            file_bytes = bytes(data)
        else:
            file_bytes = data.read()

        # Write file
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(file_bytes)

        # Store metadata in a sidecar file if provided
        if metadata:
            meta_path = full_path.with_suffix(full_path.suffix + ".meta")
            import json

            async with aiofiles.open(meta_path, "w") as f:
                await f.write(json.dumps(metadata))

        return StorageFile(
            path=path,
            size=len(file_bytes),
            content_type=content_type or self._detect_content_type(path),
            created_at=datetime.now(UTC),
            metadata=metadata,
            etag=self._compute_etag(file_bytes),
        )

    async def download(self, path: str) -> bytes:
        """Download a file from local storage."""
        full_path = self._get_full_path(path)

        if not await asyncio.to_thread(full_path.exists):
            raise FileNotFoundError("File not found")

        async with aiofiles.open(full_path, "rb") as f:
            data = await f.read()
            return bytes(data)

    async def download_stream(self, path: str) -> AsyncIterator[bytes]:  # type: ignore[override]
        """Download a file as a stream."""
        full_path = self._get_full_path(path)

        if not await asyncio.to_thread(full_path.exists):
            raise FileNotFoundError("File not found")

        async with aiofiles.open(full_path, "rb") as f:
            while chunk := await f.read(self.CHUNK_SIZE):
                yield chunk

    async def delete(self, path: str) -> bool:
        """Delete a file from local storage."""
        full_path = self._get_full_path(path)

        if not await asyncio.to_thread(full_path.exists):
            return False

        await aiofiles.os.remove(full_path)

        # Also remove metadata file if exists
        meta_path = full_path.with_suffix(full_path.suffix + ".meta")
        if await asyncio.to_thread(meta_path.exists):
            await aiofiles.os.remove(meta_path)

        return True

    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        full_path = self._get_full_path(path)
        return await asyncio.to_thread(full_path.exists)

    async def get_metadata(self, path: str) -> StorageFile | None:
        """Get file metadata without downloading."""
        full_path = self._get_full_path(path)

        if not await asyncio.to_thread(full_path.exists):
            return None

        stat = await asyncio.to_thread(full_path.stat)

        # Try to load custom metadata
        metadata = None
        meta_path = full_path.with_suffix(full_path.suffix + ".meta")
        if await asyncio.to_thread(meta_path.exists):
            import json

            async with aiofiles.open(meta_path) as f:
                metadata = json.loads(await f.read())

        return StorageFile(
            path=path,
            size=stat.st_size,
            content_type=self._detect_content_type(path),
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=UTC),
            metadata=metadata,
        )

    async def list_files(
        self,
        prefix: str = "",
        *,
        limit: int | None = None,
    ) -> list[StorageFile]:
        """List files with a given prefix."""
        search_path = self._get_full_path(prefix) if prefix else self._base_path

        files = []
        count = 0

        for root, _, filenames in await asyncio.to_thread(
            lambda: list(os.walk(search_path))
        ):
            for filename in filenames:
                # Skip metadata files
                if filename.endswith(".meta"):
                    continue

                full_path = Path(root) / filename
                relative_path = full_path.relative_to(self._base_path).as_posix()

                stat = await asyncio.to_thread(full_path.stat)
                files.append(
                    StorageFile(
                        path=relative_path,
                        size=stat.st_size,
                        content_type=self._detect_content_type(filename),
                        created_at=datetime.fromtimestamp(stat.st_ctime, tz=UTC),
                    )
                )

                count += 1
                if limit and count >= limit:
                    return files

        return files

    def _sign_url(self, path: str, expires_at: datetime) -> str:
        """Generate a signature for a presigned URL."""
        message = f"{path}:{int(expires_at.timestamp())}"
        signature = hmac.new(
            self._secret_key.encode(),
            message.encode(),
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(signature).decode()

    async def get_presigned_url(
        self,
        path: str,
        *,
        expires_in: int = 3600,
        for_upload: bool = False,
        content_type: str | None = None,
    ) -> PresignedURL:
        """
        Generate a presigned URL for direct access.

        For local storage, this generates a signed URL that can be
        validated by a FastAPI endpoint to serve/accept files.
        """
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        signature = self._sign_url(path, expires_at)

        # Build URL with signature
        encoded_path = quote(path, safe="")
        url = (
            f"{self._base_url}/{encoded_path}"
            f"?expires={int(expires_at.timestamp())}"
            f"&signature={signature}"
        )

        headers = None
        if for_upload and content_type:
            headers = {"Content-Type": content_type}

        return PresignedURL(
            url=url,
            method="PUT" if for_upload else "GET",
            expires_at=expires_at,
            headers=headers,
        )

    async def copy(self, source_path: str, dest_path: str) -> StorageFile:
        """Copy a file within storage."""
        source = self._get_full_path(source_path)
        dest = self._get_full_path(dest_path)

        if not await asyncio.to_thread(source.exists):
            raise FileNotFoundError("Source file not found")

        dest.parent.mkdir(parents=True, exist_ok=True)

        # Read and write (async)
        async with aiofiles.open(source, "rb") as sf:
            content = await sf.read()

        async with aiofiles.open(dest, "wb") as df:
            await df.write(content)

        result = await self.get_metadata(dest_path)
        if result is None:
            raise FileNotFoundError("Failed to copy file")
        return result

    async def move(self, source_path: str, dest_path: str) -> StorageFile:
        """Move/rename a file within storage."""
        result = await self.copy(source_path, dest_path)
        await self.delete(source_path)
        return result
