# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for S3 Storage Adapter.

Tests S3 storage operations with mocked boto3 client.
"""

import hashlib
from datetime import datetime, UTC
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.domain.ports.storage import PresignedURL, StorageFile


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 S3 client."""
    return MagicMock()


@pytest.fixture
def s3_adapter(mock_boto3_client):
    """S3 storage adapter with mocked client."""
    with patch("app.infrastructure.storage.s3.HAS_BOTO3", True), \
         patch("app.infrastructure.storage.s3.boto3") as mock_boto3, \
         patch("app.infrastructure.storage.s3.BotoConfig"):
        
        mock_boto3.client.return_value = mock_boto3_client
        
        from app.infrastructure.storage.s3 import S3StorageAdapter
        
        adapter = S3StorageAdapter(
            bucket="test-bucket",
            region="us-east-1",
        )
        adapter._client = mock_boto3_client
        
        return adapter


class TestS3Initialization:
    """Tests for S3 adapter initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True), \
             patch("app.infrastructure.storage.s3.boto3") as mock_boto3, \
             patch("app.infrastructure.storage.s3.BotoConfig"):
            
            from app.infrastructure.storage.s3 import S3StorageAdapter
            
            adapter = S3StorageAdapter(bucket="my-bucket")
            
            assert adapter._bucket == "my-bucket"
            assert adapter.backend_name == "s3"
            mock_boto3.client.assert_called_once()

    def test_init_with_region_and_endpoint(self):
        """Test initialization with custom region and endpoint."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True), \
             patch("app.infrastructure.storage.s3.boto3") as mock_boto3, \
             patch("app.infrastructure.storage.s3.BotoConfig"):
            
            from app.infrastructure.storage.s3 import S3StorageAdapter
            
            S3StorageAdapter(
                bucket="my-bucket",
                region="eu-west-1",
                endpoint_url="https://s3.custom.com",
            )
            
            call_kwargs = mock_boto3.client.call_args[1]
            assert call_kwargs["region_name"] == "eu-west-1"
            assert call_kwargs["endpoint_url"] == "https://s3.custom.com"

    def test_init_with_credentials(self):
        """Test initialization with explicit credentials."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True), \
             patch("app.infrastructure.storage.s3.boto3") as mock_boto3, \
             patch("app.infrastructure.storage.s3.BotoConfig"):
            
            from app.infrastructure.storage.s3 import S3StorageAdapter
            
            S3StorageAdapter(
                bucket="my-bucket",
                access_key_id="AKIAIOSFODNN7EXAMPLE",
                secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            )
            
            call_kwargs = mock_boto3.client.call_args[1]
            assert call_kwargs["aws_access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
            assert call_kwargs["aws_secret_access_key"] == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

    def test_init_without_boto3(self):
        """Test initialization fails without boto3."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", False):
            from app.infrastructure.storage.s3 import S3StorageAdapter
            
            with pytest.raises(ImportError, match="boto3 is required"):
                S3StorageAdapter(bucket="test-bucket")


class TestS3Upload:
    """Tests for upload operations."""

    @pytest.mark.asyncio
    async def test_upload_bytes_success(self, s3_adapter, mock_boto3_client):
        """Test uploading bytes data."""
        data = b"Hello, S3!"
        path = "files/test.txt"
        
        result = await s3_adapter.upload(data, path)
        
        assert isinstance(result, StorageFile)
        assert result.path == path
        assert result.size == len(data)
        assert result.content_type == "text/plain"
        assert result.etag == hashlib.md5(data).hexdigest()
        
        mock_boto3_client.put_object.assert_called_once()
        call_kwargs = mock_boto3_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == path
        assert call_kwargs["Body"] == data

    @pytest.mark.asyncio
    async def test_upload_bytes_with_custom_content_type(self, s3_adapter, mock_boto3_client):
        """Test upload with custom content type."""
        data = b"Custom data"
        path = "uploads/data.bin"
        
        await s3_adapter.upload(
            data,
            path,
            content_type="application/custom",
        )
        
        call_kwargs = mock_boto3_client.put_object.call_args[1]
        assert call_kwargs["ContentType"] == "application/custom"

    @pytest.mark.asyncio
    async def test_upload_bytes_with_metadata(self, s3_adapter, mock_boto3_client):
        """Test upload with custom metadata."""
        data = b"Metadata test"
        metadata = {"user-id": "123", "version": "1.0"}
        
        await s3_adapter.upload(
            data,
            "files/meta.txt",
            metadata=metadata,
        )
        
        call_kwargs = mock_boto3_client.put_object.call_args[1]
        assert call_kwargs["Metadata"] == metadata

    @pytest.mark.asyncio
    async def test_upload_file_object(self, s3_adapter, mock_boto3_client):
        """Test uploading file-like object."""
        file_data = b"File object content"
        file_obj = BytesIO(file_data)
        path = "uploads/file.txt"
        
        # Mock head_object for getting size after upload
        mock_boto3_client.head_object.return_value = {
            "ContentLength": len(file_data),
            "ETag": '"abc123"',
        }
        
        result = await s3_adapter.upload(file_obj, path)
        
        assert result.size == len(file_data)
        assert result.etag == "abc123"
        
        mock_boto3_client.upload_fileobj.assert_called_once()
        call_args = mock_boto3_client.upload_fileobj.call_args[0]
        assert call_args[0] == file_obj
        assert call_args[1] == "test-bucket"
        assert call_args[2] == path


