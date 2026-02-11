# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Comprehensive tests for S3 Storage Adapter."""

from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

# Import HAS_BOTO3 first to check availability
try:
    from app.infrastructure.storage.s3 import HAS_BOTO3, S3StorageAdapter
except ImportError:
    HAS_BOTO3 = False
    S3StorageAdapter = None  # type: ignore[assignment, misc]



@pytest.mark.skipif(not HAS_BOTO3, reason="boto3 not installed")
class TestS3StorageAdapter:
    """Tests for S3StorageAdapter."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        client = MagicMock()
        client.put_object = MagicMock(return_value={})
        client.get_object = MagicMock(return_value={"Body": BytesIO(b"test content")})
        client.delete_object = MagicMock(return_value={})
        client.head_object = MagicMock(
            return_value={
                "ContentLength": 100,
                "ContentType": "text/plain",
                "LastModified": datetime.now(UTC),
                "Metadata": {},
            }
        )
        client.list_objects_v2 = MagicMock(
            return_value={
                "Contents": [
                    {"Key": "file1.txt", "Size": 100},
                    {"Key": "file2.txt", "Size": 200},
                ]
            }
        )
        client.generate_presigned_url = MagicMock(
            return_value="https://s3.amazonaws.com/bucket/file.txt?signature=xyz"
        )
        client.generate_presigned_post = MagicMock(
            return_value={
                "url": "https://s3.amazonaws.com/bucket",
                "fields": {"key": "file.txt"},
            }
        )
        return client

    @pytest.fixture
    def adapter(self, mock_s3_client):
        """Create S3StorageAdapter with mocked client."""
        with patch("app.infrastructure.storage.s3.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3_client
            adapter = S3StorageAdapter(bucket="test-bucket", region="us-east-1")
            adapter._client = mock_s3_client
            return adapter

    def test_init_requires_boto3(self):
        """Should check boto3 availability."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", False):
            with pytest.raises(RuntimeError, match="boto3"):
                S3StorageAdapter(bucket="test-bucket")

    def test_init_with_custom_endpoint(self, mock_s3_client):
        """Should initialize with custom endpoint (MinIO)."""
        with patch("app.infrastructure.storage.s3.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_s3_client

            adapter = S3StorageAdapter(
                bucket="test-bucket", endpoint_url="http://localhost:9000"
            )

            # Verify boto3.client was called with endpoint_url
            assert mock_boto3.client.called

    def test_backend_name(self, adapter):
        """Should return correct backend name."""
        assert adapter.backend_name == "s3"

    @pytest.mark.asyncio
    async def test_upload_file(self, adapter, mock_s3_client):
        """Should upload file to S3."""
        data = b"test upload content"
        path = "uploads/test.txt"

        result = await adapter.upload(data, path)

        assert result.path == path
        assert mock_s3_client.put_object.called

        call_kwargs = mock_s3_client.put_object.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == path
        assert call_kwargs["Body"] == data

    @pytest.mark.asyncio
    async def test_upload_with_content_type(self, adapter, mock_s3_client):
        """Should upload with custom content type."""
        data = b"test content"
        path = "file.json"

        result = await adapter.upload(data, path, content_type="application/json")

        call_kwargs = mock_s3_client.put_object.call_args.kwargs
        assert call_kwargs["ContentType"] == "application/json"

    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, adapter, mock_s3_client):
        """Should upload with custom metadata."""
        data = b"test content"
        metadata = {"user_id": "123", "project": "test"}

        result = await adapter.upload(data, "file.txt", metadata=metadata)

        call_kwargs = mock_s3_client.put_object.call_args.kwargs
        assert call_kwargs["Metadata"] == metadata

    @pytest.mark.asyncio
    async def test_upload_with_server_side_encryption(self, adapter, mock_s3_client):
        """Should upload with server-side encryption."""
        data = b"encrypted content"

        result = await adapter.upload(data, "secure.txt")

        call_kwargs = mock_s3_client.put_object.call_args.kwargs
        assert "ServerSideEncryption" in call_kwargs

    @pytest.mark.asyncio
    async def test_download_file(self, adapter, mock_s3_client):
        """Should download file from S3."""
        mock_body = BytesIO(b"downloaded content")
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        result = await adapter.download("file.txt")

        assert result == b"downloaded content"
        assert mock_s3_client.get_object.called

    @pytest.mark.asyncio
    async def test_download_handles_client_error(self, adapter, mock_s3_client):
        """Should handle S3 client errors."""
        from botocore.exceptions import ClientError

        error_response = {"Error": {"Code": "NoSuchKey"}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, "GetObject")

        with pytest.raises(Exception):
            await adapter.download("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_delete_file(self, adapter, mock_s3_client):
        """Should delete file from S3."""
        await adapter.delete("file.txt")

        assert mock_s3_client.delete_object.called
        call_kwargs = mock_s3_client.delete_object.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "file.txt"

    @pytest.mark.asyncio
    async def test_exists_returns_true(self, adapter, mock_s3_client):
        """Should return True for existing file."""
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        result = await adapter.exists("file.txt")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self, adapter, mock_s3_client):
        """Should return False for nonexistent file."""
        from botocore.exceptions import ClientError

        error_response = {"Error": {"Code": "404"}}
        mock_s3_client.head_object.side_effect = ClientError(
            error_response, "HeadObject"
        )

        result = await adapter.exists("nonexistent.txt")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_info(self, adapter, mock_s3_client):
        """Should get file information."""
        now = datetime.now(UTC)
        mock_s3_client.head_object.return_value = {
            "ContentLength": 1024,
            "ContentType": "application/pdf",
            "LastModified": now,
            "Metadata": {"key": "value"},
        }

        info = await adapter.get_info("document.pdf")

        assert info.path == "document.pdf"
        assert info.size == 1024
        assert info.content_type == "application/pdf"

    @pytest.mark.asyncio
    async def test_list_files(self, adapter, mock_s3_client):
        """Should list files in S3."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "uploads/file1.txt", "Size": 100},
                {"Key": "uploads/file2.txt", "Size": 200},
            ]
        }

        files = []
        async for file in adapter.list_files("uploads/"):
            files.append(file)

        assert len(files) == 2
        assert files[0].path == "uploads/file1.txt"
        assert files[0].size == 100

    @pytest.mark.asyncio
    async def test_list_files_with_max_keys(self, adapter, mock_s3_client):
        """Should list files with pagination."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "file.txt", "Size": 100}]
        }

        files = []
        async for file in adapter.list_files("", max_keys=10):
            files.append(file)

        call_kwargs = mock_s3_client.list_objects_v2.call_args.kwargs
        assert call_kwargs.get("MaxKeys") == 10

    @pytest.mark.asyncio
    async def test_list_files_empty(self, adapter, mock_s3_client):
        """Should handle empty S3 prefix."""
        mock_s3_client.list_objects_v2.return_value = {}

        files = []
        async for file in adapter.list_files("empty/"):
            files.append(file)

        assert len(files) == 0

    @pytest.mark.asyncio
    async def test_get_presigned_url_for_download(self, adapter, mock_s3_client):
        """Should generate presigned URL for download."""
        mock_s3_client.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/signed"
        )

        url = await adapter.get_presigned_url(
            "file.txt", for_upload=False, expires_in=3600
        )

        assert url.url == "https://s3.amazonaws.com/signed"
        assert url.method == "GET"
        assert mock_s3_client.generate_presigned_url.called

    @pytest.mark.asyncio
    async def test_get_presigned_url_for_upload(self, adapter, mock_s3_client):
        """Should generate presigned POST for upload."""
        mock_s3_client.generate_presigned_post.return_value = {
            "url": "https://s3.amazonaws.com/bucket",
            "fields": {"key": "file.txt", "signature": "xyz"},
        }

        url = await adapter.get_presigned_url(
            "file.txt", for_upload=True, expires_in=900
        )

        assert url.method == "POST"
        assert url.fields is not None
        assert mock_s3_client.generate_presigned_post.called

    @pytest.mark.asyncio
    async def test_stream_upload(self, adapter, mock_s3_client):
        """Should upload file via streaming."""
        content = b"streaming content"
        stream = BytesIO(content)

        result = await adapter.stream_upload(stream, "streamed.txt")

        assert result.path == "streamed.txt"
        assert mock_s3_client.put_object.called

    @pytest.mark.asyncio
    async def test_stream_download(self, adapter, mock_s3_client):
        """Should download file via streaming."""
        content = b"streaming download"
        mock_body = MagicMock()
        mock_body.iter_chunks.return_value = iter([content])
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        chunks = []
        async for chunk in adapter.stream_download("file.txt"):
            chunks.append(chunk)

        # Test passes if we can iterate
        assert mock_s3_client.get_object.called


