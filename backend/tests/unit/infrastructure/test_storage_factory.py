# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for storage factory functions.

Tests for get_storage and backend selection logic.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.infrastructure.storage import (
    get_storage,
    StoragePort,
    StorageBackend,
)


class TestGetStorageAutoDetection:
    """Tests for automatic storage backend detection."""

    def test_get_storage_defaults_to_local(self) -> None:
        """Test that get_storage defaults to local when no config."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.S3_BUCKET = None
            mock_settings.STORAGE_BACKEND = "auto"
            
            # Clear cache
            get_storage.cache_clear()
            
            with patch("app.infrastructure.storage._create_local_storage") as mock_local:
                mock_local.return_value = MagicMock(spec=StoragePort)
                
                storage = get_storage()
                
                mock_local.assert_called_once()

    def test_get_storage_auto_selects_s3_when_bucket_set(self) -> None:
        """Test that S3 is selected when S3_BUCKET is configured."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.S3_BUCKET = "my-bucket"
            mock_settings.STORAGE_BACKEND = "auto"
            
            get_storage.cache_clear()
            
            with patch("app.infrastructure.storage._create_s3_storage") as mock_s3:
                mock_s3.return_value = MagicMock(spec=StoragePort)
                
                storage = get_storage()
                
                mock_s3.assert_called_once()

    def test_get_storage_explicit_s3(self) -> None:
        """Test explicit S3 backend selection."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = StorageBackend.S3
            
            get_storage.cache_clear()
            
            with patch("app.infrastructure.storage._create_s3_storage") as mock_s3:
                mock_s3.return_value = MagicMock(spec=StoragePort)
                
                storage = get_storage()
                
                mock_s3.assert_called_once()

    def test_get_storage_explicit_local(self) -> None:
        """Test explicit local backend selection."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = StorageBackend.LOCAL
            
            get_storage.cache_clear()
            
            with patch("app.infrastructure.storage._create_local_storage") as mock_local:
                mock_local.return_value = MagicMock(spec=StoragePort)
                
                storage = get_storage()
                
                mock_local.assert_called_once()

    def test_get_storage_minio_backend(self) -> None:
        """Test MinIO backend selection."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = StorageBackend.MINIO
            
            get_storage.cache_clear()
            
            with patch("app.infrastructure.storage._create_minio_storage") as mock_minio:
                mock_minio.return_value = MagicMock(spec=StoragePort)
                
                storage = get_storage()
                
                mock_minio.assert_called_once()

    def test_get_storage_caches_result(self) -> None:
        """Test that get_storage caches the result."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = "auto"
            mock_settings.S3_BUCKET = None
            
            get_storage.cache_clear()
            
            with patch("app.infrastructure.storage._create_local_storage") as mock_local:
                mock_adapter = MagicMock(spec=StoragePort)
                mock_local.return_value = mock_adapter
                
                storage1 = get_storage()
                storage2 = get_storage()
                
                # Should only create once due to caching
                mock_local.assert_called_once()
                assert storage1 is storage2


class TestCreateLocalStorage:
    """Tests for local storage creation."""

    def test_create_local_storage_default_path(self) -> None:
        """Test creating local storage with default path."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_LOCAL_PATH = None
            
            with patch("app.infrastructure.storage.local.LocalStorageAdapter") as mock_adapter:
                from app.infrastructure.storage import _create_local_storage
                
                _create_local_storage()
                
                mock_adapter.assert_called_once_with(base_path=None)

    def test_create_local_storage_custom_path(self) -> None:
        """Test creating local storage with custom path."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_LOCAL_PATH = "/custom/path"
            
            with patch("app.infrastructure.storage.local.LocalStorageAdapter") as mock_adapter:
                from app.infrastructure.storage import _create_local_storage
                
                _create_local_storage()
                
                mock_adapter.assert_called_once_with(base_path="/custom/path")


