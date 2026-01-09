# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Structured logging configuration.

Provides JSON-formatted logs with trace correlation,
context enrichment, and multiple output handlers.
"""

import logging
import sys
from contextvars import ContextVar
from datetime import datetime, UTC
from typing import Any, Optional
import json

from app.config import settings

# Context variables for log enrichment
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_tenant_id: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)


def set_log_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> None:
    """Set context variables for log enrichment."""
    if request_id:
        _request_id.set(request_id)
    if user_id:
        _user_id.set(user_id)
    if tenant_id:
        _tenant_id.set(tenant_id)


def clear_log_context() -> None:
    """Clear all log context variables."""
    _request_id.set(None)
    _user_id.set(None)
    _tenant_id.set(None)


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter with context enrichment.
    
    Produces structured logs suitable for log aggregation systems
    like ELK, Loki, or CloudWatch.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
        }
        
        # Add location info
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }
        
        # Add context from context variables
        request_id = _request_id.get()
        user_id = _user_id.get()
        tenant_id = _tenant_id.get()
        
        if request_id:
            log_data["request_id"] = request_id
        if user_id:
            log_data["user_id"] = user_id
        if tenant_id:
            log_data["tenant_id"] = tenant_id
        
        # Add trace context if available
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span and span.is_recording():
                ctx = span.get_span_context()
                log_data["trace_id"] = format(ctx.trace_id, "032x")
                log_data["span_id"] = format(ctx.span_id, "016x")
        except ImportError:
            pass
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_data["extra"] = record.extra_fields
        
        return json.dumps(log_data, default=str)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable console formatter with colors.
    
    Used in development for easier reading.
    """
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console."""
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Build prefix with context
        prefix_parts = []
        
        request_id = _request_id.get()
        if request_id:
            prefix_parts.append(f"[{request_id[:8]}]")
        
        tenant_id = _tenant_id.get()
        if tenant_id:
            prefix_parts.append(f"[T:{tenant_id[:8]}]")
        
        prefix = " ".join(prefix_parts)
        if prefix:
            prefix += " "
        
        # Format message
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        level = f"{color}{record.levelname:8}{self.RESET}"
        
        message = f"{timestamp} | {level} | {record.name} | {prefix}{record.getMessage()}"
        
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message


class ContextLogger(logging.LoggerAdapter):
    """
    Logger adapter that adds extra context to all log messages.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("User created", extra_fields={"user_id": "123"})
    """
    
    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """Process log message and add extra context."""
        extra = kwargs.get("extra", {})
        
        # Add extra_fields if provided
        extra_fields = kwargs.pop("extra_fields", None)
        if extra_fields:
            extra["extra_fields"] = extra_fields
        
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging() -> None:
    """
    Configure application logging.
    
    Should be called once during application startup.
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create handler based on environment
    handler = logging.StreamHandler(sys.stdout)
    
    if settings.ENVIRONMENT == "production" or settings.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())
    
    root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> ContextLogger:
    """
    Get a context-aware logger.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        ContextLogger instance
    """
    return ContextLogger(logging.getLogger(name), {})


# Pre-configured loggers for common modules
class Loggers:
    """Pre-configured loggers for common modules."""
    
    app = get_logger("app")
    api = get_logger("app.api")
    db = get_logger("app.database")
    auth = get_logger("app.auth")
    tasks = get_logger("app.tasks")
