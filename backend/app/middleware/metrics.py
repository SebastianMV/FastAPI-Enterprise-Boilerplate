# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Metrics middleware for tracking response times and request counts.

This middleware:
- Records response time for each request
- Tracks error counts
- Excludes health check endpoints from metrics
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.monitoring import get_metrics_service


logger = logging.getLogger(__name__)

# Paths to exclude from metrics tracking
EXCLUDED_PATHS = {
    "/api/v1/health",
    "/api/v1/health/ready",
    "/api/v1/health/live",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks response times and request metrics.
    
    Usage:
        app.add_middleware(MetricsMiddleware)
    
    Features:
    - Records response time in milliseconds
    - Tracks error count (5xx responses)
    - Excludes health check endpoints
    - Thread-safe metrics collection
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Process request and track metrics.
        """
        # Skip metrics for excluded paths
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)
        
        # Record start time
        start_time = time.perf_counter()
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Record metrics
            metrics = get_metrics_service()
            metrics.record_response_time(elapsed_ms)
            
            # Track errors
            if response.status_code >= 500:
                metrics.record_error()
            
            # Add timing header for debugging
            response.headers["X-Response-Time-Ms"] = str(round(elapsed_ms, 2))
            
            return response
            
        except Exception as e:
            # Calculate response time even on error
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Record metrics
            metrics = get_metrics_service()
            metrics.record_response_time(elapsed_ms)
            metrics.record_error()
            
            # Re-raise the exception
            raise
