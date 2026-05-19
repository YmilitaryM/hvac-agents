"""Structured logging configuration for the HVAC multi-agent system.

Provides JSON formatter for production (container/cloud) and colored console
formatter for development. Call setup_logging() once at bootstrap time.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines for production log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            entry["exc"] = str(record.exc_info[1])
        if hasattr(record, "request_id"):
            entry["req_id"] = record.request_id
        if hasattr(record, "elapsed_ms"):
            entry["elapsed_ms"] = round(record.elapsed_ms, 2)
        return json.dumps(entry, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for local development."""

    COLORS = {
        "DEBUG": "\033[36m",    # cyan
        "INFO": "\033[32m",     # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",    # red
        "CRITICAL": "\033[35m", # magenta
    }
    RESET = "\033[0m"
    GRAY = "\033[90m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        parts = [
            f"{self.GRAY}{ts}{self.RESET}",
            f"{color}{record.levelname:<8}{self.RESET}",
            f"{self.GRAY}[{record.name}]{self.RESET}",
            record.getMessage(),
        ]
        return " ".join(parts)


def setup_logging(
    debug: bool = False,
    log_file: Optional[str] = None,
    json_output: bool = False,
) -> None:
    """Configure Python logging for the HVAC system.

    Args:
        debug: If True, set root logger to DEBUG. Otherwise INFO.
        log_file: Optional file path for log output.
        json_output: If True, use JSON formatter (production). Otherwise colored.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    # Remove any existing handlers to avoid duplicates on re-config
    for h in list(root.handlers):
        root.removeHandler(h)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    if json_output or (not sys.stdout.isatty()):
        console.setFormatter(JSONFormatter())
    else:
        console.setFormatter(ColoredFormatter())
    root.addHandler(console)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        root.addHandler(file_handler)

    # Quiet noisy third-party loggers
    for noisy in ("uvicorn", "httpx", "langchain", "anthropic", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Ensure our loggers are at the right level
    for name in ("hvac", "src"):
        logging.getLogger(name).setLevel(logging.DEBUG if debug else logging.INFO)


class RequestIDFilter(logging.Filter):
    """Inject request_id into log records that have it."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True