class TestS3Download:
    """Tests for download operations."""

    @pytest.mark.asyncio
    async def test_download_success(self, s3_adapter, mock_boto3_client):
        """Test successful file download."""
        expected_data = b"Downloaded content"
        
        mock_response = {"Body": Mock()}
        mock_response["Body"].read.return_value = expected_data
        mock_boto3_client.get_object.return_value = mock_response
        
        data = await s3_adapter.download("files/download.txt")
        
        assert data == expected_data
        mock_boto3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="files/download.txt"
        )

    @pytest.mark.asyncio
    async def test_download_not_found(self, s3_adapter, mock_boto3_client):
        """Test download of non-existent file."""
        from app.infrastructure.storage.s3 import ClientError
        
        error = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject"
        )
        error.response = {"Error": {"Code": "NoSuchKey"}}
        mock_boto3_client.get_object.side_effect = error
        
        with pytest.raises(FileNotFoundError, match="File not found"):
            await s3_adapter.download("missing.txt")

    @pytest.mark.asyncio
    async def test_download_stream_success(self, s3_adapter, mock_boto3_client):
        """Test streaming download."""
        chunk1 = b"First chunk"
        chunk2 = b"Second chunk"
        
        mock_body = Mock()
        mock_body.read.side_effect = [chunk1, chunk2, b""]  # Empty bytes signals end
        
        mock_response = {"Body": mock_body}
        mock_boto3_client.get_object.return_value = mock_response
        
        chunks = []
        async for chunk in s3_adapter.download_stream("files/large.bin"):
            chunks.append(chunk)
        
        assert chunks == [chunk1, chunk2]

    @pytest.mark.asyncio
    async def test_download_stream_not_found(self, s3_adapter, mock_boto3_client):
        """Test streaming download of non-existent file."""
        from app.infrastructure.storage.s3 import ClientError
        
        error = ClientError(
            {"Error": {"Code": "NoSuchKey"}},
            "GetObject"
        )
        error.response = {"Error": {"Code": "NoSuchKey"}}
        mock_boto3_client.get_object.side_effect = error
        
        with pytest.raises(FileNotFoundError):
            async for _ in s3_adapter.download_stream("missing.bin"):
                pass


class TestS3Delete:
    """Tests for delete operations."""

    @pytest.mark.asyncio
    async def test_delete_success(self, s3_adapter, mock_boto3_client):
        """Test successful file deletion."""
        result = await s3_adapter.delete("files/to_delete.txt")
        
        assert result is True
        mock_boto3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="files/to_delete.txt"
        )

    @pytest.mark.asyncio
    async def test_delete_failure(self, s3_adapter, mock_boto3_client):
        """Test deletion failure."""
        from app.infrastructure.storage.s3 import ClientError
        
        mock_boto3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}},
            "DeleteObject"
        )
        
        result = await s3_adapter.delete("protected.txt")
        
        assert result is False


