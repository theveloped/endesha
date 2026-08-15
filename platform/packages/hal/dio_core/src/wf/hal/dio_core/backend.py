"""The ``DioBackend`` seam.

:class:`~wf.hal.dio_core.core.DioCore` serves the whole dio contract (channel
table, force overlay, lease check, publish-on-change + keepalive). A backend
only moves RAW values to/from wherever they physically live: the arm's IO bank
over the bus, an in-memory table for the simulator, a fieldbus later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from wf.contracts.dio.messages import ChannelDef


class DioBackend(ABC):
    @abstractmethod
    def start(self, core) -> None:
        """Connect / start whatever feeds :meth:`read`. Backends that learn of
        input changes asynchronously call ``core.notify()`` to publish sooner
        than the next poll."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release resources (idempotent)."""

    @abstractmethod
    def read(self) -> dict[str, bool | float]:
        """RAW values (before scale/offset) keyed by channel name for every
        channel the backend currently knows. Channels absent from the dict
        keep their last value in the core (an unwired channel simply never
        appears — the simulator returns only what was written/scripted)."""

    @abstractmethod
    def write(self, channel: ChannelDef, raw) -> None:
        """Write a RAW output value. Raise on failure (the core answers the
        command with the exception text)."""
