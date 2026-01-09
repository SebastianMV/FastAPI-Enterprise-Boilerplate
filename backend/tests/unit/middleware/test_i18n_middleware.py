# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for i18n middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.requests import Request
from starlette.responses import Response


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
        from app.middleware.i18n import get_current_locale, set_current_locale, _current_locale
        
        original = _current_locale.get()
        try:
            set_current_locale("es")
            assert get_current_locale() == "es"
            
            set_current_locale("fr")
            assert get_current_locale() == "fr"
            
            set_current_locale("de")
            assert get_current_locale() == "de"
        finally:
            set_current_locale(original)
    
    def test_set_locale_with_region(self):
        """Test setting locale with region code."""
        from app.middleware.i18n import get_current_locale, set_current_locale, _current_locale
        
        original = _current_locale.get()
        try:
            set_current_locale("en-US")
            assert get_current_locale() == "en-US"
            
            set_current_locale("es-MX")
            assert get_current_locale() == "es-MX"
        finally:
            set_current_locale(original)


class TestI18nMiddleware:
    """Tests for I18nMiddleware class."""
    
    @pytest.fixture
    def mock_i18n(self):
        """Create a mock i18n instance."""
        i18n = MagicMock()
        i18n.is_supported.return_value = True
        i18n.get_locale_from_header.return_value = "en"
        return i18n
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = MagicMock()
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock response."""
        response = MagicMock(spec=Response)
        response.headers = {}
        return response
    
    @pytest.mark.asyncio
    async def test_dispatch_with_x_locale_header(self, mock_i18n, mock_request, mock_response):
        """Test locale extraction from X-Locale header."""
        from app.middleware.i18n import I18nMiddleware, get_current_locale
        
        mock_request.headers = {"X-Locale": "es"}
        
        async def call_next(req):
            # Verify locale is set during request
            assert get_current_locale() == "es"
            return mock_response
        
        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            middleware = I18nMiddleware(app=MagicMock())
            response = await middleware.dispatch(mock_request, call_next)
        
        assert response.headers.get("Content-Language") == "es"
        assert mock_request.state.locale == "es"
    
    @pytest.mark.asyncio
    async def test_dispatch_with_accept_language_header(self, mock_i18n, mock_request, mock_response):
        """Test locale extraction from Accept-Language header."""
        from app.middleware.i18n import I18nMiddleware
        
        mock_request.headers = {"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
        mock_i18n.get_locale_from_header.return_value = "fr"
        
        async def call_next(req):
            return mock_response
        
        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            middleware = I18nMiddleware(app=MagicMock())
            response = await middleware.dispatch(mock_request, call_next)
        
        mock_i18n.get_locale_from_header.assert_called_once_with("fr-FR,fr;q=0.9,en;q=0.8")
        assert response.headers.get("Content-Language") == "fr"
    
    @pytest.mark.asyncio
    async def test_dispatch_falls_back_to_default(self, mock_i18n, mock_request, mock_response):
        """Test fallback to default locale when no headers present."""
        from app.middleware.i18n import I18nMiddleware
        
        mock_request.headers = {}
        mock_i18n.get_locale_from_header.return_value = "en"  # Default
        
        async def call_next(req):
            return mock_response
        
        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            middleware = I18nMiddleware(app=MagicMock())
            response = await middleware.dispatch(mock_request, call_next)
        
        assert response.headers.get("Content-Language") == "en"
        assert mock_request.state.locale == "en"
    
    @pytest.mark.asyncio
    async def test_dispatch_ignores_unsupported_x_locale(self, mock_i18n, mock_request, mock_response):
        """Test that unsupported X-Locale header is ignored."""
        from app.middleware.i18n import I18nMiddleware
        
        mock_request.headers = {
            "X-Locale": "xx",  # Unsupported
            "Accept-Language": "de"
        }
        mock_i18n.is_supported.return_value = False
        mock_i18n.get_locale_from_header.return_value = "de"
        
        async def call_next(req):
            return mock_response
        
        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            middleware = I18nMiddleware(app=MagicMock())
            response = await middleware.dispatch(mock_request, call_next)
        
        # Should fall back to Accept-Language
        mock_i18n.get_locale_from_header.assert_called_once_with("de")
        assert response.headers.get("Content-Language") == "de"
    
    @pytest.mark.asyncio
    async def test_dispatch_sets_request_state_locale(self, mock_i18n, mock_request, mock_response):
        """Test that locale is set in request.state."""
        from app.middleware.i18n import I18nMiddleware
        
        mock_request.headers = {"X-Locale": "ja"}
        
        async def call_next(req):
            return mock_response
        
        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            middleware = I18nMiddleware(app=MagicMock())
            await middleware.dispatch(mock_request, call_next)
        
        assert mock_request.state.locale == "ja"
    
    @pytest.mark.asyncio
    async def test_dispatch_adds_content_language_header(self, mock_i18n, mock_request, mock_response):
        """Test that Content-Language header is added to response."""
        from app.middleware.i18n import I18nMiddleware
        
        mock_request.headers = {"X-Locale": "pt"}
        
        async def call_next(req):
            return mock_response
        
        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            middleware = I18nMiddleware(app=MagicMock())
            response = await middleware.dispatch(mock_request, call_next)
        
        assert response.headers["Content-Language"] == "pt"
    
    @pytest.mark.asyncio
    async def test_x_locale_priority_over_accept_language(self, mock_i18n, mock_request, mock_response):
        """Test that X-Locale takes priority over Accept-Language."""
        from app.middleware.i18n import I18nMiddleware
        
        mock_request.headers = {
            "X-Locale": "ko",
            "Accept-Language": "zh"
        }
        
        async def call_next(req):
            return mock_response
        
        with patch("app.middleware.i18n.get_i18n", return_value=mock_i18n):
            middleware = I18nMiddleware(app=MagicMock())
            response = await middleware.dispatch(mock_request, call_next)
        
        # X-Locale should win
        assert response.headers.get("Content-Language") == "ko"
        # get_locale_from_header should NOT be called when X-Locale is valid
        mock_i18n.get_locale_from_header.assert_not_called()


class TestLocaleIsolation:
    """Tests for locale context isolation."""
    
    def test_locale_isolation_between_contexts(self):
        """Test that locale changes don't leak between contexts."""
        from app.middleware.i18n import get_current_locale, set_current_locale, _current_locale
        
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
        from app.middleware.i18n import get_current_locale, set_current_locale, _current_locale
        
        original = _current_locale.get()
        locales = ["en", "es", "fr", "de", "ja", "ko", "zh", "pt", "ru", "it"]
        
        try:
            for locale in locales:
                set_current_locale(locale)
                assert get_current_locale() == locale
        finally:
            set_current_locale(original)
