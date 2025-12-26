"""
Logging configuration for the worker.
"""

import logging
import sys
from typing import Optional

from ..config import settings


def setup_logging(
    level: str | None = None,
    request_id: str | None = None,
) -> None:
    """
    Set up logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        request_id: Optional request ID to include in all logs.
    """
    log_level = level or settings.LOG_LEVEL
    
    # Configure format
    if request_id:
        fmt = f"%(asctime)s - %(name)s - %(levelname)s - [{request_id}] %(message)s"
    else:
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str, request_id: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with optional request ID context.
    
    Args:
        name: Logger name.
        request_id: Optional request ID for context.
        
    Returns:
        Configured logger.
    """
    logger = logging.getLogger(name)
    
    if request_id:
        # Add request ID to all log messages via a filter
        class RequestIdFilter(logging.Filter):
            def filter(self, record):
                record.request_id = request_id
                return True
        
        logger.addFilter(RequestIdFilter())
    
    return logger

