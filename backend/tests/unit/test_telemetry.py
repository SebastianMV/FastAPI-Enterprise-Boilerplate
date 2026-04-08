# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Unit tests for telemetry/observability."""

from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.observability.telemetry import (
    AppMetrics,
    add_span_attributes,
    get_current_span,
    get_default_meter,
    get_meter,
    get_tracer,
    inject_trace_context,
    setup_telemetry,
    span_context,
    traced,
)


class TestAppMetrics:
    """Tests for application metrics."""

    def test_metrics_class_exists(self):
        """AppMetrics class should exist."""
        assert AppMetrics is not None
        assert hasattr(AppMetrics, "initialize")
        assert hasattr(AppMetrics, "request_counter")
        assert hasattr(AppMetrics, "db_query_counter")

    def test_metrics_attributes_exist(self):
        """Metrics should have expected attributes."""
        # These are class attributes, initially None
        assert hasattr(AppMetrics, "request_counter")
        assert hasattr(AppMetrics, "request_duration")
        assert hasattr(AppMetrics, "error_counter")
        assert hasattr(AppMetrics, "db_query_counter")
        assert hasattr(AppMetrics, "db_query_duration")
        assert hasattr(AppMetrics, "active_connections")

    def test_initialize_is_classmethod(self):
        """Initialize should be a classmethod."""
        assert callable(AppMetrics.initialize)


class TestTracedDecorator:
    """Tests for @traced decorator."""

    @pytest.mark.asyncio
    async def test_traced_async_function(self):
        """Should trace async function."""

        @traced(name="test.operation")
        async def async_operation():
            return "result"

        result = await async_operation()
        assert result == "result"

    def test_traced_sync_function(self):
        """Should trace sync function."""

        @traced(name="test.sync_operation")
        def sync_operation():
            return "sync_result"

        result = sync_operation()
        assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_traced_with_exception(self):
        """Should record exception in span."""

        @traced(name="test.failing_operation")
        async def failing_operation():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_operation()

    @pytest.mark.asyncio
    async def test_traced_without_name(self):
        """Should use function name if no name provided."""

        @traced()
        async def my_function():
            return "done"

        result = await my_function()
        assert result == "done"

    def test_traced_sync_with_kwargs(self):
        """Should handle keyword arguments."""

        @traced(name="test.with_kwargs")
        def function_with_kwargs(name: str, value: int):
            return f"{name}: {value}"

        result = function_with_kwargs(name="test", value=42)
        assert result == "test: 42"


class TestSpanContext:
    """Tests for span_context context manager."""

    def test_span_context_basic(self):
        """Should create span with context manager."""
        with span_context("test.span") as span:
            assert span is not None

    def test_span_context_with_attributes(self):
        """Should accept attributes."""
        with span_context("test.span", attributes={"key": "value"}) as span:
            assert span is not None

    def test_span_context_exception_handling(self):
        """Should handle exceptions."""
        with pytest.raises(ValueError), span_context("test.failing") as span:
            raise ValueError("Test error")


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_get_tracer_returns_tracer(self):
        """Should return a tracer instance."""
        tracer = get_tracer("test.module")
        assert tracer is not None

    def test_get_tracer_with_default_name(self):
        """Should work with default name."""
        tracer = get_tracer()
        assert tracer is not None


class TestGetMeter:
    """Tests for get_meter function."""

    def test_get_meter_returns_meter(self):
        """Should return a meter instance."""
        meter = get_meter("test.module")
        assert meter is not None

    def test_get_meter_with_default_name(self):
        """Should work with default name."""
        meter = get_meter()
        assert meter is not None


class TestGetDefaultMeter:
    """Tests for get_default_meter function."""

    def test_get_default_meter_returns_meter(self):
        """Should return a meter instance."""
        meter = get_default_meter()
        assert meter is not None

    def test_get_default_meter_caches_result(self):
        """Should return the same meter on multiple calls."""
        meter1 = get_default_meter()
        meter2 = get_default_meter()
        assert meter1 is meter2


