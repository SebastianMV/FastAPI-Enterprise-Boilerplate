# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
CSRF Protection Middleware (Double-Submit Cookie Pattern).

Generates a random CSRF token stored in a **non-HttpOnly** cookie so the
browser-side JS can read it. State-changing requests (POST, PUT, PATCH,
DELETE) must echo the token back via the ``X-CSRF-Token`` header.

Because the cookie is ``SameSite=Lax`` (or Strict) a cross-origin site
cannot read it, making the double-submit approach effective against CSRF.
"""

import hmac
import secrets

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = b"x-csrf-token"
CSRF_TOKEN_BYTES = 32
CSRF_COOKIE_MAX_AGE: int = getattr(settings, "CSRF_COOKIE_MAX_AGE", 86400)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
# Paths that are exempt from CSRF (e.g. login itself sets the cookie)
EXEMPT_PATHS: set[str] = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
    # Only exempt OAuth callback paths (external redirects), not management endpoints
    "/api/v1/auth/oauth/google/callback",
    "/api/v1/auth/oauth/github/callback",
    "/api/v1/auth/oauth/microsoft/callback",
    "/api/v1/auth/oauth/google/callback/redirect",
    "/api/v1/auth/oauth/github/callback/redirect",
    "/api/v1/auth/oauth/microsoft/callback/redirect",
    "/api/v1/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class CSRFMiddleware:
    """
    Pure ASGI middleware implementing the double-submit cookie CSRF pattern.

    • GET / HEAD / OPTIONS — pass through (no mutation).
    • POST / PUT / PATCH / DELETE:
      - Read ``csrf_token`` cookie from the request.
      - Read ``X-CSRF-Token`` header from the request.
      - If they don't match → reject with **403 Forbidden**.
    • Every response re-sets the cookie so it stays fresh.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "GET")
        path: str = scope.get("path", "/")

        # --- Extract cookies & headers from the raw ASGI scope ---
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode()
        csrf_cookie = self._parse_cookie(cookie_header, CSRF_COOKIE_NAME)

        # --- Validate on state-changing methods ---
        if method not in SAFE_METHODS and not self._is_exempt(path):
            csrf_header = headers.get(CSRF_HEADER_NAME, b"").decode()

            if (
                not csrf_cookie
                or not csrf_header
                or not hmac.compare_digest(csrf_cookie, csrf_header)
            ):
                logger.warning(
                    "csrf_validation_failed",
                    path=path,
                    method=method,
                    has_cookie=bool(csrf_cookie),
                    has_header=bool(csrf_header),
                )
                response_body = (
                    b'{"detail":"CSRF token missing or invalid","code":"CSRF_FAILED"}'
                )
                await send(
                    {
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(response_body)).encode()),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": response_body,
                    }
                )
                return

        # --- Let the request through, then stamp a CSRF cookie on the response ---
        # Rotate token on state-changing requests (POST/PUT/PATCH/DELETE)
        # to mitigate BREACH attacks. Safe requests reuse the existing token.
        if method not in SAFE_METHODS:
            new_token = secrets.token_urlsafe(CSRF_TOKEN_BYTES)
        else:
            new_token = csrf_cookie or secrets.token_urlsafe(CSRF_TOKEN_BYTES)

        async def send_with_csrf(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                cookie_value = self._build_set_cookie(new_token)
                response_headers.append((b"set-cookie", cookie_value.encode()))
                message = {**message, "headers": response_headers}
            await send(message)

        await self.app(scope, receive, send_with_csrf)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_cookie(cookie_header: str, name: str) -> str | None:
        """Extract a single cookie value from the raw Cookie header."""
        for pair in cookie_header.split(";"):
            pair = pair.strip()
            if pair.startswith(f"{name}="):
                return pair[len(name) + 1 :]
        return None

    @staticmethod
    def _is_exempt(path: str) -> bool:
        """Check if the path is exempt from CSRF validation.

        Matches exact path or path with trailing slash.
        E.g., '/api/v1/auth/login' matches '/api/v1/auth/login'
        and '/api/v1/auth/login/' but NOT '/api/v1/auth/login-extra'.
        """
        # Strip trailing slash for consistent matching
        normalized = path.rstrip("/")
        return normalized in EXEMPT_PATHS

    @staticmethod
    def _build_set_cookie(token: str) -> str:
        """Build a Set-Cookie header value for the CSRF token."""
        parts = [
            f"{CSRF_COOKIE_NAME}={token}",
            "Path=/",
            f"SameSite={settings.AUTH_COOKIE_SAMESITE.capitalize()}",
        ]
        if settings.AUTH_COOKIE_SECURE:
            parts.append("Secure")
        if settings.AUTH_COOKIE_DOMAIN:
            parts.append(f"Domain={settings.AUTH_COOKIE_DOMAIN}")
        # Max-Age = 24 hours (renewed on every response)
        parts.append(f"Max-Age={CSRF_COOKIE_MAX_AGE}")
        # NOT HttpOnly — JS must be able to read it
        return "; ".join(parts)
