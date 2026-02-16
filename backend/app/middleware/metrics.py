# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Metrics middleware for tracking response times and request counts (Pure ASGI).

This middleware:
- Records response time for each request
- Tracks error counts
- Excludes health check endpoints from metrics
"""

import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.infrastructure.monitoring import get_metrics_service
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

# Paths to exclude from metrics tracking
EXCLUDED_PATHS = {
    "/api/v1/health",
    "/api/v1/health/ready",
    "/api/v1/health/live",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class MetricsMiddleware:
    """
    Pure ASGI Middleware that tracks response times and request metrics.

    Features:
    - Records response time in milliseconds
    - Tracks error count (5xx responses)
    - Excludes health check endpoints
    - Thread-safe metrics collection
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface - track metrics for HTTP requests."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip metrics for excluded paths
        path = scope.get("path", "")
        if path in EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        # Record start time
        start_time = time.perf_counter()
        status_code = 200

        async def send_with_metrics(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                # Record metrics
                metrics = get_metrics_service()
                metrics.record_response_time(elapsed_ms)

                # Track errors
                if status_code >= 500:
                    metrics.record_error()

                # Add timing header (non-production only — prevents timing side-channels)
                headers = list(message.get("headers", []))
                if settings.ENVIRONMENT not in ("production", "staging"):
                    headers.append(
                        (b"x-response-time-ms", str(round(elapsed_ms, 2)).encode())
                    )
                message = {**message, "headers": headers}

            await send(message)

        try:
            await self.app(scope, receive, send_with_metrics)
        except Exception:
            # Record error metrics even on exception
            status_code = 500
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            metrics = get_metrics_service()
            metrics.record_response_time(elapsed_ms)
            metrics.record_error()
            raise
