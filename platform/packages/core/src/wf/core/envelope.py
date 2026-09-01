"""The wire-contract reply envelope (wire-contract RFC §4–§5).

Every queryable *request* on the bus is one shape::

    {"req_id": "<uuidv7>", "client_id": "<who>"?, "args": {...}}

and every *reply* is one tagged union with exactly three branches::

    {"ok": True,  "value": {...}}          # answered now
    {"ok": True,  "goal": {...}}           # accepted; follow the keys inside
    {"ok": False, "error": {"code", "reason", "detail"?, "retryable"?}}

``req_id`` is client-minted (UUIDv7) on every request so resubmission after
a dropped reply is idempotent: a provider that has already handled a
``req_id`` replies with the original outcome (:class:`RecentReplies`)
instead of re-executing. The ``goal`` branch adopts the ``req_id`` as the
goal id for the same reason.

``code`` comes from the closed :data:`CODES` enum — adding a code is an
ADR-level event. ``reason`` comes from a per-contract list registered in
the contract package (``ERROR_REASONS``); ``detail`` is human-oriented and
never parsed; ``retryable`` lets a generic client retry without domain
knowledge.

The envelope applies to command/request queryables (``cmd/*``, actions).
Retained keys answer queries with the *identical* payload they publish —
reads are not enveloped (RFC §3.1).
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field

import uuid6

from .codec import decode, encode

#: Closed error-code enum (RFC §5). Additions are ADR-level events.
CODES = (
    "invalid",      # request malformed / fails validation
    "conflict",     # valid but conflicts with current holder/state
    "busy",         # one-active-goal / try later
    "unavailable",  # serving party absent (incl. no reply at all)
    "not_found",    # referent unknown
    "cancelled",    # terminated by cancel / Hold / Stop
    "safety",       # terminated by the safety chain (reported, never implemented)
    "internal",     # provider fault
)


def new_req_id() -> str:
    return str(uuid6.uuid7())


@dataclass
class WireError:
    """The ``error`` branch payload."""

    code: str
    reason: str
    detail: str | None = None
    retryable: bool = False

    def __post_init__(self) -> None:
        if self.code not in CODES:
            raise ValueError(f"unknown_code:{self.code}")

    def to_wire(self) -> dict:
        d: dict = {"code": self.code, "reason": self.reason}
        if self.detail is not None:
            d["detail"] = self.detail
        if self.retryable:
            d["retryable"] = True
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "WireError":
        code = d.get("code", "internal")
        return cls(
            code=code if code in CODES else "internal",
            reason=str(d.get("reason", "unknown")),
            detail=d.get("detail"),
            retryable=bool(d.get("retryable", False)),
        )

    def __str__(self) -> str:
        s = f"{self.code}:{self.reason}"
        return s if self.detail is None else f"{s}:{self.detail}"


@dataclass
class Goal:
    """The ``goal`` branch payload — pure protocol, zero domain content."""

    goal_id: str
    state: str  # "queued" | "running"
    feedback_key: str
    result_key: str
    cancel_key: str
    result_ttl_s: float = 60.0

    def to_wire(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "state": self.state,
            "feedback_key": self.feedback_key,
            "result_key": self.result_key,
            "cancel_key": self.cancel_key,
            "result_ttl_s": float(self.result_ttl_s),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "Goal":
        return cls(
            goal_id=d["goal_id"],
            state=str(d.get("state", "running")),
            feedback_key=d["feedback_key"],
            result_key=d["result_key"],
            cancel_key=d["cancel_key"],
            result_ttl_s=float(d.get("result_ttl_s", 60.0)),
        )


@dataclass
class Request:
    """The one request shape. ``client_id`` is protocol (the lease check
    needs it) and optional for ungated operations."""

    req_id: str
    args: dict = field(default_factory=dict)
    client_id: str | None = None

    @classmethod
    def new(cls, args: dict | None = None, *, client_id: str | None = None) -> "Request":
        return cls(req_id=new_req_id(), args=dict(args or {}), client_id=client_id)

    def to_wire(self) -> dict:
        d: dict = {"req_id": self.req_id, "args": dict(self.args)}
        if self.client_id is not None:
            d["client_id"] = self.client_id
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "Request":
        if not isinstance(d, dict) or "req_id" not in d:
            raise ValueError("bad_request:missing req_id")
        args = d.get("args", {})
        if not isinstance(args, dict):
            raise ValueError("bad_request:args must be a mapping")
        return cls(req_id=str(d["req_id"]), args=args, client_id=d.get("client_id"))


@dataclass
class Reply:
    """A parsed reply envelope: exactly one of ``value`` / ``goal`` / ``error``."""

    ok: bool
    value: dict | None = None
    goal: Goal | None = None
    error: WireError | None = None

    @classmethod
    def from_wire(cls, d: dict) -> "Reply":
        if not isinstance(d, dict) or "ok" not in d:
            raise ValueError("bad_envelope:missing ok")
        if d["ok"]:
            if "goal" in d:
                return cls(ok=True, goal=Goal.from_wire(d["goal"]))
            value = d.get("value", {})
            if not isinstance(value, dict):
                raise ValueError("bad_envelope:value must be a mapping")
            return cls(ok=True, value=value)
        return cls(ok=False, error=WireError.from_wire(d.get("error") or {}))


# ── reply builders (server side) ─────────────────────────────────────────


def ok_value(value: dict | None = None) -> dict:
    """``value`` is always present on ok — ``{}`` when there is nothing to say."""
    return {"ok": True, "value": dict(value or {})}


def ok_goal(goal: Goal) -> dict:
    return {"ok": True, "goal": goal.to_wire()}


def fail(code: str, reason: str, detail: str | None = None, *, retryable: bool = False) -> dict:
    return {"ok": False, "error": WireError(code, reason, detail, retryable).to_wire()}


def parse_request(query) -> Request:
    """Decode a query's payload into a :class:`Request`; raises ``ValueError``
    (reply ``fail("invalid", "bad_request", …)``)."""
    payload = query.payload
    if payload is None:
        raise ValueError("bad_request:empty payload")
    return Request.from_wire(decode(payload))


class RecentReplies:
    """Per-provider ``req_id -> wire reply`` ring for idempotent resubmission."""

    def __init__(self, maxlen: int = 256) -> None:
        self._lock = threading.Lock()
        self._order: deque[str] = deque(maxlen=maxlen)
        self._replies: dict[str, dict] = {}

    def get(self, req_id: str) -> dict | None:
        with self._lock:
            return self._replies.get(req_id)

    def put(self, req_id: str, reply: dict) -> None:
        with self._lock:
            if req_id in self._replies:
                self._replies[req_id] = reply
                return
            if len(self._order) == self._order.maxlen:
                evicted = self._order[0]
                self._replies.pop(evicted, None)
            self._order.append(req_id)
            self._replies[req_id] = reply


# ── client side ──────────────────────────────────────────────────────────


class EnvelopeError(Exception):
    """The ``error`` branch (or a transport-level failure), as an exception."""

    def __init__(self, error: WireError):
        super().__init__(str(error))
        self.error = error

    @property
    def code(self) -> str:
        return self.error.code

    @property
    def reason(self) -> str:
        return self.error.reason

    @property
    def retryable(self) -> bool:
        return self.error.retryable


def request(
    session,
    key: str,
    args: dict | None = None,
    *,
    client_id: str | None = None,
    req_id: str | None = None,
    timeout_s: float = 5.0,
) -> Reply:
    """One enveloped query. Returns the parsed :class:`Reply`; no reply at
    all becomes ``error {code: unavailable, reason: no_reply}`` (absence is a
    first-class outcome), an unparsable reply ``internal:bad_envelope``."""
    req = Request(req_id=req_id or new_req_id(), args=dict(args or {}), client_id=client_id)
    for reply in session.get(key, payload=encode(req.to_wire()), timeout=timeout_s):
        if reply.ok is None:
            continue
        try:
            return Reply.from_wire(decode(reply.ok.payload))
        except Exception as exc:  # noqa: BLE001
            return Reply(ok=False, error=WireError("internal", "bad_envelope", repr(exc)))
    return Reply(ok=False, error=WireError("unavailable", "no_reply", key, retryable=True))


def call(
    session,
    key: str,
    args: dict | None = None,
    *,
    client_id: str | None = None,
    req_id: str | None = None,
    timeout_s: float = 5.0,
    result_timeout_s: float | None = 300.0,
) -> dict:
    """The branch-agnostic client: returns the ``value`` dict, transparently
    follows a ``goal`` to its result (which is recursively the envelope),
    raises :class:`EnvelopeError` otherwise. An operation can move from
    sync to goal-shaped without breaking a single caller."""
    reply = request(
        session, key, args, client_id=client_id, req_id=req_id, timeout_s=timeout_s
    )
    if reply.ok and reply.value is not None:
        return reply.value
    if reply.ok and reply.goal is not None:
        return _follow(session, reply.goal, result_timeout_s)
    raise EnvelopeError(reply.error or WireError("internal", "bad_envelope"))


def _follow(session, goal: Goal, result_timeout_s: float | None) -> dict:
    """Wait for the result of an accepted goal: subscribe the retained result
    key first, then seed with a query — deltas win over the seed."""
    done = threading.Event()
    outcome: dict = {}

    def _deliver(wire: dict) -> None:
        if not done.is_set():
            outcome["reply"] = wire
            done.set()

    sub = session.declare_subscriber(
        goal.result_key, lambda s: _deliver(decode(s.payload))
    )
    try:
        if not done.is_set():
            for reply in session.get(goal.result_key, timeout=5.0):
                if reply.ok is not None:
                    wire = decode(reply.ok.payload)
                    # An action server may answer "no result yet" — only a
                    # well-formed envelope counts as the outcome.
                    if isinstance(wire, dict) and "ok" in wire:
                        _deliver(wire)
                    break
        if not done.wait(result_timeout_s):
            raise EnvelopeError(
                WireError("unavailable", "result_timeout", goal.goal_id, retryable=True)
            )
    finally:
        try:
            sub.undeclare()
        except Exception:  # noqa: BLE001
            pass
    parsed = Reply.from_wire(outcome["reply"])
    if parsed.ok and parsed.value is not None:
        return parsed.value
    raise EnvelopeError(parsed.error or WireError("internal", "bad_envelope"))
