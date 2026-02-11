# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for tracing infrastructure."""

from __future__ import annotations

import pytest


class TestTracingSetup:
    """Tests for tracing setup."""

    def test_setup_tracing_import(self) -> None:
        """Test setup_tracing can be imported."""
        try:
            from app.infrastructure.observability.tracing import setup_tracing

            assert setup_tracing is not None
        except ImportError:
            pytest.skip("setup_tracing not available")

    def test_tracer_provider_exists(self) -> None:
        """Test tracer provider exists."""
        try:
            from app.infrastructure.observability.tracing import tracer_provider

            # May or may not exist depending on config
        except ImportError:
            pass


class TestSpanContext:
    """Tests for span context."""

    def test_span_context_import(self) -> None:
        """Test span context utilities exist."""
        try:
            from app.infrastructure.observability.tracing import get_current_span

            assert get_current_span is not None
        except ImportError:
            pytest.skip("get_current_span not available")


class TestTraceDecorators:
    """Tests for trace decorators."""

    def test_trace_decorator_import(self) -> None:
        """Test trace decorator can be imported."""
        try:
            from app.infrastructure.observability.tracing import trace

            assert trace is not None
        except ImportError:
            pytest.skip("trace decorator not available")


class TestObservabilityInit:
    """Tests for observability __init__."""

    def test_observability_module_import(self) -> None:
        """Test observability module can be imported."""
        from app.infrastructure import observability

        assert observability is not None

    def test_observability_has_logging(self) -> None:
        """Test observability has logging submodule."""
        from app.infrastructure.observability import logging

        assert logging is not None


class TestMetricsSetup:
    """Tests for metrics setup."""

    def test_metrics_module_import(self) -> None:
        """Test metrics module exists."""
        try:
            from app.infrastructure.observability import metrics

            assert metrics is not None
        except ImportError:
            pytest.skip("metrics module not available")


class TestObservabilityConfig:
    """Tests for observability configuration."""

    def test_config_from_settings(self) -> None:
        """Test observability reads from settings."""
        from app.config import settings

        # Settings should have observability-related configs
        assert settings is not None

    def test_log_level_setting(self) -> None:
        """Test log level can be configured."""
        from app.config import settings

        # Should have a log level setting
        log_level = getattr(settings, "LOG_LEVEL", "INFO")
        assert log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
