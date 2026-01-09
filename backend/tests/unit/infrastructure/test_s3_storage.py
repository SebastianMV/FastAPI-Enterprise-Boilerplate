# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for S3 storage adapter."""

import pytest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, UTC
from io import BytesIO
from typing import Any


# Create a base exception class that will be used as ClientError
class MockClientError(Exception):
    """Mock for botocore.exceptions.ClientError."""
    def __init__(self, error_response: dict[str, Any], operation_name: str):
        self.response = error_response
        self.operation_name = operation_name
        super().__init__(f"An error occurred ({operation_name})")


# Patch ClientError in the s3 module to use our mock
@pytest.fixture(autouse=True)
def mock_client_error():
    """Automatically patch ClientError for all tests in this module."""
    with patch("app.infrastructure.storage.s3.ClientError", MockClientError):
        yield


class TestS3StorageAdapterInit:
    """Tests for S3StorageAdapter initialization."""
    
    def test_init_without_boto3_raises_import_error(self):
        """Test that init without boto3 installed raises ImportError."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", False):
            from app.infrastructure.storage.s3 import S3StorageAdapter
            
            with pytest.raises(ImportError) as exc_info:
                S3StorageAdapter(bucket="test-bucket")
            
            assert "boto3 is required" in str(exc_info.value)
    
    @patch("app.infrastructure.storage.s3.HAS_BOTO3", True)
    @patch("app.infrastructure.storage.s3.boto3")
    @patch("app.infrastructure.storage.s3.BotoConfig")
    def test_init_with_minimal_params(self, mock_config, mock_boto3):
        """Test initialization with minimal parameters."""
        from app.infrastructure.storage.s3 import S3StorageAdapter
        
        mock_boto3.client.return_value = MagicMock()
        
        adapter = S3StorageAdapter(bucket="test-bucket")
        
        assert adapter._bucket == "test-bucket"
        assert adapter._region is None
        assert adapter._endpoint_url is None
        assert adapter._sse == "AES256"  # Default
        mock_boto3.client.assert_called_once()
    
    @patch("app.infrastructure.storage.s3.HAS_BOTO3", True)
    @patch("app.infrastructure.storage.s3.boto3")
    @patch("app.infrastructure.storage.s3.BotoConfig")
    def test_init_with_full_params(self, mock_config, mock_boto3):
        """Test initialization with all parameters."""
        from app.infrastructure.storage.s3 import S3StorageAdapter
        
        mock_boto3.client.return_value = MagicMock()
        
        adapter = S3StorageAdapter(
            bucket="my-bucket",
            region="us-east-1",
            endpoint_url="http://localhost:9000",
            access_key_id="AKIATEST",
            secret_access_key="secret123",
            server_side_encryption="aws:kms",
            default_acl="private",
        )
        
        assert adapter._bucket == "my-bucket"
        assert adapter._region == "us-east-1"
        assert adapter._endpoint_url == "http://localhost:9000"
        assert adapter._sse == "aws:kms"
        assert adapter._default_acl == "private"
    
    @patch("app.infrastructure.storage.s3.HAS_BOTO3", True)
    @patch("app.infrastructure.storage.s3.boto3")
    @patch("app.infrastructure.storage.s3.BotoConfig")
    def test_backend_name(self, mock_config, mock_boto3):
        """Test backend_name property returns 's3'."""
        from app.infrastructure.storage.s3 import S3StorageAdapter
        
        mock_boto3.client.return_value = MagicMock()
        
        adapter = S3StorageAdapter(bucket="test-bucket")
        assert adapter.backend_name == "s3"


class TestS3StorageAdapterHelpers:
    """Tests for S3 adapter helper methods."""
    
    @pytest.fixture
    def adapter(self):
        """Create an adapter with mocked boto3."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True):
            with patch("app.infrastructure.storage.s3.boto3") as mock_boto3:
                with patch("app.infrastructure.storage.s3.BotoConfig"):
                    mock_boto3.client.return_value = MagicMock()
                    from app.infrastructure.storage.s3 import S3StorageAdapter
                    return S3StorageAdapter(bucket="test-bucket")
    
    def test_detect_content_type_pdf(self, adapter):
        """Test content type detection for PDF."""
        content_type = adapter._detect_content_type("document.pdf")
        assert content_type == "application/pdf"
    
    def test_detect_content_type_png(self, adapter):
        """Test content type detection for PNG."""
        content_type = adapter._detect_content_type("image.png")
        assert content_type == "image/png"
    
    def test_detect_content_type_json(self, adapter):
        """Test content type detection for JSON."""
        content_type = adapter._detect_content_type("data.json")
        assert content_type == "application/json"
    
    def test_detect_content_type_unknown(self, adapter):
        """Test content type detection for unknown extension."""
        content_type = adapter._detect_content_type("file.xyz123")
        assert content_type == "application/octet-stream"
    
    def test_build_upload_args_minimal(self, adapter):
        """Test building upload args with minimal params."""
        args = adapter._build_upload_args(None, None)
        
        # Should include SSE by default
        assert "ServerSideEncryption" in args
        assert args["ServerSideEncryption"] == "AES256"
    
    def test_build_upload_args_full(self, adapter):
        """Test building upload args with all params."""
        args = adapter._build_upload_args(
            content_type="application/json",
            metadata={"custom": "value"}
        )
        
        assert args["ContentType"] == "application/json"
        assert args["Metadata"] == {"custom": "value"}
        assert args["ServerSideEncryption"] == "AES256"


