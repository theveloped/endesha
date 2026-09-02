"""`supervisor` contract wire messages (wire-contract RFC).

First typed slice of the supervisor surface: the ``cmd/set_source`` args.
The retained payloads (descriptor, devices, log/event rings) are still
ad-hoc dicts assembled in the service — typing them is the remainder of
architecture seam #3, scheduled with the codegen step.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SetSource:
    """``cmd/set_source`` envelope ``args``: cold-switch one device."""

    device_id: str
    source: str  # a declared mode, or "off"

    def to_wire(self) -> dict:
        return {"device_id": self.device_id, "source": self.source}

    @classmethod
    def from_wire(cls, d: dict) -> "SetSource":
        return cls(device_id=d["device_id"], source=d["source"])


#: Registered envelope error ``reason`` values (wire-contract RFC §5).
ERROR_REASONS = (
    "bad_request",
    "unknown_device",
    "provided_by",
    "no_source",
    "spawn_failed",
)
