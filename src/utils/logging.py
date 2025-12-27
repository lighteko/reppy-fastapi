"""Logging configuration and utilities."""

import logging
import sys
from contextvars import ContextVar
from typing import Any

from src.config import Settings

# Context variable for request-scoped logging
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """Filter that adds request_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id to the record."""
        record.request_id = _request_id_var.get()
        return True


def configure_logging(settings: Settings | None = None) -> None:
    """
    Configure application logging.
    
    Args:
        settings: Application settings (optional).
    """
    level = logging.INFO
    if settings:
        level = getattr(logging, settings.log_level, logging.INFO)

    # Create formatter with request_id
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add stream handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("oci").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def set_request_id(request_id: str) -> None:
    """
    Set the current request ID for logging context.
    
    Args:
        request_id: Request identifier.
    """
    _request_id_var.set(request_id)


def get_request_id() -> str:
    """Get the current request ID."""
    return _request_id_var.get()


def get_request_logger(name: str) -> logging.Logger:
    """
    Get a logger for the given name.
    
    Args:
        name: Logger name.
        
    Returns:
        Configured logger.
    """
    return logging.getLogger(name)


class LatencyLogger:
    """Context manager for logging operation latency."""

    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        level: int = logging.INFO,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize latency logger.
        
        Args:
            logger: Logger instance.
            operation: Operation name for logging.
            level: Log level.
            extra: Extra data to log.
        """
        self._logger = logger
        self._operation = operation
        self._level = level
        self._extra = extra or {}
        self._start_time: float = 0

    def __enter__(self) -> "LatencyLogger":
        """Start timing."""
        import time
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Log latency."""
        import time
        elapsed_ms = (time.perf_counter() - self._start_time) * 1000
        
        if exc_type is not None:
            self._logger.error(
                f"{self._operation} failed after {elapsed_ms:.2f}ms: {exc_val}",
                extra=self._extra,
            )
        else:
            self._logger.log(
                self._level,
                f"{self._operation} completed in {elapsed_ms:.2f}ms",
                extra=self._extra,
            )


def latency_log(
    logger: logging.Logger,
    operation: str,
    level: int = logging.INFO,
    extra: dict[str, Any] | None = None,
) -> LatencyLogger:
    """
    Create a latency logging context manager.
    
    Args:
        logger: Logger instance.
        operation: Operation name.
        level: Log level.
        extra: Extra data to log.
        
    Returns:
        LatencyLogger context manager.
    """
    return LatencyLogger(logger, operation, level, extra)

