"""Test coverage for missing lines in observability/logging.py (87% → 100%)."""

import json
import logging
from unittest.mock import Mock, patch

from app.infrastructure.observability.logging import (
    ConsoleFormatter,
    JSONFormatter,
    clear_log_context,
    set_log_context,
)


class TestJSONFormatterContextVariables:
    """Test JSONFormatter with context variables set (lines 80, 82, 84)."""

    def test_format_with_request_id(self):
        """Test JSONFormatter includes request_id when set (line 80)."""
        formatter = JSONFormatter()
        set_log_context(request_id="test-req-123")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["request_id"] == "test-req-123"
        clear_log_context()

    def test_format_with_user_id(self):
        """Test JSONFormatter includes user_id when set (line 82)."""
        formatter = JSONFormatter()
        set_log_context(user_id="user-456")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["user_id"] == "user-456"
        clear_log_context()

    def test_format_with_tenant_id(self):
        """Test JSONFormatter includes tenant_id when set (line 84)."""
        formatter = JSONFormatter()
        set_log_context(tenant_id="tenant-789")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["tenant_id"] == "tenant-789"
        clear_log_context()

    def test_format_with_all_context(self):
        """Test JSONFormatter with all context variables set."""
        formatter = JSONFormatter()
        set_log_context(
            request_id="req-123", user_id="user-456", tenant_id="tenant-789"
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["request_id"] == "req-123"
        assert data["user_id"] == "user-456"
        assert data["tenant_id"] == "tenant-789"
        clear_log_context()


class TestJSONFormatterOpenTelemetry:
    """Test JSONFormatter with OpenTelemetry trace context (lines 91-95)."""

    def test_format_with_opentelemetry_span(self):
        """Test JSONFormatter includes trace context when OpenTelemetry available."""
        formatter = JSONFormatter()

        # Mock OpenTelemetry span
        mock_span_context = Mock()
        mock_span_context.trace_id = 0x12345678901234567890123456789012
        mock_span_context.span_id = 0x1234567890123456

        mock_span = Mock()
        mock_span.is_recording.return_value = True
        mock_span.get_span_context.return_value = mock_span_context

        # Patch at the import location (inside the try block)
        with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            result = formatter.format(record)
            data = json.loads(result)

            assert "trace_id" in data
            assert "span_id" in data
            assert data["trace_id"] == "12345678901234567890123456789012"
            assert data["span_id"] == "1234567890123456"

    def test_format_without_opentelemetry(self):
        """Test JSONFormatter handles missing OpenTelemetry gracefully."""
        formatter = JSONFormatter()

        # Test with a span that is not recording
        mock_span = Mock()
        mock_span.is_recording.return_value = False

        with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            result = formatter.format(record)
            data = json.loads(result)

            # Should not include trace context when span is not recording
            assert "trace_id" not in data
            assert "span_id" not in data


class TestJSONFormatterException:
    """Test JSONFormatter with exception info (line 103)."""

    def test_format_with_exception(self):
        """Test JSONFormatter includes exception info when present."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=exc_info,
            )

            result = formatter.format(record)
            data = json.loads(result)

            assert "exception" in data
            assert "ValueError" in data["exception"]
            assert "Test error" in data["exception"]


class TestConsoleFormatterContextVariables:
    """Test ConsoleFormatter with context variables (lines 133, 137, 141)."""

    def test_format_with_request_id_prefix(self):
        """Test ConsoleFormatter includes request_id in prefix (line 133)."""
        formatter = ConsoleFormatter()
        set_log_context(request_id="test-req-123456789")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        # Should include first 8 chars of request_id
        assert "[test-req" in result
        clear_log_context()

    def test_format_with_tenant_id_prefix(self):
        """Test ConsoleFormatter includes tenant_id in prefix (line 137)."""
        formatter = ConsoleFormatter()
        set_log_context(tenant_id="tenant-789012345")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        # Should include first 8 chars of tenant_id with T: prefix
        assert "[T:tenant-7" in result
        clear_log_context()

    def test_format_with_both_ids_prefix(self):
        """Test ConsoleFormatter with both request and tenant IDs (lines 133, 137, 141)."""
        formatter = ConsoleFormatter()
        set_log_context(request_id="req-12345678901234", tenant_id="ten-98765432109876")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        # Should include both prefixes
        assert "[req-1234" in result
        assert "[T:ten-987" in result
        clear_log_context()


class TestConsoleFormatterException:
    """Test ConsoleFormatter with exception info (line 150)."""

    def test_format_with_exception(self):
        """Test ConsoleFormatter includes exception traceback when present."""
        formatter = ConsoleFormatter()

        try:
            raise RuntimeError("Test runtime error")
        except RuntimeError:
            import sys

            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

            result = formatter.format(record)

            # Should include traceback
            assert "RuntimeError" in result
            assert "Test runtime error" in result
            assert "Traceback" in result