class TestS3StorageAdapterUpload:
    """Tests for upload operations."""
    
    @pytest.fixture
    def adapter(self):
        """Create an adapter with mocked boto3."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True):
            with patch("app.infrastructure.storage.s3.boto3") as mock_boto3:
                with patch("app.infrastructure.storage.s3.BotoConfig"):
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client
                    from app.infrastructure.storage.s3 import S3StorageAdapter
                    adapter = S3StorageAdapter(bucket="test-bucket")
                    return adapter
    
    @pytest.mark.asyncio
    async def test_upload_bytes(self, adapter):
        """Test uploading bytes data."""
        data = b"Hello, World!"
        
        result = await adapter.upload(data, "test/file.txt")
        
        adapter._client.put_object.assert_called_once()
        call_kwargs = adapter._client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "test/file.txt"
        assert call_kwargs["Body"] == data
        
        assert result.path == "test/file.txt"
        assert result.size == len(data)
    
    @pytest.mark.asyncio
    async def test_upload_file_object(self, adapter):
        """Test uploading file-like object."""
        data = BytesIO(b"File content")
        
        adapter._client.head_object.return_value = {
            "ContentLength": 12,
            "ETag": '"abc123"'
        }
        
        result = await adapter.upload(data, "test/file.bin")
        
        adapter._client.upload_fileobj.assert_called_once()
        assert result.path == "test/file.bin"
        assert result.size == 12
    
    @pytest.mark.asyncio
    async def test_upload_with_custom_content_type(self, adapter):
        """Test upload with custom content type."""
        data = b"JSON data"
        
        result = await adapter.upload(
            data, 
            "data.txt", 
            content_type="application/json"
        )
        
        call_kwargs = adapter._client.put_object.call_args[1]
        assert call_kwargs["ContentType"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, adapter):
        """Test upload with custom metadata."""
        data = b"Data with metadata"
        metadata = {"author": "test", "version": "1.0"}
        
        await adapter.upload(data, "file.txt", metadata=metadata)
        
        call_kwargs = adapter._client.put_object.call_args[1]
        assert call_kwargs["Metadata"] == metadata


class TestS3StorageAdapterDownload:
    """Tests for download operations."""
    
    @pytest.fixture
    def adapter(self):
        """Create an adapter with mocked boto3."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True):
            with patch("app.infrastructure.storage.s3.boto3") as mock_boto3:
                with patch("app.infrastructure.storage.s3.BotoConfig"):
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client
                    from app.infrastructure.storage.s3 import S3StorageAdapter
                    return S3StorageAdapter(bucket="test-bucket")
    
    @pytest.mark.asyncio
    async def test_download_success(self, adapter):
        """Test successful file download."""
        expected_data = b"Downloaded content"
        mock_body = MagicMock()
        mock_body.read.return_value = expected_data
        
        adapter._client.get_object.return_value = {"Body": mock_body}
        
        result = await adapter.download("test/file.txt")
        
        assert result == expected_data
        adapter._client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test/file.txt"
        )
    
    @pytest.mark.asyncio
    async def test_download_not_found(self, adapter):
        """Test download of non-existent file raises FileNotFoundError."""
        error_response = {"Error": {"Code": "NoSuchKey"}}
        adapter._client.get_object.side_effect = MockClientError(error_response, "GetObject")
        
        with pytest.raises(FileNotFoundError) as exc_info:
            await adapter.download("nonexistent.txt")
        
        assert "File not found" in str(exc_info.value)


