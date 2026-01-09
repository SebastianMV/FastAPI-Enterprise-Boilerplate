# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
OpenTelemetry instrumentation for tracing and metrics.

Provides distributed tracing, metrics collection, and context propagation.
Exports to Jaeger, OTLP, or console based on configuration.
"""

import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.config import settings

logger = logging.getLogger(__name__)


def setup_telemetry(app=None) -> None:
    """
    Initialize OpenTelemetry with tracing and metrics.
    
    Args:
        app: FastAPI application instance (optional, for auto-instrumentation)
    """
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry disabled")
        return
    
    # Create resource with service info
    resource = Resource.create({
        SERVICE_NAME: settings.APP_NAME,
        SERVICE_VERSION: settings.APP_VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })
    
    # Setup tracing
    _setup_tracing(resource)
    
    # Setup metrics
    _setup_metrics(resource)
    
    # Auto-instrument libraries
    _instrument_libraries(app)
    
    logger.info(f"OpenTelemetry initialized for {settings.APP_NAME}")


def _setup_tracing(resource: Resource) -> None:
    """Configure trace provider and exporters."""
    provider = TracerProvider(resource=resource)
    
    # Add exporter based on configuration
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(f"OTLP trace exporter configured: {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
    else:
        # Console exporter for development
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("Console trace exporter configured")
    
    trace.set_tracer_provider(provider)


def _setup_metrics(resource: Resource) -> None:
    """Configure metrics provider and exporters."""
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        exporter = OTLPMetricExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        )
        reader = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=60000,  # Export every 60 seconds
        )
    else:
        reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(),
            export_interval_millis=60000,
        )
    
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)


def _instrument_libraries(app=None) -> None:
    """Auto-instrument common libraries."""
    # FastAPI
    if app:
        FastAPIInstrumentor.instrument_app(app)
    
    # SQLAlchemy (will instrument when engine is created)
    SQLAlchemyInstrumentor().instrument()
    
    # Redis
    RedisInstrumentor().instrument()
    
    # HTTPX (for outgoing HTTP requests)
    HTTPXClientInstrumentor().instrument()


def get_tracer(name: str = __name__) -> trace.Tracer:
    """
    Get a tracer instance.
    
    Args:
        name: Name for the tracer (usually __name__)
        
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def get_meter(name: str = __name__) -> metrics.Meter:
    """
    Get a meter instance for metrics.
    
    Args:
        name: Name for the meter (usually __name__)
        
    Returns:
        Meter instance
    """
    return metrics.get_meter(name)


@contextmanager
def span_context(
    name: str,
    attributes: Optional[dict[str, Any]] = None,
    tracer_name: str = __name__,
):
    """
    Context manager for creating spans.
    
    Usage:
        with span_context("process_order", {"order_id": "123"}) as span:
            # Do work
            span.set_attribute("items_count", 5)
    
    Args:
        name: Span name
        attributes: Initial attributes
        tracer_name: Name of the tracer
        
    Yields:
        Active span
    """
    tracer = get_tracer(tracer_name)
    with tracer.start_as_current_span(name, attributes=attributes) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def traced(
    name: Optional[str] = None,
    attributes: Optional[dict[str, Any]] = None,
):
    """
    Decorator for tracing functions.
    
    Usage:
        @traced("process_payment")
        async def process_payment(order_id: str):
            ...
    
    Args:
        name: Span name (defaults to function name)
        attributes: Initial span attributes
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with span_context(span_name, attributes) as span:
                # Add function arguments as attributes
                if kwargs:
                    for key, value in kwargs.items():
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"arg.{key}", value)
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with span_context(span_name, attributes) as span:
                if kwargs:
                    for key, value in kwargs.items():
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"arg.{key}", value)
                return func(*args, **kwargs)
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Pre-configured metrics
_meter = None


def get_default_meter() -> metrics.Meter:
    """Get the default application meter."""
    global _meter
    if _meter is None:
        _meter = get_meter(settings.APP_NAME)
    return _meter


class AppMetrics:
    """
    Pre-defined application metrics.
    
    Usage:
        AppMetrics.request_counter.add(1, {"endpoint": "/users"})
        AppMetrics.request_duration.record(0.5, {"endpoint": "/users"})
    """
    
    _initialized = False
    
    # Counters
    request_counter = None
    error_counter = None
    db_query_counter = None
    
    # Histograms
    request_duration = None
    db_query_duration = None
    
    # Gauges (using UpDownCounter for gauge-like behavior)
    active_connections = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize all metrics."""
        if cls._initialized:
            return
        
        meter = get_default_meter()
        
        # Request metrics
        cls.request_counter = meter.create_counter(
            "http_requests_total",
            description="Total HTTP requests",
            unit="1",
        )
        
        cls.request_duration = meter.create_histogram(
            "http_request_duration_seconds",
            description="HTTP request duration",
            unit="s",
        )
        
        cls.error_counter = meter.create_counter(
            "http_errors_total",
            description="Total HTTP errors",
            unit="1",
        )
        
        # Database metrics
        cls.db_query_counter = meter.create_counter(
            "db_queries_total",
            description="Total database queries",
            unit="1",
        )
        
        cls.db_query_duration = meter.create_histogram(
            "db_query_duration_seconds",
            description="Database query duration",
            unit="s",
        )
        
        # Connection metrics
        cls.active_connections = meter.create_up_down_counter(
            "active_connections",
            description="Number of active connections",
            unit="1",
        )
        
        cls._initialized = True


def add_span_attributes(span: Span, **attributes) -> None:
    """
    Add multiple attributes to a span.
    
    Args:
        span: The span to add attributes to
        **attributes: Key-value pairs to add
    """
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, value)


def get_current_span() -> Optional[Span]:
    """Get the current active span."""
    return trace.get_current_span()


def inject_trace_context(headers: dict) -> dict:
    """
    Inject trace context into headers for propagation.
    
    Args:
        headers: Headers dict to inject into
        
    Returns:
        Headers with trace context
    """
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers
