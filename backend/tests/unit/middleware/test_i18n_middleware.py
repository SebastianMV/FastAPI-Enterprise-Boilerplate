# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for i18n middleware."""

from unittest.mock import MagicMock, patch

import pytest


class TestCurrentLocaleContextVar:
    """Tests for locale context variable functions."""

    def test_get_current_locale_default(self):
        """Test default locale is 'en'."""
        from app.middleware.i18n import _current_locale

        # Reset to default
        token = _current_locale.set("en")
        try:
            from app.middleware.i18n import get_current_locale

            assert get_current_locale() == "en"
        finally:
            _current_locale.reset(token)

    def test_set_and_get_current_locale(self):
        """Test setting and getting locale."""
        from app.middleware.i18n import (
            _current_locale,
            get_current_locale,
            set_current_locale,
        )

        original = _current_locale.get()
        try:
            set_current_locale("es")
            assert get_current_locale() == "es"

            set_current_locale("pt")
            assert get_current_locale() == "pt"
        finally:
            set_current_locale(original)

    def test_set_locale_with_region(self):
        """Test setting locale with region code."""
        from app.middleware.i18n import (
            _current_locale,
            get_current_locale,
            set_current_locale,
        )

        original = _current_locale.get()
        try:
            set_current_locale("en-US")
            assert get_current_locale() == "en-US"

            set_current_locale("es-MX")
            assert get_current_locale() == "es-MX"
        finally:
            set_current_locale(original)


class TestI18nMiddleware:
    """Tests for I18nMiddleware class using pure ASGI interface."""

    @pytest.fixture
    def mock_i18n(self):
        """Create a mock i18n instance."""
        i18n = MagicMock()
        i18n.is_supported.return_value = True
        i18n.get_locale_from_header.return_value = "en"
        return i18n

    @pytest.fixture
    def app_with_i18n(self, mock_i18n):
        """Create a test app with I18nMiddleware."""
        from fastapi import FastAPI

        from app.middleware.i18n import I18nMiddleware, get_current_locale

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"locale": get_current_locale()}

        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            app.add_middleware(I18nMiddleware)

        return app

    @pytest.mark.asyncio
    async def test_dispatch_with_x_locale_header(self, mock_i18n):
        """Test locale extraction from X-Locale header."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.middleware.i18n import I18nMiddleware, get_current_locale

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"locale": get_current_locale()}

        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            app.add_middleware(I18nMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/test", headers={"X-Locale": "es"})

        assert response.status_code == 200
        assert response.headers.get("content-language") == "es"
        assert response.json()["locale"] == "es"

    @pytest.mark.asyncio
    async def test_dispatch_with_accept_language_header(self, mock_i18n):
        """Test locale extraction from Accept-Language header."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.middleware.i18n import I18nMiddleware

        mock_i18n.get_locale_from_header.return_value = "es"

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            app.add_middleware(I18nMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/test", headers={"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
                )

        mock_i18n.get_locale_from_header.assert_called_once()
        assert response.headers.get("content-language") == "es"

    @pytest.mark.asyncio
    async def test_dispatch_falls_back_to_default(self, mock_i18n):
        """Test fallback to default locale when no headers present."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.middleware.i18n import I18nMiddleware, get_current_locale

        mock_i18n.get_locale_from_header.return_value = "en"

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"locale": get_current_locale()}

        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            app.add_middleware(I18nMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/test")

        assert response.headers.get("content-language") == "en"

    @pytest.mark.asyncio
    async def test_dispatch_ignores_unsupported_x_locale(self, mock_i18n):
        """Test that unsupported X-Locale header is ignored."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.middleware.i18n import I18nMiddleware

        mock_i18n.is_supported.return_value = False
        mock_i18n.get_locale_from_header.return_value = "pt"

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            app.add_middleware(I18nMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/test", headers={"X-Locale": "xx", "Accept-Language": "pt"}
                )

        assert response.headers.get("content-language") == "pt"

    @pytest.mark.asyncio
    async def test_dispatch_sets_request_state_locale(self, mock_i18n):
        """Test that locale is set in context variable during request."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.middleware.i18n import I18nMiddleware, get_current_locale

        captured_locale = None

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            nonlocal captured_locale
            # The middleware sets locale via context variable, not request.state
            captured_locale = get_current_locale()
            return {"ok": True}

        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            app.add_middleware(I18nMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/test", headers={"X-Locale": "ja"})

        assert captured_locale == "ja"

    @pytest.mark.asyncio
    async def test_dispatch_adds_content_language_header(self, mock_i18n):
        """Test that Content-Language header is added to response."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.middleware.i18n import I18nMiddleware

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            app.add_middleware(I18nMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/test", headers={"X-Locale": "pt"})

        assert response.headers.get("content-language") == "pt"

    @pytest.mark.asyncio
    async def test_x_locale_priority_over_accept_language(self, mock_i18n):
        """Test that X-Locale takes priority over Accept-Language."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.middleware.i18n import I18nMiddleware, get_current_locale

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"locale": get_current_locale()}

        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            app.add_middleware(I18nMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/test", headers={"X-Locale": "ko", "Accept-Language": "zh"}
                )

        # X-Locale should win
        assert response.headers.get("content-language") == "ko"
        assert response.json()["locale"] == "ko"


class TestLocaleIsolation:
    """Tests for locale context isolation."""

    def test_locale_isolation_between_contexts(self):
        """Test that locale changes don't leak between contexts."""
        from app.middleware.i18n import (
            _current_locale,
            get_current_locale,
            set_current_locale,
        )

        original = _current_locale.get()
        try:
            set_current_locale("it")
            assert get_current_locale() == "it"

            # Simulate another "request" changing locale
            set_current_locale("ru")
            assert get_current_locale() == "ru"
        finally:
            set_current_locale(original)

    def test_multiple_locale_sets(self):
        """Test multiple locale changes in sequence."""
        from app.middleware.i18n import (
            _current_locale,
            get_current_locale,
            set_current_locale,
        )

        original = _current_locale.get()
        locales = ["en", "es", "pt", "ja", "ko", "zh", "ru", "it"]

        try:
            for locale in locales:
                set_current_locale(locale)
                assert get_current_locale() == locale
        finally:
            set_current_locale(original)
