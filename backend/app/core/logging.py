"""
Centralised logging configuration for the PRMS backend.

- Development: human-readable text format with colours (via uvicorn defaults).
- Production:  JSON format for log aggregation pipelines (e.g. CloudWatch, Datadog).

Call `configure_logging()` once inside the lifespan context manager before the
first request is processed.
"""

import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]


def configure_logging(log_level: str, environment: str) -> None:
    """
    Configure the root logger and silence noisy third-party loggers.

    Args:
        log_level:   One of DEBUG / INFO / WARNING / ERROR / CRITICAL.
        environment: The current runtime environment string.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove any handlers added by libraries before we configure ours.
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if environment == "production":
        formatter: logging.Formatter = _JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
        # Suppress noisy uvicorn access logs in production.
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper — returns a named logger."""
    return logging.getLogger(name)


class _JsonFormatter(jsonlogger.JsonFormatter):  # type: ignore[misc]
    """
    Extends python-json-logger to always emit a canonical set of fields.
    """

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger", record.name)
