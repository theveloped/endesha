"""`program` contract wire messages. Timestamps int ns."""

from __future__ import annotations

from dataclasses import dataclass, field

# PackML (ISA-TR88.00.02) unit states, as the runner reports them.
UNIT_STATES = (
    "idle",
    "starting",
    "execute",
    "completing",
    "complete",
    "holding",
    "held",
    "unholding",
    "suspending",
    "suspended",
    "unsuspending",
    "stopping",
    "stopped",
    "aborting",
    "aborted",
    "clearing",
    "resetting",
)


@dataclass
class Ack:
    ok: bool
    error: str | None = None

    def to_wire(self) -> dict:
        return {"ok": bool(self.ok), "error": self.error}

    @classmethod
    def from_wire(cls, d: dict) -> "Ack":
        return cls(ok=d["ok"], error=d.get("error"))


@dataclass
class CatalogEntry:
    """One discoverable program. ``error`` is set (and roles/params empty) when
    the module failed to import — the catalog still lists it so the operator
    sees WHY it is missing."""

    name: str
    roles: dict[str, str] = field(default_factory=dict)  # role -> contract
    params: dict = field(default_factory=dict)  # defaults
    doc: str = ""
    path: str = ""
    error: str | None = None

    def to_wire(self) -> dict:
        return {
            "name": self.name,
            "roles": dict(self.roles),
            "params": dict(self.params),
            "doc": self.doc,
            "path": self.path,
            "error": self.error,
        }

    @classmethod
    def from_wire(cls, d: dict) -> "CatalogEntry":
        return cls(
            name=d["name"],
            roles=dict(d.get("roles") or {}),
            params=dict(d.get("params") or {}),
            doc=d.get("doc", ""),
            path=d.get("path", ""),
            error=d.get("error"),
        )


@dataclass
class Catalog:
    t: int
    programs: list[CatalogEntry] = field(default_factory=list)

    def to_wire(self) -> dict:
        return {"t": int(self.t), "programs": [p.to_wire() for p in self.programs]}

    @classmethod
    def from_wire(cls, d: dict) -> "Catalog":
        return cls(
            t=int(d["t"]),
            programs=[CatalogEntry.from_wire(p) for p in d.get("programs") or []],
        )


@dataclass
class LoadRequest:
    """``programs/cmd/load``: pick a program, bind roles to device ids, set
    params. Missing bindings default to the sole device of that contract."""

    name: str
    bindings: dict[str, str] = field(default_factory=dict)  # role -> rid
    params: dict = field(default_factory=dict)

    def to_wire(self) -> dict:
        return {"name": self.name, "bindings": dict(self.bindings), "params": dict(self.params)}

    @classmethod
    def from_wire(cls, d: dict) -> "LoadRequest":
        return cls(
            name=d["name"],
            bindings=dict(d.get("bindings") or {}),
            params=dict(d.get("params") or {}),
        )


@dataclass
class EventRequest:
    """``program/cmd/event``: an external event for the loaded program."""

    event: str
    data: dict = field(default_factory=dict)

    def to_wire(self) -> dict:
        return {"event": self.event, "data": dict(self.data)}

    @classmethod
    def from_wire(cls, d: dict) -> "EventRequest":
        return cls(event=d["event"], data=dict(d.get("data") or {}))


@dataclass
class ProgramState:
    """Payload of ``program/state`` (latest-wins).

    ``unit`` is the PackML state; ``program`` the loaded program name (None
    when nothing is loaded); ``program_states`` the program's active state ids
    (StateChart configuration); ``actions`` the state ids whose action is
    currently running; ``reason`` explains the last Stopped/Aborted.
    """

    t: int
    unit: str
    program: str | None = None
    program_states: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    reason: str | None = None
    params: dict = field(default_factory=dict)
    bindings: dict[str, str] = field(default_factory=dict)
    client_id: str | None = None
    cycle: int = 0

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "unit": self.unit,
            "program": self.program,
            "program_states": list(self.program_states),
            "actions": list(self.actions),
            "reason": self.reason,
            "params": dict(self.params),
            "bindings": dict(self.bindings),
            "client_id": self.client_id,
            "cycle": int(self.cycle),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ProgramState":
        return cls(
            t=int(d["t"]),
            unit=d["unit"],
            program=d.get("program"),
            program_states=list(d.get("program_states") or []),
            actions=list(d.get("actions") or []),
            reason=d.get("reason"),
            params=dict(d.get("params") or {}),
            bindings=dict(d.get("bindings") or {}),
            client_id=d.get("client_id"),
            cycle=int(d.get("cycle", 0)),
        )


@dataclass
class TransitionEvent:
    """One entry of ``program/transitions``: ``scope`` is ``unit`` or
    ``program``; ``event`` is what triggered it."""

    t: int
    scope: str
    source: str | None
    target: str
    event: str | None = None
    detail: str | None = None

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "scope": self.scope,
            "source": self.source,
            "target": self.target,
            "event": self.event,
            "detail": self.detail,
        }

    @classmethod
    def from_wire(cls, d: dict) -> "TransitionEvent":
        return cls(
            t=int(d["t"]),
            scope=d["scope"],
            source=d.get("source"),
            target=d["target"],
            event=d.get("event"),
            detail=d.get("detail"),
        )