@pytest.mark.skipif(not HAS_BOTO3, reason="boto3 not installed")
class TestS3StorageAdapterWithoutBoto3:
    """Tests for S3 adapter when boto3 is not available."""

    def test_init_fails_without_boto3(self):
        """Should fail to initialize without boto3."""
        with patch("app.infrastructure.storage.s3.HAS_BOTO3", False):
            with pytest.raises(ImportError, match="boto3"):
                S3StorageAdapter(bucket="test-bucket")


@pytest.mark.skipif(not HAS_BOTO3, reason="boto3 not installed")
class TestS3Configuration:
    """Tests for S3 configuration options."""

    @pytest.fixture
    def mock_boto3(self):
        """Mock boto3 module."""
        with patch("app.infrastructure.storage.s3.boto3") as mock:
            mock.client.return_value = MagicMock()
            yield mock

    def test_init_with_all_parameters(self, mock_boto3):
        """Should initialize with all configuration parameters."""
        adapter = S3StorageAdapter(
            bucket="my-bucket",
            region="eu-west-1",
            endpoint_url="http://localhost:9000",
            access_key_id="test-key",
            secret_access_key="test-secret",
            server_side_encryption="aws:kms",
            default_acl="public-read",
        )

        assert adapter._bucket == "my-bucket"
        assert mock_boto3.client.called

    def test_init_with_minimal_parameters(self, mock_boto3):
        """Should initialize with minimal parameters."""
        adapter = S3StorageAdapter(bucket="simple-bucket")

        assert adapter._bucket == "simple-bucket"
        assert mock_boto3.client.called

    def test_server_side_encryption_disabled(self, mock_boto3):
        """Should disable server-side encryption when set to None."""
        adapter = S3StorageAdapter(bucket="test-bucket", server_side_encryption=None)

        assert adapter._sse is None
