# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
AWS S3 storage adapter.

Production-ready storage adapter for AWS S3, supporting:
- Presigned URLs for direct upload/download
- Streaming for large files
- Server-side encryption
- Custom metadata
"""

import asyncio
import hashlib
import mimetypes
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any, BinaryIO

# boto3 is an optional dependency for S3/MinIO support
# Install with: pip install boto3
# These type: ignore comments are intentional for optional dependency handling
try:
    import boto3  # type: ignore[import-not-found]
    from botocore.config import Config as BotoConfig  # type: ignore[import-not-found]
    from botocore.exceptions import ClientError  # type: ignore[import-not-found]

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    boto3 = None  # type: ignore[assignment]
    BotoConfig = None  # type: ignore[assignment, misc]

    class ClientError(Exception):  # type: ignore[no-redef]
        """Stub for botocore.exceptions.ClientError when boto3 is not installed."""

        response: dict[str, Any] = {}


from app.domain.ports.storage import (
    PresignedURL,
    StorageFile,
    StoragePort,
)


class S3StorageAdapter(StoragePort):
    """
    AWS S3 storage adapter.

    Production-ready adapter for storing files in AWS S3.
    Supports presigned URLs for direct browser uploads/downloads.

    Requirements:
        pip install boto3

    Environment variables:
        AWS_ACCESS_KEY_ID: AWS access key
        AWS_SECRET_ACCESS_KEY: AWS secret key
        AWS_DEFAULT_REGION: AWS region (or use S3_REGION setting)
        S3_BUCKET: Bucket name
        S3_ENDPOINT_URL: Custom endpoint (for MinIO, LocalStack, etc.)

    Usage:
        storage = S3StorageAdapter(
            bucket="my-bucket",
            region="us-east-1",
        )

        # Upload with presigned URL
        url = await storage.get_presigned_url(
            "uploads/file.pdf",
            for_upload=True,
            expires_in=900,
        )
        # Client PUTs directly to this URL
    """

    CHUNK_SIZE = 8 * 1024 * 1024  # 8MB chunks for multipart

    def __init__(
        self,
        bucket: str,
        region: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        *,
        server_side_encryption: str | None = "AES256",
        default_acl: str | None = None,
    ) -> None:
        """
        Initialize the S3 storage adapter.

        Args:
            bucket: S3 bucket name
            region: AWS region (uses AWS_DEFAULT_REGION if not provided)
            endpoint_url: Custom endpoint for S3-compatible services
            access_key_id: AWS access key (uses AWS_ACCESS_KEY_ID if not provided)
            secret_access_key: AWS secret (uses AWS_SECRET_ACCESS_KEY if not provided)
            server_side_encryption: SSE algorithm (AES256, aws:kms, or None)
            default_acl: Default ACL for uploaded objects
        """
        if not HAS_BOTO3:
            raise ImportError(
                "boto3 is required for S3 storage. Install it with: pip install boto3"
            )

        self._bucket = bucket
        self._region = region
        self._endpoint_url = endpoint_url
        self._sse = server_side_encryption
        self._default_acl = default_acl

        # Create S3 client
        config = BotoConfig(  # type: ignore[misc]
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "adaptive"},
        )

        client_kwargs: dict[str, Any] = {
            "config": config,
        }

        if region:
            client_kwargs["region_name"] = region
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if access_key_id:
            client_kwargs["aws_access_key_id"] = access_key_id
        if secret_access_key:
            client_kwargs["aws_secret_access_key"] = secret_access_key

        self._client: Any = boto3.client("s3", **client_kwargs)  # type: ignore[union-attr]

    @property
    def backend_name(self) -> str:
        """Get the name of this storage backend."""
        return "s3"

    def _detect_content_type(self, path: str) -> str:
        """Detect MIME type from file extension."""
        content_type, _ = mimetypes.guess_type(path)
        return content_type or "application/octet-stream"

    def _build_upload_args(
        self,
        content_type: str | None,
        metadata: dict[str, str] | None,
    ) -> dict:
        """Build extra arguments for upload operations."""
        args = {}

        if content_type:
            args["ContentType"] = content_type
        if metadata:
            args["Metadata"] = metadata
        if self._sse:
            args["ServerSideEncryption"] = self._sse
        if self._default_acl:
            args["ACL"] = self._default_acl

        return args

    async def upload(
        self,
        data: bytes | BinaryIO,
        path: str,
        *,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> StorageFile:
        """Upload a file to S3."""
        content_type = content_type or self._detect_content_type(path)
        extra_args = self._build_upload_args(content_type, metadata)
        loop = asyncio.get_running_loop()

        # Handle bytes or file-like object
        if isinstance(data, bytes):
            await loop.run_in_executor(
                None,
                partial(
                    self._client.put_object,
                    Bucket=self._bucket,
                    Key=path,
                    Body=data,
                    **extra_args,
                ),
            )
            size = len(data)
            etag = hashlib.md5(data, usedforsecurity=False).hexdigest()
        else:
            # Use upload_fileobj for file-like objects
            await loop.run_in_executor(
                None,
                partial(
                    self._client.upload_fileobj,
                    data,
                    self._bucket,
                    path,
                    ExtraArgs=extra_args,
                ),
            )
            # Get size from S3
            head = await loop.run_in_executor(
                None,
                partial(self._client.head_object, Bucket=self._bucket, Key=path),
            )
            size = head["ContentLength"]
            etag = head.get("ETag", "").strip('"')

        return StorageFile(
            path=path,
            size=size,
            content_type=content_type,
            created_at=datetime.now(UTC),
            metadata=metadata,
            etag=etag,
        )

    async def download(self, path: str) -> bytes:
        """Download a file from S3."""
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                partial(self._client.get_object, Bucket=self._bucket, Key=path),
            )
            return await loop.run_in_executor(None, response["Body"].read)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError("File not found") from None
            raise

    async def download_stream(self, path: str) -> AsyncIterator[bytes]:
        """Download a file as a stream."""
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                partial(self._client.get_object, Bucket=self._bucket, Key=path),
            )
            body = response["Body"]

            while True:
                chunk = await loop.run_in_executor(None, body.read, self.CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError("File not found") from None
            raise

    async def delete(self, path: str) -> bool:
        """Delete a file from S3."""
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                partial(self._client.delete_object, Bucket=self._bucket, Key=path),
            )
            return True
        except ClientError:
            return False

    async def exists(self, path: str) -> bool:
        """Check if a file exists in S3."""
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                partial(self._client.head_object, Bucket=self._bucket, Key=path),
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    async def get_metadata(self, path: str) -> StorageFile | None:
        """Get file metadata without downloading."""
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                partial(self._client.head_object, Bucket=self._bucket, Key=path),
            )

            return StorageFile(
                path=path,
                size=response["ContentLength"],
                content_type=response.get("ContentType"),
                created_at=response.get("LastModified"),
                metadata=response.get("Metadata"),
                etag=response.get("ETag", "").strip('"'),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            raise

    async def list_files(
        self,
        prefix: str = "",
        *,
        limit: int | None = None,
    ) -> list[StorageFile]:
        """List files with a given prefix."""
        loop = asyncio.get_running_loop()
        paginator = self._client.get_paginator("list_objects_v2")

        files = []
        count = 0

        page_config = {"Bucket": self._bucket}
        if prefix:
            page_config["Prefix"] = prefix

        pages = await loop.run_in_executor(
            None, lambda: list(paginator.paginate(**page_config))
        )
        for page in pages:
            for obj in page.get("Contents", []):
                files.append(
                    StorageFile(
                        path=obj["Key"],
                        size=obj["Size"],
                        content_type=self._detect_content_type(obj["Key"]),
                        created_at=obj["LastModified"],
                        etag=obj.get("ETag", "").strip('"'),
                    )
                )

                count += 1
                if limit and count >= limit:
                    return files

        return files

    async def get_presigned_url(
        self,
        path: str,
        *,
        expires_in: int = 3600,
        for_upload: bool = False,
        content_type: str | None = None,
    ) -> PresignedURL:
        """Generate a presigned URL for direct S3 access."""
        loop = asyncio.get_running_loop()
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        if for_upload:
            params = {
                "Bucket": self._bucket,
                "Key": path,
            }
            if content_type:
                params["ContentType"] = content_type

            url = await loop.run_in_executor(
                None,
                partial(
                    self._client.generate_presigned_url,
                    "put_object",
                    Params=params,
                    ExpiresIn=expires_in,
                ),
            )

            headers = {"Content-Type": content_type} if content_type else None
        else:
            url = await loop.run_in_executor(
                None,
                partial(
                    self._client.generate_presigned_url,
                    "get_object",
                    Params={"Bucket": self._bucket, "Key": path},
                    ExpiresIn=expires_in,
                ),
            )
            headers = None

        return PresignedURL(
            url=url,
            method="PUT" if for_upload else "GET",
            expires_at=expires_at,
            headers=headers,
        )

    async def copy(self, source_path: str, dest_path: str) -> StorageFile:
        """Copy a file within S3."""
        loop = asyncio.get_running_loop()
        copy_source = {"Bucket": self._bucket, "Key": source_path}

        await loop.run_in_executor(
            None,
            partial(
                self._client.copy_object,
                CopySource=copy_source,
                Bucket=self._bucket,
                Key=dest_path,
            ),
        )

        result = await self.get_metadata(dest_path)
        if result is None:
            raise FileNotFoundError("Failed to copy file")
        return result

    async def move(self, source_path: str, dest_path: str) -> StorageFile:
        """Move/rename a file within S3."""
        result = await self.copy(source_path, dest_path)
        await self.delete(source_path)
        return result
