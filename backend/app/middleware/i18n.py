# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
i18n middleware for FastAPI (Pure ASGI).

Extracts locale from request headers and makes it available
throughout the request lifecycle.
"""

from contextvars import ContextVar

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.infrastructure.i18n import get_i18n

# Context variable to store current locale for the request
_current_locale: ContextVar[str] = ContextVar("current_locale", default="en")


def get_current_locale() -> str:
    """Get the current request's locale."""
    return _current_locale.get()


def set_current_locale(locale: str) -> None:
    """Set the current request's locale."""
    _current_locale.set(locale)


class I18nMiddleware:
    """
    Pure ASGI Middleware that extracts locale from Accept-Language header.

    The detected locale is stored in a context variable and can
    be accessed via get_current_locale() throughout the request.

    Priority for locale detection:
    1. X-Locale header (explicit override)
    2. Accept-Language header
    3. Default locale (en)
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface - set locale context for HTTP requests."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        i18n = get_i18n()

        # Extract headers
        headers = dict(scope.get("headers", []))

        # Check for explicit locale header first
        explicit_locale = headers.get(b"x-locale", b"").decode()
        if explicit_locale and i18n.is_supported(explicit_locale):
            locale = explicit_locale
        else:
            # Fall back to Accept-Language header
            accept_language = headers.get(b"accept-language", b"").decode()
            locale = (
                i18n.get_locale_from_header(accept_language)
                if accept_language
                else "en"
            )

        # Set locale in context
        token = _current_locale.set(locale)

        try:

            async def send_with_locale(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    # Add Content-Language header
                    headers.append((b"content-language", locale.encode()))
                    message = {**message, "headers": headers}
                await send(message)

            await self.app(scope, receive, send_with_locale)
        finally:
            _current_locale.reset(token)
