# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Storage port (interface) for file operations.

Defines the abstract interface for file storage operations.
Implementations can use local filesystem, S3, Azure Blob, etc.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import BinaryIO


class StorageBackend(str, Enum):
    """Available storage backend types."""

    LOCAL = "local"
    S3 = "s3"
    MINIO = "minio"


@dataclass
class StorageFile:
    """
    Metadata about a stored file.

    Attributes:
        path: The storage path/key of the file
        size: File size in bytes
        content_type: MIME type of the file
        created_at: When the file was uploaded
        metadata: Additional custom metadata
        etag: Entity tag for caching/versioning
    """

    path: str
    size: int
    content_type: str | None = None
    created_at: datetime | None = None
    metadata: dict[str, str] | None = None
    etag: str | None = None


@dataclass
class PresignedURL:
    """
    A presigned URL for direct upload/download.

    Attributes:
        url: The presigned URL
        method: HTTP method (GET for download, PUT for upload)
        expires_at: When the URL expires
        headers: Required headers for the request
    """

    url: str
    method: str
    expires_at: datetime
    headers: dict[str, str] | None = None


class StoragePort(ABC):
    """
    Abstract interface for file storage operations.

    This is a port in hexagonal architecture. Implementations
    (adapters) provide the actual storage logic for different
    backends like local filesystem, AWS S3, Azure Blob, etc.

    The application code depends only on this interface, making
    it easy to switch storage backends without code changes.

    Usage:
        storage = get_storage()  # Returns configured adapter

        # Upload a file
        file_info = await storage.upload(
            data=file_bytes,
            path="uploads/document.pdf",
            content_type="application/pdf"
        )

        # Get a download URL
        url = await storage.get_presigned_url("uploads/document.pdf")
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Get the name of this storage backend."""
        ...

    @abstractmethod
    async def upload(
        self,
        data: bytes | BinaryIO,
        path: str,
        *,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> StorageFile:
        """
        Upload a file to storage.

        Args:
            data: File content as bytes or file-like object
            path: Destination path/key in storage
            content_type: MIME type (auto-detected if not provided)
            metadata: Custom metadata to store with the file

        Returns:
            StorageFile with metadata about the uploaded file
        """
        ...

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """
        Download a file from storage.

        Args:
            path: Path/key of the file to download

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        ...

    @abstractmethod
    def download_stream(self, path: str) -> AsyncIterator[bytes]:
        """
        Download a file as a stream (for large files).

        Args:
            path: Path/key of the file to download

        Yields:
            Chunks of file content
        """
        ...

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            path: Path/key of the file to delete

        Returns:
            True if deleted, False if file didn't exist
        """
        ...

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if a file exists.

        Args:
            path: Path/key to check

        Returns:
            True if file exists, False otherwise
        """
        ...

    @abstractmethod
    async def get_metadata(self, path: str) -> StorageFile | None:
        """
        Get metadata about a file without downloading it.

        Args:
            path: Path/key of the file

        Returns:
            StorageFile with metadata, or None if not found
        """
        ...

    @abstractmethod
    async def list_files(
        self,
        prefix: str = "",
        *,
        limit: int | None = None,
    ) -> list[StorageFile]:
        """
        List files with a given prefix.

        Args:
            prefix: Path prefix to filter by
            limit: Maximum number of files to return

        Returns:
            List of StorageFile objects
        """
        ...

    @abstractmethod
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

        For download: Client can GET the file directly
        For upload: Client can PUT the file directly

        Args:
            path: Path/key of the file
            expires_in: URL validity in seconds (default 1 hour)
            for_upload: If True, generate upload URL (PUT)
            content_type: Required content type for uploads

        Returns:
            PresignedURL with the signed URL and metadata
        """
        ...

    @abstractmethod
    async def copy(self, source_path: str, dest_path: str) -> StorageFile:
        """
        Copy a file within storage.

        Args:
            source_path: Source file path
            dest_path: Destination file path

        Returns:
            StorageFile metadata for the new file
        """
        ...

    @abstractmethod
    async def move(self, source_path: str, dest_path: str) -> StorageFile:
        """
        Move/rename a file within storage.

        Args:
            source_path: Source file path
            dest_path: Destination file path

        Returns:
            StorageFile metadata for the moved file
        """
        ...