class TestCreateS3Storage:
    """Tests for S3 storage creation."""

    def test_create_s3_storage_success(self) -> None:
        """Test creating S3 storage successfully."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.S3_BUCKET = "my-bucket"
            mock_settings.S3_REGION = "us-east-1"
            mock_settings.S3_ENDPOINT_URL = None
            mock_settings.AWS_ACCESS_KEY_ID = "access-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "secret-key"
            
            with patch("app.infrastructure.storage.s3.S3StorageAdapter") as mock_adapter:
                from app.infrastructure.storage import _create_s3_storage
                
                _create_s3_storage()
                
                mock_adapter.assert_called_once()
                call_kwargs = mock_adapter.call_args[1]
                assert call_kwargs["bucket"] == "my-bucket"
                assert call_kwargs["region"] == "us-east-1"

    def test_create_s3_storage_no_bucket_fallback(self) -> None:
        """Test S3 creation falls back to local when no bucket."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.S3_BUCKET = None
            
            with patch("app.infrastructure.storage._create_local_storage") as mock_local:
                mock_local.return_value = MagicMock(spec=StoragePort)
                
                from app.infrastructure.storage import _create_s3_storage
                
                result = _create_s3_storage()
                
                mock_local.assert_called_once()

    def test_create_s3_storage_boto3_not_installed(self) -> None:
        """Test S3 creation raises ImportError when boto3 not available."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.S3_BUCKET = "my-bucket"
            
            # Simulate boto3 not installed by patching HAS_BOTO3
            with patch("app.infrastructure.storage.s3.HAS_BOTO3", False):
                from app.infrastructure.storage import _create_s3_storage
                
                # Should raise ImportError
                with pytest.raises(ImportError, match="boto3 is required"):
                    _create_s3_storage()


class TestCreateMinIOStorage:
    """Tests for MinIO storage creation."""

    def test_create_minio_storage_success(self) -> None:
        """Test creating MinIO storage successfully."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.MINIO_BUCKET = "my-bucket"
            mock_settings.MINIO_ENDPOINT = "http://localhost:9000"
            mock_settings.MINIO_ACCESS_KEY = "minioadmin"
            mock_settings.MINIO_SECRET_KEY = "minioadmin"
            
            with patch("app.infrastructure.storage.s3.S3StorageAdapter") as mock_adapter:
                from app.infrastructure.storage import _create_minio_storage
                
                _create_minio_storage()
                
                mock_adapter.assert_called_once()
                call_kwargs = mock_adapter.call_args[1]
                assert call_kwargs["bucket"] == "my-bucket"
                assert call_kwargs["endpoint_url"] == "http://localhost:9000"
                assert call_kwargs["server_side_encryption"] is None

    def test_create_minio_storage_missing_bucket(self) -> None:
        """Test MinIO creation falls back when bucket missing."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.MINIO_BUCKET = None
            mock_settings.MINIO_ENDPOINT = "http://localhost:9000"
            
            with patch("app.infrastructure.storage._create_local_storage") as mock_local:
                mock_local.return_value = MagicMock(spec=StoragePort)
                
                from app.infrastructure.storage import _create_minio_storage
                
                result = _create_minio_storage()
                
                mock_local.assert_called_once()

    def test_create_minio_storage_missing_endpoint(self) -> None:
        """Test MinIO creation falls back when endpoint missing."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.MINIO_BUCKET = "my-bucket"
            mock_settings.MINIO_ENDPOINT = None
            
            with patch("app.infrastructure.storage._create_local_storage") as mock_local:
                mock_local.return_value = MagicMock(spec=StoragePort)
                
                from app.infrastructure.storage import _create_minio_storage
                
                result = _create_minio_storage()
                
                mock_local.assert_called_once()

    def test_create_minio_storage_boto3_not_installed(self) -> None:
        """Test MinIO creation falls back when boto3 not available."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.MINIO_BUCKET = "my-bucket"
            mock_settings.MINIO_ENDPOINT = "http://localhost:9000"
            
            # Simulate boto3 not installed by patching HAS_BOTO3
            with patch("app.infrastructure.storage.s3.HAS_BOTO3", False):
                from app.infrastructure.storage import _create_minio_storage
                
                # Should raise ImportError
                with pytest.raises(ImportError, match="boto3 is required"):
                    _create_minio_storage()


class TestStorageBackendStrings:
    """Tests for string-based backend selection."""

    def test_s3_string_backend(self) -> None:
        """Test 's3' string selects S3 backend."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = "s3"
            
            get_storage.cache_clear()
            
            with patch("app.infrastructure.storage._create_s3_storage") as mock_s3:
                mock_s3.return_value = MagicMock(spec=StoragePort)
                
                storage = get_storage()
                
                mock_s3.assert_called_once()

    def test_minio_string_backend(self) -> None:
        """Test 'minio' string selects MinIO backend."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = "minio"
            
            get_storage.cache_clear()
            
            with patch("app.infrastructure.storage._create_minio_storage") as mock_minio:
                mock_minio.return_value = MagicMock(spec=StoragePort)
                
                storage = get_storage()
                
                mock_minio.assert_called_once()

    def test_unknown_backend_defaults_to_local(self) -> None:
        """Test unknown backend string defaults to local."""
        with patch("app.infrastructure.storage.settings") as mock_settings:
            mock_settings.STORAGE_BACKEND = "unknown"
            
            get_storage.cache_clear()
            
            with patch("app.infrastructure.storage._create_local_storage") as mock_local:
                mock_local.return_value = MagicMock(spec=StoragePort)
                
                storage = get_storage()
                
                mock_local.assert_called_once()