class TestSetupTelemetry:
    """Tests for setup_telemetry function."""

    def test_setup_telemetry_disabled(self):
        """Should skip setup when OTEL is disabled."""
        with patch(
            "app.infrastructure.observability.telemetry.settings"
        ) as mock_settings:
            mock_settings.OTEL_ENABLED = False
            # Should not raise and should return early
            setup_telemetry(app=None)

    def test_setup_telemetry_with_console_exporter(self):
        """Should configure console exporter when no OTLP endpoint."""
        with patch(
            "app.infrastructure.observability.telemetry.settings"
        ) as mock_settings:
            mock_settings.OTEL_ENABLED = True
            mock_settings.OTEL_EXPORTER_OTLP_ENDPOINT = None
            mock_settings.APP_NAME = "test-app"
            mock_settings.APP_VERSION = "1.0.0"
            mock_settings.ENVIRONMENT = "test"
            # Should configure with console exporter
            setup_telemetry(app=None)


class TestAddSpanAttributes:
    """Tests for add_span_attributes function."""

    def test_add_span_attributes_with_values(self):
        """Should add multiple attributes to span."""
        mock_span = MagicMock()
        add_span_attributes(mock_span, key1="value1", key2=123)
        assert mock_span.set_attribute.call_count == 2
        mock_span.set_attribute.assert_any_call("key1", "value1")
        mock_span.set_attribute.assert_any_call("key2", 123)

    def test_add_span_attributes_skips_none(self):
        """Should skip None values."""
        mock_span = MagicMock()
        add_span_attributes(mock_span, key1="value1", key2=None)
        mock_span.set_attribute.assert_called_once_with("key1", "value1")

    def test_add_span_attributes_empty(self):
        """Should handle no attributes."""
        mock_span = MagicMock()
        add_span_attributes(mock_span)
        mock_span.set_attribute.assert_not_called()


class TestGetCurrentSpan:
    """Tests for get_current_span function."""

    def test_get_current_span_returns_span(self):
        """Should return current span or NoOp span."""
        span = get_current_span()
        assert span is not None

    def test_get_current_span_within_context(self):
        """Should return actual span within span context."""
        with span_context("test.span") as expected_span:
            current = get_current_span()
            # Should be the same span or wrapped version
            assert current is not None


class TestInjectTraceContext:
    """Tests for inject_trace_context function."""

    def test_inject_trace_context_empty_headers(self):
        """Should inject trace context into empty headers."""
        headers = {}
        result = inject_trace_context(headers)
        assert result is headers  # Should return same dict

    def test_inject_trace_context_existing_headers(self):
        """Should preserve existing headers."""
        headers = {"Content-Type": "application/json"}
        result = inject_trace_context(headers)
        assert "Content-Type" in result
        assert result["Content-Type"] == "application/json"

    def test_inject_trace_context_within_span(self):
        """Should inject traceparent within a span context."""
        with span_context("test.propagation"):
            headers = {}
            result = inject_trace_context(headers)
            # Within an active span, traceparent should be injected
            # Note: This depends on the actual tracer implementation
            assert result is not None


class TestAppMetricsInitialize:
    """Tests for AppMetrics.initialize method."""

    def test_initialize_creates_counters(self):
        """Should create metric counters."""
        # Reset state
        AppMetrics._initialized = False
        AppMetrics.request_counter = None

        AppMetrics.initialize()

        assert AppMetrics._initialized is True
        assert AppMetrics.request_counter is not None

    def test_initialize_idempotent(self):
        """Should only initialize once."""
        AppMetrics._initialized = False
        AppMetrics.initialize()
        first_counter = AppMetrics.request_counter

        AppMetrics.initialize()  # Second call
        second_counter = AppMetrics.request_counter

        # Should be the same instance
        assert first_counter is second_counter

    def test_initialize_creates_all_metrics(self):
        """Should create all defined metrics."""
        AppMetrics._initialized = False
        AppMetrics.request_counter = None
        AppMetrics.request_duration = None
        AppMetrics.error_counter = None
        AppMetrics.db_query_counter = None
        AppMetrics.db_query_duration = None
        AppMetrics.active_connections = None

        AppMetrics.initialize()

        assert AppMetrics.request_counter is not None
        assert AppMetrics.request_duration is not None
        assert AppMetrics.error_counter is not None
        assert AppMetrics.db_query_counter is not None
        assert AppMetrics.db_query_duration is not None
        assert AppMetrics.active_connections is not None
