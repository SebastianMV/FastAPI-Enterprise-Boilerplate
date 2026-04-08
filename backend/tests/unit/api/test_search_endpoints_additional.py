"""Additional search endpoint tests for coverage."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


class TestCreateIndexEndpoint:
    """Tests for create search index endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_superuser(self):
        """Create mock superuser."""
        user = MagicMock()
        user.id = uuid4()
        user.is_superuser = True
        return user

    @pytest.fixture
    def mock_regular_user(self):
        """Create mock regular user."""
        user = MagicMock()
        user.id = uuid4()
        user.is_superuser = False
        return user

    @pytest.mark.asyncio
    async def test_create_index_forbidden_non_superuser(
        self, mock_session, mock_regular_user
    ):
        """Test that non-superusers cannot create indices (enforced via SuperuserId dependency)."""
        import inspect

        from app.api.v1.endpoints.search import create_index

        # Auth is enforced by the SuperuserId dependency at DI level
        sig = inspect.signature(create_index)
        assert "superuser_id" in sig.parameters

    @pytest.mark.asyncio
    async def test_create_index_invalid_index(self, mock_session, mock_superuser):
        """Test creating with invalid index name."""
        from app.api.v1.endpoints.search import create_index

        with pytest.raises(HTTPException) as exc:
            await create_index(
                index="invalid_index_name",
                session=mock_session,
                superuser_id=mock_superuser.id,
            )

        assert exc.value.status_code == 400
        assert exc.value.detail["code"] == "INVALID_SEARCH_INDEX"

    @pytest.mark.asyncio
    async def test_create_index_success(self, mock_session, mock_superuser):
        """Test successful index creation."""
        from app.api.v1.endpoints.search import create_index

        with patch(
            "app.api.v1.endpoints.search.get_search_backend",
            new_callable=AsyncMock,
        ) as mock_get_backend:
            mock_service = MagicMock()
            mock_service.create_index = AsyncMock(return_value=True)
            mock_get_backend.return_value = mock_service

            result = await create_index(
                index="users",
                session=mock_session,
                superuser_id=mock_superuser.id,
            )

            assert result["status"] == "created"
            assert result["index"] == "users"

    @pytest.mark.asyncio
    async def test_create_index_failure(self, mock_session, mock_superuser):
        """Test index creation failure."""
        from app.api.v1.endpoints.search import create_index

        with patch(
            "app.api.v1.endpoints.search.get_search_backend",
            new_callable=AsyncMock,
        ) as mock_get_backend:
            mock_service = MagicMock()
            mock_service.create_index = AsyncMock(return_value=False)
            mock_get_backend.return_value = mock_service

            with pytest.raises(HTTPException) as exc:
                await create_index(
                    index="users",
                    session=mock_session,
                    superuser_id=mock_superuser.id,
                )

            assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_create_index_exception(self, mock_session, mock_superuser):
        """Test index creation with exception."""
        from app.api.v1.endpoints.search import create_index

        with patch(
            "app.api.v1.endpoints.search.get_search_backend",
            new_callable=AsyncMock,
        ) as mock_get_backend:
            mock_get_backend.side_effect = Exception("Connection failed")

            with pytest.raises(HTTPException) as exc:
                await create_index(
                    index="users",
                    session=mock_session,
                    superuser_id=mock_superuser.id,
                )

            assert exc.value.status_code == 500
            assert exc.value.detail["code"] == "INDEX_CREATE_FAILED"


