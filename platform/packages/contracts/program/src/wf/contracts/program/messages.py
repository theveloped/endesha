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
    hmi: dict[str, str] = field(default_factory=dict)  # event -> operator label
    graph: dict = field(default_factory=dict)  # states/transitions/triggers/source (wf.program.graph)

    def to_wire(self) -> dict:
        return {
            "name": self.name,
            "roles": dict(self.roles),
            "params": dict(self.params),
            "doc": self.doc,
            "path": self.path,
            "error": self.error,
            "hmi": dict(self.hmi),
            "graph": dict(self.graph),
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
            hmi=dict(d.get("hmi") or {}),
            graph=dict(d.get("graph") or {}),
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

    Debug aid: ``waiting_for`` lists, for the active states, what would move
    the program on — ``{"kind": "channel", "role", "channel", "edge",
    "event"}``, ``{"kind": "timer", "state", "seconds", "event"}``,
    ``{"kind": "event", "event", "target"}`` (any accepted event, e.g. from
    an action's ``emit`` or ``cmd/event``).
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
    waiting_for: list[dict] = field(default_factory=list)

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
            "waiting_for": [dict(w) for w in self.waiting_for],
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
            waiting_for=[dict(w) for w in d.get("waiting_for") or []],
        )


@dataclass
class LogLine:
    """One ``program/log`` entry. ``level`` is info|warning|error; ``source``
    is the program name or ``runner``."""

    t: int
    level: str
    source: str
    message: str

    def to_wire(self) -> dict:
        return {"t": int(self.t), "level": self.level, "source": self.source, "message": self.message}

    @classmethod
    def from_wire(cls, d: dict) -> "LogLine":
        return cls(t=int(d["t"]), level=d.get("level", "info"), source=d.get("source", ""), message=d.get("message", ""))


@dataclass
class SourceReply:
    """``programs/cmd/source`` envelope ``value``."""

    name: str = ""
    path: str = ""
    text: str = ""

    def to_wire(self) -> dict:
        return {"name": self.name, "path": self.path, "text": self.text}

    @classmethod
    def from_wire(cls, d: dict) -> "SourceReply":
        return cls(name=str(d.get("name", "")), path=str(d.get("path", "")), text=str(d.get("text", "")))


@dataclass
class SaveRequest:
    """``programs/cmd/save``: write ``text`` to ``<programs_dir>/<file>`` (a
    bare module file name like ``demo_pick.py``; created when missing), then
    rescan. The reply carries the resulting catalog entry so an import error
    shows up immediately in the editor."""

    file: str
    text: str

    def to_wire(self) -> dict:
        return {"file": self.file, "text": self.text}

    @classmethod
    def from_wire(cls, d: dict) -> "SaveRequest":
        return cls(file=d["file"], text=d["text"])


@dataclass
class SaveReply:
    """``programs/cmd/save`` envelope ``value``: the rescanned catalog entry
    (its ``error`` reports an import failure — the file is written anyway)."""

    entry: CatalogEntry

    def to_wire(self) -> dict:
        return {"entry": self.entry.to_wire()}

    @classmethod
    def from_wire(cls, d: dict) -> "SaveReply":
        return cls(entry=CatalogEntry.from_wire(d["entry"]))


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


#: Registered envelope error ``reason`` values (wire-contract RFC §5).
ERROR_REASONS = (
    "bad_request",
    "invalid_in_state",
    "no_program_loaded",
    "no_program_running",
    "unknown_program",
    "unknown_event",
    "unknown_params",
    "program_broken",
    "bind",
    "bad_file",
    "load_failed",
    "save_failed",
    "delete_failed",
    "command_failed",
    "event_failed",
    "source_failed",
)
