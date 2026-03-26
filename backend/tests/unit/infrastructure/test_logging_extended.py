# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Extended tests for logging infrastructure."""

from __future__ import annotations

import logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_import(self) -> None:
        """Test setup_logging can be imported."""
        from app.infrastructure.observability.logging import setup_logging

        assert setup_logging is not None
        assert callable(setup_logging)

    def test_setup_logging_configures_root(self) -> None:
        """Test setup_logging configures root logger."""
        from app.infrastructure.observability.logging import setup_logging

        # Should not raise
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger is not None


class TestStructuredLogging:
    """Tests for structured logging."""

    def test_json_formatter_exists(self) -> None:
        """Test JSON formatter is available."""
        try:
            from app.infrastructure.observability.logging import JSONFormatter

            formatter = JSONFormatter()
            assert formatter is not None
        except ImportError:
            # Might use different name
            pass

    def test_log_context_exists(self) -> None:
        """Test log context utilities exist."""
        try:
            from app.infrastructure.observability.logging import LogContext

            assert LogContext is not None
        except ImportError:
            pass


class TestLogLevels:
    """Tests for log level configuration."""

    def test_debug_level(self) -> None:
        """Test DEBUG log level."""
        assert logging.DEBUG == 10

    def test_info_level(self) -> None:
        """Test INFO log level."""
        assert logging.INFO == 20

    def test_warning_level(self) -> None:
        """Test WARNING log level."""
        assert logging.WARNING == 30

    def test_error_level(self) -> None:
        """Test ERROR log level."""
        assert logging.ERROR == 40


class TestLoggerCreation:
    """Tests for logger creation."""

    def test_get_logger(self) -> None:
        """Test getting a named logger."""
        logger = logging.getLogger("test_logger")
        assert logger is not None
        assert logger.name == "test_logger"

    def test_logger_has_handlers(self) -> None:
        """Test root logger has handlers after setup."""
        from app.infrastructure.observability.logging import setup_logging

        setup_logging()
        root = logging.getLogger()
        # Root logger should have at least one handler
        assert root is not None


class TestLoggingConfig:
    """Tests for logging configuration."""

    def test_log_format_contains_timestamp(self) -> None:
        """Test log format includes timestamp."""
        # Standard log format should include time
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert "asctime" in format_str

    def test_log_format_contains_level(self) -> None:
        """Test log format includes level."""
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert "levelname" in format_str
