"""Minimal, dependency-free logging setup shared by the whole app."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, writing to stdout (what Render reads)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Ultralytics is extremely chatty at INFO level on every prediction.
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
