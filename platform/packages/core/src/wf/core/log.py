"""Boring stdlib logging. Structured JSON logging is not phase-1."""

from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_configured = False


def get_logger(name: str) -> logging.Logger:
    """Logger with a single shared stderr handler."""
    global _configured
    if not _configured:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT))
        root = logging.getLogger("wf")
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        root.propagate = False
        _configured = True
    return logging.getLogger(name if name.startswith("wf") else f"wf.{name}")
