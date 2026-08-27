"""The backend seam of a channel device: raw values in, raw values out."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ChannelsBackend(ABC):
    def points(self) -> list[tuple[str, dict]]:
        """The provider's raw inventory as ``[(kind_or_type, address), …]``
        (every pin of a bank, every tag of a PLC). The core synthesizes an
        ``auto`` channel for each point no cell channel maps to, so the raw
        device stays visible. Default: none."""
        return []

    @abstractmethod
    def start(self, core) -> None:
        """Connect / start whatever feeds :meth:`read`. Backends that learn of
        changes asynchronously call ``core.notify()``."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release resources (idempotent)."""

    @abstractmethod
    def read(self) -> dict[str, object]:
        """RAW values keyed by channel name for every channel the backend
        currently knows; absent names keep their last value in the core."""

    @abstractmethod
    def write(self, channel, raw) -> None:
        """Write a RAW value to a writable channel; raise on failure."""
