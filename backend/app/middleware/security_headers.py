# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Security Headers Middleware (Pure ASGI).

Adds essential security headers to all responses for protection against
common web vulnerabilities like XSS, clickjacking, and content sniffing.

Migrated from BaseHTTPMiddleware to pure ASGI for better compatibility
with Python 3.13+ and pytest-asyncio.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware:
    """
    Pure ASGI Middleware that adds security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Legacy XSS protection for older browsers
    - Strict-Transport-Security: Enforces HTTPS connections (HSTS)
    - Content-Security-Policy: Controls resource loading
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    """

    HSTS_DEFAULT_MAX_AGE = 31536000  # 1 year in seconds

    def __init__(
        self,
        app: ASGIApp,
        *,
        hsts_enabled: bool = True,
        hsts_max_age: int = HSTS_DEFAULT_MAX_AGE,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        csp_policy: str | None = None,
        frame_options: str = "DENY",
        referrer_policy: str = "strict-origin-when-cross-origin",
    ):
        """Initialize security headers middleware."""
        self.app = app
        self.hsts_enabled = hsts_enabled
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.frame_options = frame_options
        self.referrer_policy = referrer_policy

        # Build HSTS header value
        self.hsts_value = self._build_hsts_value()

        # Build CSP header value
        self.csp_policy = csp_policy or self._default_csp_policy()

        # Pre-build security headers for performance
        self._security_headers = self._build_security_headers()

        logger.info(
            "security_headers_initialized",
            hsts_enabled=self.hsts_enabled,
            frame_options=self.frame_options,
        )

    def _build_hsts_value(self) -> str:
        """Build the Strict-Transport-Security header value."""
        parts = [f"max-age={self.hsts_max_age}"]
        if self.hsts_include_subdomains:
            parts.append("includeSubDomains")
        if self.hsts_preload:
            parts.append("preload")
        return "; ".join(parts)

    def _default_csp_policy(self) -> str:
        """Build default Content-Security-Policy."""
        directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        return "; ".join(directives)

    def _build_security_headers(self) -> list[tuple[bytes, bytes]]:
        """Pre-build security headers as bytes for performance."""
        headers = [
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", self.frame_options.encode()),
            (b"x-xss-protection", b"0"),  # Deprecated; CSP provides XSS protection
            (b"content-security-policy", self.csp_policy.encode()),
            (b"referrer-policy", self.referrer_policy.encode()),
            (b"cache-control", b"no-store"),
            (
                b"permissions-policy",
                b"accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()",
            ),
        ]

        if self.hsts_enabled:
            headers.append((b"strict-transport-security", self.hsts_value.encode()))

        return headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface - add security headers to HTTP responses."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # Add security headers
                headers.extend(self._security_headers)

                # Remove server header if present
                headers = [(k, v) for k, v in headers if k.lower() != b"server"]

                message = {**message, "headers": headers}

            await send(message)

        await self.app(scope, receive, send_with_security_headers)


def get_security_headers_middleware() -> type[SecurityHeadersMiddleware]:
    """Factory function to create security headers middleware with settings."""
    hsts_enabled = getattr(settings, "SECURITY_HEADERS_HSTS_ENABLED", True)
    hsts_max_age = getattr(
        settings,
        "SECURITY_HEADERS_HSTS_MAX_AGE",
        SecurityHeadersMiddleware.HSTS_DEFAULT_MAX_AGE,
    )
    csp_policy = getattr(settings, "SECURITY_HEADERS_CSP", None)

    class ConfiguredSecurityHeadersMiddleware(SecurityHeadersMiddleware):
        def __init__(self, app: ASGIApp):
            super().__init__(
                app,
                hsts_enabled=hsts_enabled,
                hsts_max_age=hsts_max_age,
                csp_policy=csp_policy,
            )

    return ConfiguredSecurityHeadersMiddleware
