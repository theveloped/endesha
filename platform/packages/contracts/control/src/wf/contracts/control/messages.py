"""`control` contract wire messages (moved verbatim from the arm contract when
the lease became cell-level). Timestamps are int nanoseconds."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ControlOwner:
    """Current holder of the control lease."""

    client_id: str
    user: str
    granted_at: int
    expires_at: int

    def to_wire(self) -> dict:
        return {
            "client_id": self.client_id,
            "user": self.user,
            "granted_at": int(self.granted_at),
            "expires_at": int(self.expires_at),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ControlOwner":
        return cls(
            client_id=d["client_id"],
            user=d["user"],
            granted_at=d["granted_at"],
            expires_at=d["expires_at"],
        )


@dataclass
class AcquireControl:
    """``cmd/acquire`` envelope ``args`` — the acquiring ``client_id``
    travels top-level in the envelope request (wire-contract RFC §4.1).
    ``cmd/release`` takes empty args (the ``client_id`` is the request's).
    On success both reply ``value: ControlOwnerState``; a denied acquire is
    ``conflict:held_by:<user>``, a release by a non-holder
    ``conflict:not_holder``."""

    user: str

    def to_wire(self) -> dict:
        return {"user": self.user}

    @classmethod
    def from_wire(cls, d: dict) -> "AcquireControl":
        return cls(user=d["user"])


#: Registered envelope error ``reason`` values (wire-contract RFC §5).
ERROR_REASONS = ("bad_request", "held_by", "not_holder")


@dataclass
class ControlOwnerState:
    """Payload of ``state/owner`` (latest-wins)."""

    t: int
    owner: ControlOwner | None = None

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "owner": None if self.owner is None else self.owner.to_wire(),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ControlOwnerState":
        owner = d.get("owner")
        return cls(
            t=d["t"], owner=None if owner is None else ControlOwner.from_wire(owner)
        )
