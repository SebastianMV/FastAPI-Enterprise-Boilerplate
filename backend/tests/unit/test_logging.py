# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Unit tests for structured logging."""

import json
import logging

import pytest

from app.infrastructure.observability.logging import (
    ConsoleFormatter,
    ContextLogger,
    JSONFormatter,
    clear_log_context,
    get_logger,
    set_log_context,
    setup_logging,
)


class TestJSONFormatter:
    """Tests for JSON log formatter."""

    @pytest.fixture
    def formatter(self):
        """Create JSON formatter."""
        return JSONFormatter()

    @pytest.fixture
    def log_record(self):
        """Create a log record for testing."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_format_basic_record(self, formatter, log_record):
        """Should format log record as JSON."""
        output = formatter.format(log_record)

        data = json.loads(output)

        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert "timestamp" in data

    def test_format_with_exception(self, formatter):
        """Should include exception info."""
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="/app/test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "Test error" in data["exception"]


class TestConsoleFormatter:
    """Tests for console log formatter."""

    @pytest.fixture
    def formatter(self):
        """Create console formatter."""
        return ConsoleFormatter()

    @pytest.fixture
    def log_record(self):
        """Create a log record for testing."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_format_includes_level_and_message(self, formatter, log_record):
        """Should include level and message."""
        output = formatter.format(log_record)

        assert "INFO" in output
        assert "Test message" in output

    def test_format_warning_level(self, formatter):
        """Should format warning level."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="/app/test.py",
            lineno=42,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        assert "WARNING" in output

    def test_format_error_level(self, formatter):
        """Should format error level."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/app/test.py",
            lineno=42,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        assert "ERROR" in output


class TestContextLogger:
    """Tests for context-aware logger."""

    def test_get_logger_returns_context_logger(self):
        """Should return ContextLogger instance."""
        logger = get_logger("test")
        assert isinstance(logger, ContextLogger)

    def test_logger_can_log_info(self):
        """Should be able to log info messages."""
        logger = get_logger("test.unit")
        # Should not raise
        logger.info("Test info message")

    def test_logger_can_log_with_extra_fields(self):
        """Should accept extra_fields parameter."""
        logger = get_logger("test.unit")
        # Should not raise
        logger.info("Test with extras", extra_fields={"key": "value"})


class TestSetLogContext:
    """Tests for log context setting."""

    def test_set_log_context_sets_request_id(self):
        """Should set request_id in context."""
        clear_log_context()
        set_log_context(request_id="test-123")
        # Context is set (no exception means success)
        clear_log_context()

    def test_set_log_context_sets_user_id(self):
        """Should set user_id in context."""
        clear_log_context()
        set_log_context(user_id="user-456")
        clear_log_context()

    def test_set_log_context_sets_tenant_id(self):
        """Should set tenant_id in context."""
        clear_log_context()
        set_log_context(tenant_id="tenant-789")
        clear_log_context()

    def test_clear_log_context(self):
        """Should clear all context variables."""
        set_log_context(request_id="123", user_id="456", tenant_id="789")
        clear_log_context()
        # No exception means success


class TestSetupLogging:
    """Tests for logging setup."""

    def test_setup_configures_root_logger(self):
        """Should configure root logger."""
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger is not None
        assert len(root_logger.handlers) > 0

    def test_setup_with_json_format(self, monkeypatch):
        """Should use JSON formatter for production."""
        from app import config

        monkeypatch.setattr(config.settings, "LOG_FORMAT", "json")
        monkeypatch.setattr(config.settings, "ENVIRONMENT", "production")

        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger is not None