class TestS3StorageAdapterDelete:
    """Tests for delete operations."""
    
    @pytest.fixture
    def adapter(self):
        """Create an adapter with mocked boto3."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True):
            with patch("app.infrastructure.storage.s3.boto3") as mock_boto3:
                with patch("app.infrastructure.storage.s3.BotoConfig"):
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client
                    from app.infrastructure.storage.s3 import S3StorageAdapter
                    return S3StorageAdapter(bucket="test-bucket")
    
    @pytest.mark.asyncio
    async def test_delete_success(self, adapter):
        """Test successful file deletion."""
        result = await adapter.delete("test/file.txt")
        
        assert result is True
        adapter._client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test/file.txt"
        )
    
    @pytest.mark.asyncio
    async def test_delete_failure(self, adapter):
        """Test delete failure returns False."""
        adapter._client.delete_object.side_effect = MockClientError({}, "DeleteObject")
        
        result = await adapter.delete("test/file.txt")
        
        assert result is False


class TestS3StorageAdapterExists:
    """Tests for exists check."""
    
    @pytest.fixture
    def adapter(self):
        """Create an adapter with mocked boto3."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True):
            with patch("app.infrastructure.storage.s3.boto3") as mock_boto3:
                with patch("app.infrastructure.storage.s3.BotoConfig"):
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client
                    from app.infrastructure.storage.s3 import S3StorageAdapter
                    return S3StorageAdapter(bucket="test-bucket")
    
    @pytest.mark.asyncio
    async def test_exists_true(self, adapter):
        """Test exists returns True for existing file."""
        adapter._client.head_object.return_value = {"ContentLength": 100}
        
        result = await adapter.exists("test/file.txt")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_false(self, adapter):
        """Test exists returns False for non-existent file."""
        error_response = {"Error": {"Code": "404"}}
        adapter._client.head_object.side_effect = MockClientError(error_response, "HeadObject")
        
        result = await adapter.exists("nonexistent.txt")
        
        assert result is False


class TestS3StorageAdapterPresignedUrl:
    """Tests for presigned URL generation."""
    
    @pytest.fixture
    def adapter(self):
        """Create an adapter with mocked boto3."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True):
            with patch("app.infrastructure.storage.s3.boto3") as mock_boto3:
                with patch("app.infrastructure.storage.s3.BotoConfig"):
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client
                    from app.infrastructure.storage.s3 import S3StorageAdapter
                    return S3StorageAdapter(bucket="test-bucket")
    
    @pytest.mark.asyncio
    async def test_presigned_url_for_download(self, adapter):
        """Test generating presigned URL for download."""
        adapter._client.generate_presigned_url.return_value = "https://s3.example.com/signed-url"
        
        result = await adapter.get_presigned_url("test/file.txt")
        
        assert result.url == "https://s3.example.com/signed-url"
        assert result.method == "GET"
        assert result.expires_at is not None
        
        adapter._client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "test/file.txt"},
            ExpiresIn=3600
        )
    
    @pytest.mark.asyncio
    async def test_presigned_url_for_upload(self, adapter):
        """Test generating presigned URL for upload."""
        adapter._client.generate_presigned_url.return_value = "https://s3.example.com/upload-url"
        
        result = await adapter.get_presigned_url(
            "uploads/new-file.pdf",
            for_upload=True,
            content_type="application/pdf"
        )
        
        assert result.url == "https://s3.example.com/upload-url"
        assert result.method == "PUT"
        assert result.headers == {"Content-Type": "application/pdf"}
    
    @pytest.mark.asyncio
    async def test_presigned_url_custom_expiry(self, adapter):
        """Test presigned URL with custom expiry."""
        adapter._client.generate_presigned_url.return_value = "https://s3.example.com/url"
        
        result = await adapter.get_presigned_url("file.txt", expires_in=900)
        
        adapter._client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "file.txt"},
            ExpiresIn=900
        )


class TestS3StorageAdapterCopyMove:
    """Tests for copy and move operations."""
    
    @pytest.fixture
    def adapter(self):
        """Create an adapter with mocked boto3."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", True):
            with patch("app.infrastructure.storage.s3.boto3") as mock_boto3:
                with patch("app.infrastructure.storage.s3.BotoConfig"):
                    mock_client = MagicMock()
                    mock_boto3.client.return_value = mock_client
                    from app.infrastructure.storage.s3 import S3StorageAdapter
                    return S3StorageAdapter(bucket="test-bucket")
    
    @pytest.mark.asyncio
    async def test_copy_success(self, adapter):
        """Test successful file copy."""
        adapter._client.head_object.return_value = {
            "ContentLength": 100,
            "ContentType": "text/plain",
            "LastModified": datetime.now(UTC),
            "ETag": '"abc123"'
        }
        
        result = await adapter.copy("source/file.txt", "dest/file.txt")
        
        adapter._client.copy_object.assert_called_once()
        assert result.path == "dest/file.txt"
    
    @pytest.mark.asyncio
    async def test_move_success(self, adapter):
        """Test successful file move."""
        adapter._client.head_object.return_value = {
            "ContentLength": 100,
            "ContentType": "text/plain",
            "LastModified": datetime.now(UTC),
            "ETag": '"abc123"'
        }
        
        result = await adapter.move("old/file.txt", "new/file.txt")
        
        # Should copy then delete
        adapter._client.copy_object.assert_called_once()
        adapter._client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="old/file.txt"
        )
        assert result.path == "new/file.txt"
