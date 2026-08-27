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
    """``cmd/acquire`` request."""

    client_id: str
    user: str

    def to_wire(self) -> dict:
        return {"client_id": self.client_id, "user": self.user}

    @classmethod
    def from_wire(cls, d: dict) -> "AcquireControl":
        return cls(client_id=d["client_id"], user=d["user"])


@dataclass
class ReleaseControl:
    """``cmd/release`` request."""

    client_id: str

    def to_wire(self) -> dict:
        return {"client_id": self.client_id}

    @classmethod
    def from_wire(cls, d: dict) -> "ReleaseControl":
        return cls(client_id=d["client_id"])


@dataclass
class ControlAck:
    """Reply payload for the lease queryables. ``owner`` is the holder after
    the request (the requester on grant/renew; the blocking holder on denial)."""

    ok: bool
    owner: ControlOwner | None = None
    error: str | None = None

    def to_wire(self) -> dict:
        return {
            "ok": bool(self.ok),
            "owner": None if self.owner is None else self.owner.to_wire(),
            "error": self.error,
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ControlAck":
        owner = d.get("owner")
        return cls(
            ok=d["ok"],
            owner=None if owner is None else ControlOwner.from_wire(owner),
            error=d.get("error"),
        )


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
