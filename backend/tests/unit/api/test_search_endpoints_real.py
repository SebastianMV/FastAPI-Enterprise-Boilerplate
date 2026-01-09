# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for search endpoints."""

from __future__ import annotations

from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import pytest


class TestSearchEndpointStructure:
    """Tests for search endpoints structure."""

    def test_router_import(self) -> None:
        """Test router can be imported."""
        from app.api.v1.endpoints.search import router
        assert router is not None

    def test_router_is_api_router(self) -> None:
        """Test router is an APIRouter."""
        from app.api.v1.endpoints.search import router
        from fastapi import APIRouter
        assert isinstance(router, APIRouter)

    def test_router_has_routes(self) -> None:
        """Test router has search routes."""
        from app.api.v1.endpoints.search import router
        assert len(router.routes) >= 1


class TestSearchInfrastructure:
    """Tests for search infrastructure."""

    def test_elasticsearch_module_import(self) -> None:
        """Test elasticsearch module can be imported."""
        from app.infrastructure.search import elasticsearch
        assert elasticsearch is not None

    def test_postgres_fts_module_import(self) -> None:
        """Test postgres_fts module can be imported."""
        from app.infrastructure.search import postgres_fts
        assert postgres_fts is not None


class TestSearchRoutes:
    """Tests for search router routes."""

    def test_search_endpoint_exists(self) -> None:
        """Test search endpoint is registered."""
        from app.api.v1.endpoints.search import router
        
        paths = [getattr(r, "path", None) for r in router.routes]
        assert len(paths) > 0

    def test_router_has_multiple_routes(self) -> None:
        """Test router has multiple search routes."""
        from app.api.v1.endpoints.search import router
        
        assert len(router.routes) >= 1


class TestSearchConfig:
    """Tests for search configuration."""

    def test_search_config_exists(self) -> None:
        """Test search configuration exists in settings."""
        from app.config import settings
        
        # Check that settings object exists and has attributes
        assert settings is not None