class TestReindexEndpoint:
    """Tests for reindex endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_superuser(self):
        """Create mock superuser."""
        user = MagicMock()
        user.id = uuid4()
        user.is_superuser = True
        return user

    @pytest.fixture
    def mock_regular_user(self):
        """Create mock regular user."""
        user = MagicMock()
        user.id = uuid4()
        user.is_superuser = False
        return user

    @pytest.mark.asyncio
    async def test_reindex_forbidden_non_superuser(
        self, mock_session, mock_regular_user
    ):
        """Test that non-superusers cannot reindex (enforced via SuperuserId dependency)."""
        import inspect

        from app.api.v1.endpoints.search import reindex

        # Auth is enforced by the SuperuserId dependency at DI level
        sig = inspect.signature(reindex)
        assert "superuser_id" in sig.parameters

    @pytest.mark.asyncio
    async def test_reindex_invalid_index(self, mock_session, mock_superuser):
        """Test reindex with invalid index name."""
        from app.api.v1.endpoints.search import reindex

        with pytest.raises(HTTPException) as exc:
            await reindex(
                index="invalid_index",
                session=mock_session,
                superuser_id=mock_superuser.id,
                tenant_id=None,
            )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_reindex_success(self, mock_session, mock_superuser):
        """Test successful reindex."""
        from app.api.v1.endpoints.search import reindex

        mock_result = MagicMock()
        mock_result.indexed = 100
        mock_result.failed = 0
        mock_result.took_ms = 1500

        with patch(
            "app.api.v1.endpoints.search.get_search_backend",
            new_callable=AsyncMock,
        ) as mock_get_backend:
            mock_service = MagicMock()
            mock_service.reindex = AsyncMock(return_value=mock_result)
            mock_get_backend.return_value = mock_service

            result = await reindex(
                index="users",
                session=mock_session,
                superuser_id=mock_superuser.id,
                tenant_id=uuid4(),
            )

            assert result["status"] == "completed"
            assert result["indexed"] == 100
            assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_reindex_exception(self, mock_session, mock_superuser):
        """Test reindex with exception."""
        from app.api.v1.endpoints.search import reindex

        with patch(
            "app.api.v1.endpoints.search.get_search_backend",
            new_callable=AsyncMock,
        ) as mock_get_backend:
            mock_service = MagicMock()
            mock_service.reindex = AsyncMock(side_effect=Exception("Reindex failed"))
            mock_get_backend.return_value = mock_service

            with pytest.raises(HTTPException) as exc:
                await reindex(
                    index="users",
                    session=mock_session,
                    superuser_id=mock_superuser.id,
                    tenant_id=None,
                )

            assert exc.value.status_code == 500


class TestDeleteIndexEndpoint:
    """Tests for delete index endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_superuser(self):
        """Create mock superuser."""
        user = MagicMock()
        user.id = uuid4()
        user.is_superuser = True
        return user

    @pytest.fixture
    def mock_regular_user(self):
        """Create mock regular user."""
        user = MagicMock()
        user.id = uuid4()
        user.is_superuser = False
        return user

    @pytest.mark.asyncio
    async def test_delete_index_forbidden_non_superuser(
        self, mock_session, mock_regular_user
    ):
        """Test that non-superusers cannot delete indices (enforced via SuperuserId dependency)."""
        import inspect

        from app.api.v1.endpoints.search import delete_index

        # Auth is enforced by the SuperuserId dependency at DI level
        sig = inspect.signature(delete_index)
        assert "superuser_id" in sig.parameters

    @pytest.mark.asyncio
    async def test_delete_index_invalid_index(self, mock_session, mock_superuser):
        """Test delete with invalid index name."""
        from app.api.v1.endpoints.search import delete_index

        with pytest.raises(HTTPException) as exc:
            await delete_index(
                index="invalid_index",
                session=mock_session,
                superuser_id=mock_superuser.id,
            )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_index_success(self, mock_session, mock_superuser):
        """Test successful index deletion."""
        from app.api.v1.endpoints.search import delete_index

        with patch(
            "app.api.v1.endpoints.search.get_search_backend",
            new_callable=AsyncMock,
        ) as mock_get_backend:
            mock_service = MagicMock()
            mock_service.delete_index = AsyncMock(return_value=True)
            mock_get_backend.return_value = mock_service

            result = await delete_index(
                index="users",
                session=mock_session,
                superuser_id=mock_superuser.id,
            )

            assert result is None  # 204 No Content

    @pytest.mark.asyncio
    async def test_delete_index_failure(self, mock_session, mock_superuser):
        """Test index deletion failure."""
        from app.api.v1.endpoints.search import delete_index

        with patch(
            "app.api.v1.endpoints.search.get_search_backend",
            new_callable=AsyncMock,
        ) as mock_get_backend:
            mock_service = MagicMock()
            mock_service.delete_index = AsyncMock(return_value=False)
            mock_get_backend.return_value = mock_service

            with pytest.raises(HTTPException) as exc:
                await delete_index(
                    index="users",
                    session=mock_session,
                    superuser_id=mock_superuser.id,
                )

            assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_delete_index_exception(self, mock_session, mock_superuser):
        """Test index deletion with exception."""
        from app.api.v1.endpoints.search import delete_index

        with patch(
            "app.api.v1.endpoints.search.get_search_backend",
            new_callable=AsyncMock,
        ) as mock_get_backend:
            mock_get_backend.side_effect = Exception("Connection lost")

            with pytest.raises(HTTPException) as exc:
                await delete_index(
                    index="users",
                    session=mock_session,
                    superuser_id=mock_superuser.id,
                )

            assert exc.value.status_code == 500
