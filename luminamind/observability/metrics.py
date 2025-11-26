from __future__ import annotations

import functools
import logging
import os
import time
from typing import Any, Callable, Optional

from prometheus_client import Counter, Histogram, start_http_server

logger = logging.getLogger(__name__)

# Tool metrics
TOOL_INVOCATIONS = Counter(
    "luminamind_tool_invocations_total",
    "Total tool invocations",
    ["tool_name", "status"],  # status: success|error
)

TOOL_DURATION = Histogram(
    "luminamind_tool_duration_seconds",
    "Tool execution duration",
    ["tool_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

TOOL_ERRORS = Counter(
    "luminamind_tool_errors_total",
    "Tool execution errors",
    ["tool_name", "error_type"],
)


def monitor_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to capture metrics around tool execution."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        tool_name = func.__name__
        start_time = time.time()
        status = "success"
        error_type: Optional[str] = None
        try:
            result = func(*args, **kwargs)
            if isinstance(result, dict) and result.get("error"):
                status = "error"
                error_type = "error_result"
            return result
        except Exception as exc:
            status = "error"
            error_type = type(exc).__name__
            raise
        finally:
            TOOL_INVOCATIONS.labels(tool_name=tool_name, status=status).inc()
            TOOL_DURATION.labels(tool_name=tool_name).observe(time.time() - start_time)
            if status == "error":
                TOOL_ERRORS.labels(tool_name=tool_name, error_type=error_type or "unknown").inc()

    return wrapper


def start_metrics_server(port: Optional[int] = None) -> None:
    """Start the Prometheus metrics HTTP server if not already running."""
    disabled = os.getenv("METRICS_DISABLED", "").lower() in {"1", "true", "yes"}
    if disabled:
        logger.info("Metrics server disabled via METRICS_DISABLED")
        return

    resolved_port = port
    env_port = os.getenv("METRICS_PORT")
    if resolved_port is None and env_port:
        try:
            resolved_port = int(env_port)
        except ValueError:
            logger.warning("Invalid METRICS_PORT value %s; using default 9090", env_port)

    if resolved_port is None:
        resolved_port = 9090

    try:
        start_http_server(resolved_port)
        logger.info("Metrics server started on port %s", resolved_port)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to start metrics server: %s", exc)


__all__ = [
    "monitor_tool",
    "start_metrics_server",
    "TOOL_INVOCATIONS",
    "TOOL_DURATION",
    "TOOL_ERRORS",
]
