"""Structured logging configuration."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, override

from outreach_tool.core.config import get_config


class JSONFormatter(logging.Formatter):
    """EMIT structured JSON log records."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_data.update(record.extra)  # type: ignore[attr-defined]
        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, default=str)


def setup_logging(
    *,
    level: str | None = None,
    log_file: Path | None = None,
    json_output: bool = False,
) -> logging.Logger:
    """Configure logging for the application.

    Args:
        level: Logging level (defaults to config value).
        log_file: Optional file to write logs to.
        json_output: Whether to format logs as JSON.

    Returns:
        The configured root logger for this package.
    """
    config = get_config()
    effective_level = (level or config.log_level).upper()

    # Configure root logger
    logger = logging.getLogger("outreach_tool")
    logger.setLevel(effective_level)
    logger.handlers = []  # Clear existing handlers

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # If level is DEBUG, show everything on console with full format
    # Otherwise, only show WARNING and above on console with minimal format
    if effective_level == "DEBUG":
        console_handler.setLevel(logging.DEBUG)
        if json_output:
            console_formatter = JSONFormatter()
        else:
            console_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
    else:
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Optional file handler (always gets the full effective_level)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(effective_level)
        if json_output:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