class TestS3Exists:
    """Tests for file existence checks."""

    @pytest.mark.asyncio
    async def test_exists_true(self, s3_adapter, mock_boto3_client):
        """Test file exists."""
        mock_boto3_client.head_object.return_value = {}
        
        result = await s3_adapter.exists("files/exists.txt")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, s3_adapter, mock_boto3_client):
        """Test file does not exist."""
        from app.infrastructure.storage.s3 import ClientError
        
        error = ClientError(
            {"Error": {"Code": "404"}},
            "HeadObject"
        )
        error.response = {"Error": {"Code": "404"}}
        mock_boto3_client.head_object.side_effect = error
        
        result = await s3_adapter.exists("files/missing.txt")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_other_error(self, s3_adapter, mock_boto3_client):
        """Test exists with non-404 error."""
        from app.infrastructure.storage.s3 import ClientError
        
        mock_boto3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}},
            "HeadObject"
        )
        
        with pytest.raises(Exception):  # Should propagate error
            await s3_adapter.exists("files/test.txt")


class TestS3GetMetadata:
    """Tests for metadata retrieval."""

    @pytest.mark.asyncio
    async def test_get_metadata_success(self, s3_adapter, mock_boto3_client):
        """Test getting file metadata."""
        mock_boto3_client.head_object.return_value = {
            "ContentLength": 1024,
            "ContentType": "image/png",
            "LastModified": datetime(2025, 1, 15, 12, 0, tzinfo=UTC),
            "ETag": '"def456"',
            "Metadata": {"key": "value"},
        }
        
        metadata = await s3_adapter.get_metadata("images/photo.png")
        
        assert metadata is not None
        assert metadata.path == "images/photo.png"
        assert metadata.size == 1024
        assert metadata.content_type == "image/png"
        assert metadata.etag == "def456"
        assert metadata.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_metadata_not_found(self, s3_adapter, mock_boto3_client):
        """Test metadata for non-existent file."""
        from app.infrastructure.storage.s3 import ClientError
        
        error = ClientError(
            {"Error": {"Code": "404"}},
            "HeadObject"
        )
        error.response = {"Error": {"Code": "404"}}
        mock_boto3_client.head_object.side_effect = error
        
        metadata = await s3_adapter.get_metadata("missing.txt")
        
        assert metadata is None


class TestS3ListFiles:
    """Tests for listing files."""

    @pytest.mark.asyncio
    async def test_list_files_success(self, s3_adapter, mock_boto3_client):
        """Test listing files."""
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "files/file1.txt",
                        "Size": 100,
                        "LastModified": datetime(2025, 1, 1, tzinfo=UTC),
                        "ETag": '"abc"',
                    },
                    {
                        "Key": "files/file2.jpg",
                        "Size": 200,
                        "LastModified": datetime(2025, 1, 2, tzinfo=UTC),
                        "ETag": '"def"',
                    },
                ]
            }
        ]
        
        mock_boto3_client.get_paginator.return_value = mock_paginator
        
        files = await s3_adapter.list_files(prefix="files/")
        
        assert len(files) == 2
        assert files[0].path == "files/file1.txt"
        assert files[0].size == 100
        assert files[1].path == "files/file2.jpg"

    @pytest.mark.asyncio
    async def test_list_files_with_limit(self, s3_adapter, mock_boto3_client):
        """Test listing files with limit."""
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": f"file{i}.txt", "Size": i * 10, "LastModified": datetime(2025, 1, 1, tzinfo=UTC)}
                    for i in range(100)
                ]
            }
        ]
        
        mock_boto3_client.get_paginator.return_value = mock_paginator
        
        files = await s3_adapter.list_files(limit=5)
        
        assert len(files) == 5

    @pytest.mark.asyncio
    async def test_list_files_empty(self, s3_adapter, mock_boto3_client):
        """Test listing files with no results."""
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{}]  # No Contents key
        
        mock_boto3_client.get_paginator.return_value = mock_paginator
        
        files = await s3_adapter.list_files()
        
        assert files == []


class TestS3PresignedURLs:
    """Tests for presigned URL generation."""

    @pytest.mark.asyncio
    async def test_presigned_url_download(self, s3_adapter, mock_boto3_client):
        """Test generating presigned URL for download."""
        mock_boto3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/presigned-url"
        
        presigned = await s3_adapter.get_presigned_url(
            "files/download.pdf",
            expires_in=900,
        )
        
        assert isinstance(presigned, PresignedURL)
        assert presigned.url == "https://s3.amazonaws.com/presigned-url"
        assert presigned.method == "GET"
        assert presigned.headers is None
        
        mock_boto3_client.generate_presigned_url.assert_called_once()
        call_args = mock_boto3_client.generate_presigned_url.call_args
        assert call_args[0][0] == "get_object"
        assert call_args[1]["ExpiresIn"] == 900

    @pytest.mark.asyncio
    async def test_presigned_url_upload(self, s3_adapter, mock_boto3_client):
        """Test generating presigned URL for upload."""
        mock_boto3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/presigned-upload"
        
        presigned = await s3_adapter.get_presigned_url(
            "uploads/file.jpg",
            for_upload=True,
            content_type="image/jpeg",
            expires_in=1800,
        )
        
        assert presigned.method == "PUT"
        assert presigned.headers == {"Content-Type": "image/jpeg"}
        
        call_args = mock_boto3_client.generate_presigned_url.call_args
        assert call_args[0][0] == "put_object"
        assert call_args[1]["Params"]["ContentType"] == "image/jpeg"


