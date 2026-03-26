# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Storage infrastructure package.

Provides pluggable storage backends with automatic fallback:
- LocalStorageAdapter: Default, works without external dependencies
- S3StorageAdapter: For AWS S3 or S3-compatible services (MinIO)

Usage:
    from app.infrastructure.storage import get_storage

    storage = get_storage()  # Auto-selects based on config
    await storage.upload(data, "path/to/file.pdf")
"""

from functools import lru_cache

from app.config import settings
from app.domain.ports.storage import StorageBackend, StoragePort
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_storage() -> StoragePort:
    """
    Get the configured storage adapter.

    Automatically selects the storage backend based on configuration:
    - If S3_BUCKET is set → S3StorageAdapter
    - Otherwise → LocalStorageAdapter (fallback)

    The result is cached for performance.

    Returns:
        StoragePort implementation based on configuration
    """
    backend = getattr(settings, "STORAGE_BACKEND", "auto")

    # Auto-detect based on available configuration
    if backend == "auto":
        if getattr(settings, "S3_BUCKET", None):
            backend = StorageBackend.S3
        else:
            backend = StorageBackend.LOCAL

    if backend == StorageBackend.S3 or backend == "s3":
        return _create_s3_storage()
    if backend == StorageBackend.MINIO or backend == "minio":
        return _create_minio_storage()
    return _create_local_storage()


def _create_local_storage() -> StoragePort:
    """Create a local filesystem storage adapter."""
    from app.infrastructure.storage.local import LocalStorageAdapter

    base_path = getattr(settings, "STORAGE_LOCAL_PATH", None)

    adapter = LocalStorageAdapter(base_path=base_path)
    logger.info("storage_initialized", adapter="LocalStorageAdapter")

    return adapter


def _create_s3_storage() -> StoragePort:
    """Create an AWS S3 storage adapter."""
    try:
        from app.infrastructure.storage.s3 import S3StorageAdapter
    except ImportError:
        logger.warning(
            "s3_storage_boto3_not_installed",
            fallback="local",
        )
        return _create_local_storage()

    bucket = getattr(settings, "S3_BUCKET", None)
    if not bucket:
        logger.warning(
            "s3_storage_bucket_not_configured",
            fallback="local",
        )
        return _create_local_storage()

    adapter = S3StorageAdapter(
        bucket=bucket,
        region=getattr(settings, "S3_REGION", None),
        endpoint_url=getattr(settings, "S3_ENDPOINT_URL", None),
        access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
    )

    logger.info("storage_initialized", adapter="S3StorageAdapter")

    return adapter


def _create_minio_storage() -> StoragePort:
    """Create a MinIO storage adapter (S3-compatible)."""
    try:
        from app.infrastructure.storage.s3 import S3StorageAdapter
    except ImportError:
        logger.warning(
            "minio_storage_boto3_not_installed",
            fallback="local",
        )
        return _create_local_storage()

    bucket = getattr(settings, "MINIO_BUCKET", None)
    endpoint = getattr(settings, "MINIO_ENDPOINT", None)

    if not bucket or not endpoint:
        logger.warning(
            "minio_storage_not_configured",
            fallback="local",
        )
        return _create_local_storage()

    adapter = S3StorageAdapter(
        bucket=bucket,
        endpoint_url=endpoint,
        access_key_id=getattr(settings, "MINIO_ACCESS_KEY", None),
        secret_access_key=getattr(settings, "MINIO_SECRET_KEY", None),
        server_side_encryption=None,  # MinIO doesn't require SSE
    )

    logger.info("storage_initialized", adapter="S3StorageAdapter", backend="minio")

    return adapter


# Export main interface
__all__ = [
    "get_storage",
    "StoragePort",
    "StorageBackend",
]
