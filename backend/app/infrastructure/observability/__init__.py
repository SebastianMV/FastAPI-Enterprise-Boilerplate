# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Observability package - telemetry, logging, metrics."""

from app.infrastructure.observability.telemetry import (
    AppMetrics,
    add_span_attributes,
    get_current_span,
    get_meter,
    get_tracer,
    inject_trace_context,
    setup_telemetry,
    span_context,
    traced,
)

__all__ = [
    "AppMetrics",
    "add_span_attributes",
    "get_current_span",
    "get_meter",
    "get_tracer",
    "inject_trace_context",
    "setup_telemetry",
    "span_context",
    "traced",
]
