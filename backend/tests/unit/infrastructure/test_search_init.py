# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Tests for Search module initialization."""

from unittest.mock import MagicMock

import pytest

from app.infrastructure.search import (
    PostgresFullTextSearch,
    get_postgres_search,
    get_search_backend,
)


class TestSearchAvailability:
    """Tests for search backend availability."""

    def test_postgres_search_always_available(self):
        """PostgreSQL FTS should always be available."""
        from app.infrastructure.search import PostgresFullTextSearch

        assert PostgresFullTextSearch is not None

    def test_postgres_search_factory_exists(self):
        """get_postgres_search factory should exist."""
        from app.infrastructure.search import get_postgres_search

        assert callable(get_postgres_search)


class TestGetSearchBackend:
    """Tests for getting PostgreSQL search backend."""

    @pytest.mark.asyncio
    async def test_get_backend_with_session(self):
        """Should return PostgresFullTextSearch with session."""
        mock_session = MagicMock()

        backend = await get_search_backend(session=mock_session)

        assert backend is not None
        assert isinstance(backend, PostgresFullTextSearch)

    @pytest.mark.asyncio
    async def test_get_backend_with_language(self):
        """Should pass language parameter to postgres backend."""
        mock_session = MagicMock()

        backend = await get_search_backend(session=mock_session, language="spanish")

        assert backend is not None
        assert backend._language == "spanish"

    @pytest.mark.asyncio
    async def test_get_backend_default_language(self):
        """Should use default english language if not specified."""
        mock_session = MagicMock()

        backend = await get_search_backend(session=mock_session)

        assert backend._language == "english"


class TestGetPostgresSearch:
    """Tests for get_postgres_search factory."""

    def test_get_postgres_search_returns_instance(self):
        """Should return PostgresFullTextSearch instance."""
        mock_session = MagicMock()

        result = get_postgres_search(session=mock_session)

        assert isinstance(result, PostgresFullTextSearch)

    def test_get_postgres_search_with_language(self):
        """Should set custom language."""
        mock_session = MagicMock()

        result = get_postgres_search(session=mock_session, language="spanish")

        assert result._language == "spanish"

    def test_get_postgres_search_default_english(self):
        """Should default to english language."""
        mock_session = MagicMock()

        result = get_postgres_search(session=mock_session)

        assert result._language == "english"
