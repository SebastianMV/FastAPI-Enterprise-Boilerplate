# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for common schemas."""

from __future__ import annotations

import pytest
from pydantic import BaseModel


class TestPaginatedResponse:
    """Tests for PaginatedResponse schema."""

    def test_create_paginated_response(self) -> None:
        """Test PaginatedResponse.create() method."""
        from app.api.v1.schemas.common import PaginatedResponse
        
        class Item(BaseModel):
            id: int
            name: str
        
        items = [
            Item(id=1, name="Item 1"),
            Item(id=2, name="Item 2"),
            Item(id=3, name="Item 3"),
        ]
        
        response = PaginatedResponse[Item].create(
            items=items,
            total=10,
            page=1,
            page_size=3,
        )
        
        assert len(response.items) == 3
        assert response.total == 10
        assert response.page == 1
        assert response.page_size == 3
        assert response.pages == 4  # ceil(10 / 3) = 4

    def test_create_paginated_response_exact_pages(self) -> None:
        """Test pagination with exact page division."""
        from app.api.v1.schemas.common import PaginatedResponse
        
        class Item(BaseModel):
            id: int
        
        items = [Item(id=i) for i in range(10)]
        
        response = PaginatedResponse[Item].create(
            items=items,
            total=20,
            page=1,
            page_size=10,
        )
        
        assert response.pages == 2  # 20 / 10 = 2

    def test_create_paginated_response_single_page(self) -> None:
        """Test pagination with single page."""
        from app.api.v1.schemas.common import PaginatedResponse
        
        class Item(BaseModel):
            id: int
        
        items = [Item(id=i) for i in range(5)]
        
        response = PaginatedResponse[Item].create(
            items=items,
            total=5,
            page=1,
            page_size=10,
        )
        
        assert response.pages == 1  # Only 1 page needed

    def test_create_paginated_response_empty_items(self) -> None:
        """Test pagination with no items."""
        from app.api.v1.schemas.common import PaginatedResponse
        
        class Item(BaseModel):
            id: int
        
        response = PaginatedResponse[Item].create(
            items=[],
            total=0,
            page=1,
            page_size=10,
        )
        
        assert len(response.items) == 0
        assert response.total == 0
        assert response.pages == 0
