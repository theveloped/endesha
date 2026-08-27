"""Shared dio-contract core + backend seam (program-layer RFC §2.3)."""

from .backend import DioBackend
from .core import DioCore, load_dio_resource

__all__ = ["DioBackend", "DioCore", "load_dio_resource"]
