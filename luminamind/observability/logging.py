from __future__ import annotations

import logging
import os
import sys
from typing import Optional

import structlog


def setup_logging(level: Optional[str] = None, json_format: Optional[bool] = None) -> structlog.stdlib.BoundLogger:
    """Configure structured logging for the application."""
    resolved_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    use_json = json_format if json_format is not None else os.getenv("LOG_FORMAT", "json").lower() == "json"

    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)

    # Reset existing handlers to avoid duplicate logs when reconfiguring.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if use_json else structlog.dev.ConsoleRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


__all__ = ["setup_logging"]
