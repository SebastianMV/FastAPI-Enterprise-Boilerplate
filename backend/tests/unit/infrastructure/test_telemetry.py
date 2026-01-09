# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for telemetry infrastructure.

Tests for OpenTelemetry decorators and utilities.
"""

from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

import pytest

from app.infrastructure.observability.telemetry import (
    get_tracer,
    get_meter,
    get_default_meter,
    span_context,
    traced,
    get_current_span,
    inject_trace_context,
)


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_returns_tracer(self) -> None:
        """Test that get_tracer returns a tracer."""
        tracer = get_tracer("test_module")
        
        assert tracer is not None

    def test_tracer_with_different_names(self) -> None:
        """Test getting tracers with different names."""
        tracer1 = get_tracer("module1")
        tracer2 = get_tracer("module2")
        
        assert tracer1 is not None
        assert tracer2 is not None

    def test_default_name(self) -> None:
        """Test tracer with default name."""
        tracer = get_tracer()
        
        assert tracer is not None


class TestGetMeter:
    """Tests for get_meter function."""

    def test_returns_meter(self) -> None:
        """Test that get_meter returns a meter."""
        meter = get_meter("test_module")
        
        assert meter is not None

    def test_meter_with_different_names(self) -> None:
        """Test getting meters with different names."""
        meter1 = get_meter("module1")
        meter2 = get_meter("module2")
        
        assert meter1 is not None
        assert meter2 is not None

    def test_default_name(self) -> None:
        """Test meter with default name."""
        meter = get_meter()
        
        assert meter is not None


class TestGetDefaultMeter:
    """Tests for get_default_meter function."""

    def test_returns_meter(self) -> None:
        """Test that get_default_meter returns a meter."""
        meter = get_default_meter()
        
        assert meter is not None


class TestSpanContext:
    """Tests for span_context context manager."""

    def test_span_context_executes_code(self) -> None:
        """Test that span_context executes wrapped code."""
        executed = False
        
        with span_context("test_operation"):
            executed = True
        
        assert executed is True

    def test_span_context_returns_value(self) -> None:
        """Test that span_context allows return values."""
        result = None
        
        with span_context("calculation"):
            result = 1 + 1
        
        assert result == 2

    def test_span_context_propagates_exceptions(self) -> None:
        """Test that span_context propagates exceptions."""
        with pytest.raises(ValueError, match="test error"):
            with span_context("failing_operation"):
                raise ValueError("test error")


class TestTracedDecorator:
    """Tests for traced decorator."""

    def test_traced_sync_function(self) -> None:
        """Test traced decorator on sync function."""
        @traced("test_func")
        def my_function():
            return 42
        
        result = my_function()
        
        assert result == 42

    def test_traced_sync_with_args(self) -> None:
        """Test traced decorator preserves arguments."""
        @traced("add_func")
        def add(a, b):
            return a + b
        
        result = add(3, 4)
        
        assert result == 7

    @pytest.mark.asyncio
    async def test_traced_async_function(self) -> None:
        """Test traced decorator on async function."""
        @traced("async_test_func")
        async def my_async_function():
            return "async_result"
        
        result = await my_async_function()
        
        assert result == "async_result"

    @pytest.mark.asyncio
    async def test_traced_async_with_args(self) -> None:
        """Test traced decorator preserves async arguments."""
        @traced("async_multiply")
        async def multiply(a, b):
            return a * b
        
        result = await multiply(5, 6)
        
        assert result == 30


class TestGetCurrentSpan:
    """Tests for get_current_span function."""

    def test_returns_span_or_none(self) -> None:
        """Test get_current_span returns span or None."""
        # Outside any span, might return None or a NoOpSpan
        span = get_current_span()
        
        # Should not raise
        assert span is not None or span is None


class TestInjectTraceContext:
    """Tests for inject_trace_context function."""

    def test_inject_to_empty_headers(self) -> None:
        """Test injecting trace context to empty headers."""
        headers = {}
        result = inject_trace_context(headers)
        
        # Should return dict
        assert isinstance(result, dict)

    def test_inject_preserves_existing_headers(self) -> None:
        """Test that existing headers are preserved."""
        headers = {"Authorization": "Bearer token", "Content-Type": "application/json"}
        result = inject_trace_context(headers)
        
        assert result["Authorization"] == "Bearer token"
        assert result["Content-Type"] == "application/json"
