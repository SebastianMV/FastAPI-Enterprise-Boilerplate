# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
OpenTelemetry instrumentation for tracing and metrics.

Provides distributed tracing, metrics collection, and context propagation.
Exports to Jaeger, OTLP, or console based on configuration.
"""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from typing import Any

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Span, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.config import settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


def setup_telemetry(app: FastAPI | None = None) -> None:
    """
    Initialize OpenTelemetry with tracing and metrics.

    Args:
        app: FastAPI application instance (optional, for auto-instrumentation)
    """
    if not settings.OTEL_ENABLED:
        logger.info("otel_disabled")
        return

    # Create resource with service info
    resource = Resource.create(
        {
            SERVICE_NAME: settings.APP_NAME,
            SERVICE_VERSION: settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    # Setup tracing
    _setup_tracing(resource)

    # Setup metrics
    _setup_metrics(resource)

    # Auto-instrument libraries
    _instrument_libraries(app)

    logger.info("otel_initialized", app_name=settings.APP_NAME)


def _setup_tracing(resource: Resource) -> None:
    """Configure trace provider and exporters."""
    provider = TracerProvider(resource=resource)

    # Add exporter based on configuration
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        otel_insecure = getattr(
            settings, "OTEL_EXPORTER_INSECURE", settings.ENVIRONMENT == "development"
        )
        if not otel_insecure and settings.ENVIRONMENT in ("production", "staging"):
            logger.warning(
                "otlp_exporter_tls_enabled", environment=settings.ENVIRONMENT
            )
        exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=otel_insecure,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(
            "otlp_trace_exporter_configured",
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        )
    else:
        # Console exporter for development
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("console_trace_exporter_configured")

    trace.set_tracer_provider(provider)


def _setup_metrics(resource: Resource) -> None:
    """Configure metrics provider and exporters."""
    export_interval_ms = 60_000  # Export every 60 seconds

    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        otel_insecure = getattr(
            settings, "OTEL_EXPORTER_INSECURE", settings.ENVIRONMENT == "development"
        )
        exporter = OTLPMetricExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=otel_insecure,
        )
        reader = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=export_interval_ms,
        )
    else:
        reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(),
            export_interval_millis=export_interval_ms,
        )

    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)


def _instrument_libraries(app: FastAPI | None = None) -> None:
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
    attributes: dict[str, Any] | None = None,
    tracer_name: str = __name__,
) -> Generator[trace.Span]:
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
            span.set_status(Status(StatusCode.ERROR, type(e).__name__))
            span.record_exception(e)
            raise


def traced(
    name: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Callable[..., Callable[..., Any]]:
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

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        span_name = name or func.__name__
        # PII blocklist: never capture these kwargs as span attributes
        _sensitive_keys = {
            "password",
            "secret",
            "token",
            "api_key",
            "authorization",
            "email",
            "credit_card",
            "refresh_token",
            "access_token",
            "password_hash",
            "mfa_code",
            "otp",
        }

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with span_context(span_name, attributes) as span:
                # Add function arguments as attributes (excluding PII)
                if kwargs:
                    for key, value in kwargs.items():
                        if key.lower() in _sensitive_keys:
                            continue
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"arg.{key}", value)
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with span_context(span_name, attributes) as span:
                if kwargs:
                    for key, value in kwargs.items():
                        if key.lower() in _sensitive_keys:
                            continue
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


def add_span_attributes(span: Span, **attributes: Any) -> None:
    """
    Add multiple attributes to a span.

    Args:
        span: The span to add attributes to
        **attributes: Key-value pairs to add
    """
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, value)


def get_current_span() -> Span | None:
    """Get the current active span."""
    return trace.get_current_span()


def inject_trace_context(headers: dict[str, str]) -> dict[str, str]:
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
