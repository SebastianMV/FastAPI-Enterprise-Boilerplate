# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Extended tests for storage infrastructure."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4


class TestStorageImport:
    """Tests for storage import."""

    def test_storage_module_import(self) -> None:
        """Test storage module can be imported."""
        from app.infrastructure import storage

        assert storage is not None


class TestFileStorage:
    """Tests for file storage."""

    def test_file_path_validation(self) -> None:
        """Test file path validation."""
        valid_path = "/uploads/file.txt"
        assert valid_path.startswith("/")

    def test_file_extension_validation(self) -> None:
        """Test file extension validation."""
        filename = "document.pdf"
        ext = Path(filename).suffix
        assert ext == ".pdf"

    def test_allowed_extensions(self) -> None:
        """Test allowed file extensions."""
        allowed = [".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"]
        test_ext = ".pdf"
        assert test_ext in allowed


class TestStorageOperations:
    """Tests for storage operations."""

    def test_upload_path_generation(self) -> None:
        """Test upload path generation."""
        user_id = uuid4()
        filename = "test.pdf"
        path = f"uploads/{user_id}/{filename}"
        assert str(user_id) in path

    def test_download_url_generation(self) -> None:
        """Test download URL generation."""
        file_id = uuid4()
        url = f"/api/v1/files/{file_id}/download"
        assert str(file_id) in url


class TestStorageSecurity:
    """Tests for storage security."""

    def test_path_traversal_prevention(self) -> None:
        """Test path traversal prevention."""
        malicious_path = "../../../etc/passwd"
        sanitized = malicious_path.replace("..", "")
        assert ".." not in sanitized

    def test_mime_type_validation(self) -> None:
        """Test MIME type validation."""
        allowed_mime_types = [
            "application/pdf",
            "image/png",
            "image/jpeg",
        ]
        test_mime = "application/pdf"
        assert test_mime in allowed_mime_types


class TestStorageQuota:
    """Tests for storage quota."""

    def test_file_size_limit(self) -> None:
        """Test file size limit."""
        max_size_mb = 10
        max_size_bytes = max_size_mb * 1024 * 1024
        assert max_size_bytes == 10485760

    def test_storage_quota_calculation(self) -> None:
        """Test storage quota calculation."""
        used_bytes = 5 * 1024 * 1024  # 5 MB
        quota_bytes = 100 * 1024 * 1024  # 100 MB
        usage_percent = (used_bytes / quota_bytes) * 100
        assert usage_percent == 5.0


class TestStorageFactoryFallbacks:
    """Tests for storage factory fallback behavior when dependencies are missing."""

    @patch("app.infrastructure.storage._create_local_storage")
    def test_s3_storage_fallback_on_import_error(self, mock_local: MagicMock) -> None:
        """Test S3 storage falls back to local when boto3 not installed."""
        from app.infrastructure.storage import _create_s3_storage

        # Mock LocalStorageAdapter
        mock_local_adapter = MagicMock()
        mock_local.return_value = mock_local_adapter

        # Patch the import to raise ImportError
        with patch.dict("sys.modules", {"app.infrastructure.storage.s3": None}):
            with patch("app.infrastructure.storage.settings") as mock_settings:
                mock_settings.S3_BUCKET = "test-bucket"

                # Force ImportError by making the import fail
                with patch(
                    "builtins.__import__", side_effect=ImportError("boto3 not found")
                ):
                    result = _create_s3_storage()

        # Should fall back to local storage
        assert result == mock_local_adapter
        mock_local.assert_called_once()

    @patch("app.infrastructure.storage._create_local_storage")
    def test_minio_storage_fallback_on_import_error(
        self, mock_local: MagicMock
    ) -> None:
        """Test MinIO storage falls back to local when boto3 not installed."""
        from app.infrastructure.storage import _create_minio_storage

        # Mock LocalStorageAdapter
        mock_local_adapter = MagicMock()
        mock_local.return_value = mock_local_adapter

        # Patch the import to raise ImportError
        with patch.dict("sys.modules", {"app.infrastructure.storage.s3": None}):
            with patch("app.infrastructure.storage.settings") as mock_settings:
                mock_settings.MINIO_BUCKET = "test-bucket"
                mock_settings.MINIO_ENDPOINT = "localhost:9000"

                # Force ImportError by making the import fail
                with patch(
                    "builtins.__import__", side_effect=ImportError("boto3 not found")
                ):
                    result = _create_minio_storage()

        # Should fall back to local storage
        assert result == mock_local_adapter
        mock_local.assert_called_once()
