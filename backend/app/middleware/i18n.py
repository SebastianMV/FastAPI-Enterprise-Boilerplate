# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
i18n middleware for FastAPI.

Extracts locale from request headers and makes it available
throughout the request lifecycle.
"""

from contextvars import ContextVar
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.i18n import get_i18n


# Context variable to store current locale for the request
_current_locale: ContextVar[str] = ContextVar("current_locale", default="en")


def get_current_locale() -> str:
    """Get the current request's locale."""
    return _current_locale.get()


def set_current_locale(locale: str) -> None:
    """Set the current request's locale."""
    _current_locale.set(locale)


class I18nMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts locale from Accept-Language header.
    
    The detected locale is stored in a context variable and can
    be accessed via get_current_locale() throughout the request.
    
    Priority for locale detection:
    1. X-Locale header (explicit override)
    2. Accept-Language header
    3. Default locale (en)
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request and set locale context."""
        i18n = get_i18n()
        
        # Check for explicit locale header first
        explicit_locale = request.headers.get("X-Locale")
        if explicit_locale and i18n.is_supported(explicit_locale):
            locale = explicit_locale
        else:
            # Fall back to Accept-Language header
            accept_language = request.headers.get("Accept-Language")
            locale = i18n.get_locale_from_header(accept_language)
        
        # Set locale in context
        set_current_locale(locale)
        
        # Add locale to request state for easy access
        request.state.locale = locale
        
        response = await call_next(request)
        
        # Add Content-Language header to response
        response.headers["Content-Language"] = locale
        
        return response