class TestS3CopyMove:
    """Tests for copy and move operations."""

    @pytest.mark.asyncio
    async def test_copy_success(self, s3_adapter, mock_boto3_client):
        """Test copying a file."""
        # Mock head_object for metadata after copy
        mock_boto3_client.head_object.return_value = {
            "ContentLength": 512,
            "ContentType": "text/plain",
            "LastModified": datetime(2025, 1, 15, tzinfo=UTC),
            "ETag": '"xyz789"',
        }
        
        result = await s3_adapter.copy("source.txt", "dest.txt")
        
        assert isinstance(result, StorageFile)
        assert result.path == "dest.txt"
        assert result.size == 512
        
        mock_boto3_client.copy_object.assert_called_once()
        call_kwargs = mock_boto3_client.copy_object.call_args[1]
        assert call_kwargs["CopySource"] == {"Bucket": "test-bucket", "Key": "source.txt"}
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "dest.txt"

    @pytest.mark.asyncio
    async def test_copy_failure(self, s3_adapter, mock_boto3_client):
        """Test copy failure when metadata unavailable."""
        mock_boto3_client.head_object.return_value = None
        mock_boto3_client.head_object.side_effect = Exception("Metadata retrieval failed")
        
        with pytest.raises(Exception):
            await s3_adapter.copy("source.txt", "dest.txt")

    @pytest.mark.asyncio
    async def test_move_success(self, s3_adapter, mock_boto3_client):
        """Test moving/renaming a file."""
        # Mock metadata after copy
        mock_boto3_client.head_object.return_value = {
            "ContentLength": 256,
            "ContentType": "application/pdf",
            "LastModified": datetime(2025, 1, 15, tzinfo=UTC),
            "ETag": '"move123"',
        }
        
        result = await s3_adapter.move("old_path.pdf", "new_path.pdf")
        
        assert result.path == "new_path.pdf"
        
        # Verify copy was called
        mock_boto3_client.copy_object.assert_called_once()
        
        # Verify delete was called
        mock_boto3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="old_path.pdf"
        )


class TestS3HelperMethods:
    """Tests for helper methods."""

    def test_detect_content_type_known(self, s3_adapter):
        """Test content type detection for known types."""
        assert s3_adapter._detect_content_type("file.txt") == "text/plain"
        assert s3_adapter._detect_content_type("image.jpg") == "image/jpeg"
        assert s3_adapter._detect_content_type("doc.pdf") == "application/pdf"

    def test_detect_content_type_unknown(self, s3_adapter):
        """Test content type detection for unknown types."""
        assert s3_adapter._detect_content_type("file.unknown") == "application/octet-stream"

    def test_build_upload_args_minimal(self, s3_adapter):
        """Test build upload args with no extras."""
        args = s3_adapter._build_upload_args(None, None)
        
        # Should include SSE by default
        assert "ServerSideEncryption" in args
        assert args["ServerSideEncryption"] == "AES256"

    def test_build_upload_args_full(self):
        """Test build upload args with all options."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True), \
             patch("app.infrastructure.storage.s3.boto3") as mock_boto3, \
             patch("app.infrastructure.storage.s3.BotoConfig"):
            
            from app.infrastructure.storage.s3 import S3StorageAdapter
            
            adapter = S3StorageAdapter(
                bucket="test-bucket",
                server_side_encryption="aws:kms",
                default_acl="public-read",
            )
            
            args = adapter._build_upload_args(
                content_type="image/png",
                metadata={"key": "value"},
            )
            
            assert args["ContentType"] == "image/png"
            assert args["Metadata"] == {"key": "value"}
            assert args["ServerSideEncryption"] == "aws:kms"
            assert args["ACL"] == "public-read"
