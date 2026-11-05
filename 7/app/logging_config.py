import logging
import os
from pathlib import Path
import traceback

from dotenv import load_dotenv


class SafeExceptionFormatter(logging.Formatter):
    """Keep traceback locations without exposing SQL parameters or credentials."""

    def format(self, record):
        # Another handler may have cached an unsanitized exception rendering.
        previous_exception_text = record.exc_text
        record.exc_text = None
        try:
            return super().format(record)
        finally:
            record.exc_text = previous_exception_text

    def formatException(self, exc_info):
        exception_type, _, trace = exc_info
        # Source lines can contain hard-coded secrets, so keep locations only.
        frames = "".join(
            f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}\n'
            for frame in traceback.extract_tb(trace)
        )
        return (
            f"Traceback (most recent call last):\n{frames}"
            f"{exception_type.__name__}: exception message omitted for security"
        )


def configure_logging() -> None:
    """Configure this application only; leave Uvicorn and other loggers alone."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    invalid_level = level not in valid_levels
    if invalid_level:
        level = "INFO"

    logger = logging.getLogger(__package__)
    logger.setLevel(level)
    logger.propagate = False

    # Repeated configuration must not add duplicate console handlers.
    handler = next(
        (item for item in logger.handlers if item.name == "lesson7.console"), None
    )
    if handler is None:
        handler = logging.StreamHandler()
        handler.set_name("lesson7.console")
        logger.addHandler(handler)
    handler.setFormatter(SafeExceptionFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))

    if invalid_level:
        logger.warning("Invalid LOG_LEVEL; using INFO")
