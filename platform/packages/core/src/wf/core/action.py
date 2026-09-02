"""Action pattern: goal lifecycle per design Appendix A, on the wire-contract
envelope (RFC §4.2–§4.3, ADR-0013).

Wire protocol (prefix = e.g. ``cell/arm/r1/action``):

- Goal submit (queryable per action name): client GETs ``{prefix}/{name}``
  with an envelope request ``{"req_id", "client_id"?, "args": <goal>}``.
  The goal id is the **adopted req_id** (client-minted UUIDv7), so
  resubmission after a dropped reply is idempotent. Reply branches:

  - accepted: ``{"ok": true, "goal": {goal_id, state, feedback_key,
    result_key, cancel_key, result_ttl_s}}`` — self-describing follow keys.
  - busy: ``{"ok": false, "error": {code: "busy", reason: "goal_active",
    detail: <active goal id>, retryable: true}}`` (one active goal across
    all actions; no queueing; ``on_accept`` not consulted).
  - rejected: the ``on_accept`` reason string ``"head:detail"`` maps onto
    the envelope (``no_control``/``wrong_phase`` → conflict, …).

- Feedback (best-effort pub): ``{prefix}/{goal_id}/feedback``, payload
  ``{"t", "seq", "goal_id", "state", "progress", "detail": dict}``.
- Result (retained: pub + queryable on the same key — the queryable is the
  source of truth): ``{prefix}/{goal_id}/result``; the payload is
  **recursively the envelope**: ``{"ok": true, "value": data}`` on success,
  ``{"ok": false, "error": {code: "cancelled"|"internal", reason:
  "canceled"|"failed"|"aborted", detail}}`` otherwise. A query for an
  expired/never-seen goal replies ``not_found:unknown_goal``; a query for a
  goal still executing gets **no reply** (the client keeps waiting).
- Cancel (one envelope queryable per prefix, shared by all actions):
  ``{prefix}/cancel`` with args ``{"goal_id"}`` → ``value {"state"}`` or
  ``not_found:unknown_goal``.

Server semantics enforced here (HALs cannot diverge):

- One worker thread per :class:`ActionServer`; goals execute strictly
  serially. At most one active (non-terminal) goal across all registered
  actions. No queueing.
- Idempotency: a resubmitted known goal id replies the ``goal`` branch with
  the current state without re-executing — including terminal goals still
  inside the TTL window. Rejected goals are NOT recorded, so a goal id that
  was rejected (e.g. busy) may be resubmitted and re-evaluated.
- The result queryable serves cached results for ``result_ttl_s`` after the
  terminal transition; records are pruned lazily (on goal submit and result
  query). The result is also published once at the terminal transition.
- ``on_execute`` must end the goal via exactly one terminal
  :class:`GoalHandle` method; if it raises, the server calls
  ``handle.fail(error=repr(exc))``.

Driver-restart rule (Appendix A: publish ``aborted {cause: driver_restart}``
for unaccounted goals on restart) is a deliberate no-op in phase 1 — there is
no goal persistence yet.
"""

from __future__ import annotations

import queue
import threading
import time as _time
from enum import Enum
from typing import Callable

import uuid6

from .codec import decode, encode
from .envelope import (
    Goal as GoalInfo,
    Reply,
    Request,
    WireError,
    fail,
    ok_goal,
    ok_value,
    parse_request,
)
from .log import get_logger
from .time import now_ns

_log = get_logger("wf.core.action")

UNKNOWN_GOAL = "unknown_goal"

#: on_accept reason heads that are not plain validation failures.
_REJECT_CODES = {
    "no_control": "conflict",
    "wrong_phase": "conflict",
    "jog_active": "conflict",
    "busy": "busy",
    "not_connected": "unavailable",
    "no_joint_state": "unavailable",
    "accept_error": "internal",
}


def _reject_wire(reason: str) -> dict:
    head, _, detail = reason.partition(":")
    return fail(_REJECT_CODES.get(head, "invalid"), head, detail or None)


class GoalState(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    RUNNING = "running"
    CANCELING = "canceling"
    CANCELED = "canceled"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"


TERMINAL_STATES = frozenset(
    {
        GoalState.REJECTED,
        GoalState.CANCELED,
        GoalState.SUCCEEDED,
        GoalState.FAILED,
        GoalState.ABORTED,
    }
)


class ActionRejected(Exception):
    """Raised by :meth:`ActionClient.send` when the server rejects the goal.
    ``reason`` reconstructs the accept-time ``"head:detail"`` string; the
    parsed envelope error rides on ``.error``."""

    def __init__(self, error: WireError):
        reason = error.reason if error.detail is None else f"{error.reason}:{error.detail}"
        super().__init__(reason)
        self.reason = reason
        self.error = error


class ActionFailed(Exception):
    """A terminal non-success result (canceled / failed / aborted), as raised
    by result-consuming helpers. The envelope error rides on ``.error``."""

    def __init__(self, error: WireError):
        super().__init__(str(error))
        self.error = error


class _GoalRecord:
    __slots__ = (
        "goal_id",
        "name",
        "goal",
        "state",
        "cancel_requested",
        "result",
        "terminal_at",
        "feedback_seq",
    )

    def __init__(self, goal_id: str, name: str, goal: dict):
        self.goal_id = goal_id
        self.name = name
        self.goal = goal
        self.state = GoalState.ACCEPTED
        self.cancel_requested = False
        self.result: dict | None = None  # envelope wire once terminal
        self.terminal_at: float | None = None  # time.monotonic() at terminal
        self.feedback_seq = 0


class GoalHandle:
    """Server-side handle passed to ``on_execute``."""

    def __init__(self, server: "ActionServer", record: _GoalRecord):
        self._server = server
        self._record = record

    @property
    def goal_id(self) -> str:
        return self._record.goal_id

    @property
    def goal(self) -> dict:
        return self._record.goal

    @property
    def cancel_requested(self) -> bool:
        return self._record.cancel_requested

    @property
    def is_terminal(self) -> bool:
        return self._record.state in TERMINAL_STATES

    def feedback(self, progress: float, **data) -> None:
        """Publish best-effort feedback. No-op after the terminal transition."""
        rec = self._record
        if rec.state in TERMINAL_STATES:
            return
        self._server._publish_feedback(rec, float(progress), data)

    def succeed(self, **data) -> None:
        self._server._terminate(self._record, GoalState.SUCCEEDED, None, data)

    def fail(self, error: str, **data) -> None:
        self._server._terminate(self._record, GoalState.FAILED, error, data)

    def set_canceled(self, **data) -> None:
        self._server._terminate(self._record, GoalState.CANCELED, None, data)

    def abort(self, cause: str, **data) -> None:
        self._server._terminate(self._record, GoalState.ABORTED, cause, data)


class ActionServer:
    def __init__(self, session, prefix: str, *, result_ttl_s: float = 60.0, audit=None):
        self._session = session
        self._prefix = prefix
        self._result_ttl_s = result_ttl_s
        # Optional wf.core.audit.QueryAudit: echoes goal/cancel queries (not
        # the result polls) onto the realm's audit stream.
        self._audit = audit
        self._lock = threading.RLock()
        self._records: dict[str, _GoalRecord] = {}
        self._active: _GoalRecord | None = None
        self._handlers: dict[str, tuple[Callable, Callable]] = {}
        self._queue: queue.Queue = queue.Queue()
        self._queryables: list = []
        self._closed = False

        self._worker = threading.Thread(
            target=self._worker_loop, name="action-server-worker", daemon=True
        )
        self._worker.start()

        self._queryables.append(
            session.declare_queryable(f"{prefix}/cancel", self._wrap(self._on_cancel_query))
        )
        self._queryables.append(
            session.declare_queryable(f"{prefix}/*/result", self._on_result_query)
        )

    @property
    def active_goal_id(self) -> str | None:
        """goal_id of the currently active (non-terminal) goal, if any."""
        with self._lock:
            return self._active.goal_id if self._active is not None else None

    def register(
        self,
        name: str,
        on_accept: Callable[[dict, str | None], str | None],
        on_execute: Callable[[GoalHandle], None],
    ) -> None:
        """Register an action. ``on_accept(goal, client_id)`` returns None to
        accept or a machine-readable ``"head:detail"`` rejection reason (the
        acting ``client_id`` arrives top-level in the envelope request)."""
        if name == "cancel":
            raise ValueError("'cancel' is a reserved action name")
        with self._lock:
            if name in self._handlers:
                raise ValueError(f"action {name!r} already registered")
            self._handlers[name] = (on_accept, on_execute)
        self._queryables.append(
            self._session.declare_queryable(
                f"{self._prefix}/{name}",
                self._wrap(lambda query, _name=name: self._on_goal_query(_name, query)),
            )
        )

    def _wrap(self, handler):
        return handler if self._audit is None else self._audit.wrap(handler)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for q in self._queryables:
            try:
                q.undeclare()
            except Exception:
                pass
        self._queue.put(None)
        self._worker.join(timeout=5.0)

    # ── queryable callbacks (zenoh threads) ──────────────────────────────

    def _goal_wire(self, record: _GoalRecord) -> dict:
        return ok_goal(
            GoalInfo(
                goal_id=record.goal_id,
                state=record.state.value,
                feedback_key=f"{self._prefix}/{record.goal_id}/feedback",
                result_key=f"{self._prefix}/{record.goal_id}/result",
                cancel_key=f"{self._prefix}/cancel",
                result_ttl_s=self._result_ttl_s,
            )
        )

    def _on_goal_query(self, name: str, query) -> None:
        key = str(query.key_expr)
        try:
            req = parse_request(query)
        except Exception as exc:  # noqa: BLE001
            query.reply(key, encode(fail("invalid", "bad_request", repr(exc))))
            return
        goal_id, goal = req.req_id, req.args

        on_accept, on_execute = self._handlers[name]

        with self._lock:
            self._prune_locked()

            existing = self._records.get(goal_id)
            if existing is not None:
                # Idempotent resubmission: reply current state, no re-execution.
                query.reply(key, encode(self._goal_wire(existing)))
                return

            if self._active is not None:
                query.reply(
                    key,
                    encode(
                        fail("busy", "goal_active", self._active.goal_id, retryable=True)
                    ),
                )
                return

            try:
                reason = on_accept(goal, req.client_id)
            except Exception as exc:
                reason = f"accept_error:{exc!r}"
            if reason is not None:
                # Rejected goals are not recorded (the same goal_id may retry).
                query.reply(key, encode(_reject_wire(reason)))
                return

            record = _GoalRecord(goal_id, name, goal)
            self._records[goal_id] = record
            self._active = record
            self._queue.put((record, on_execute))
            wire = self._goal_wire(record)

        query.reply(key, encode(wire))

    def _on_cancel_query(self, query) -> None:
        key = str(query.key_expr)
        try:
            req = parse_request(query)
            goal_id = req.args["goal_id"]
        except Exception as exc:  # noqa: BLE001
            query.reply(key, encode(fail("invalid", "bad_request", repr(exc))))
            return
        with self._lock:
            record = self._records.get(goal_id)
            if record is None:
                query.reply(key, encode(fail("not_found", UNKNOWN_GOAL, goal_id)))
                return
            if record.state not in TERMINAL_STATES:
                record.cancel_requested = True
                record.state = GoalState.CANCELING
            state = record.state.value
        query.reply(key, encode(ok_value({"state": state})))

    def _on_result_query(self, query) -> None:
        key = str(query.key_expr)
        goal_id = key.rsplit("/", 2)[-2]
        with self._lock:
            self._prune_locked()
            record = self._records.get(goal_id)
            result = record.result if record is not None else None
        if result is not None:
            query.reply(key, encode(result))
        elif record is None:
            query.reply(key, encode(fail("not_found", UNKNOWN_GOAL, goal_id)))
        # Known goal still executing: no reply — the client keeps waiting.

    # ── worker thread ────────────────────────────────────────────────────

    def _worker_loop(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            record, on_execute = item
            with self._lock:
                if record.state == GoalState.ACCEPTED:
                    record.state = GoalState.RUNNING
            handle = GoalHandle(self, record)
            try:
                on_execute(handle)
            except Exception as exc:
                if record.state not in TERMINAL_STATES:
                    self._terminate(record, GoalState.FAILED, repr(exc), {})
            if record.state not in TERMINAL_STATES:
                self._terminate(
                    record,
                    GoalState.FAILED,
                    "on_execute returned without terminal state",
                    {},
                )

    # ── internals ────────────────────────────────────────────────────────

    def _publish_feedback(self, record: _GoalRecord, progress: float, data: dict):
        with self._lock:
            record.feedback_seq += 1
            seq = record.feedback_seq
        payload = {
            "t": now_ns(),
            "seq": seq,
            "goal_id": record.goal_id,
            "state": record.state.value,
            "progress": progress,
            "detail": data,
        }
        self._session.put(f"{self._prefix}/{record.goal_id}/feedback", encode(payload))

    def _terminate(
        self, record: _GoalRecord, state: GoalState, error: str | None, data: dict
    ) -> None:
        assert state in TERMINAL_STATES
        with self._lock:
            if record.state in TERMINAL_STATES:
                _log.warning(
                    "goal %s already terminal (%s); ignoring %s",
                    record.goal_id,
                    record.state.value,
                    state.value,
                )
                return
            record.state = state
            if state == GoalState.SUCCEEDED:
                record.result = ok_value(data)
            elif state == GoalState.CANCELED:
                record.result = fail("cancelled", "canceled", error)
            else:  # FAILED / ABORTED
                record.result = fail(
                    "internal", "failed" if state == GoalState.FAILED else "aborted", error
                )
            record.terminal_at = _time.monotonic()
            if self._active is record:
                self._active = None
            result = record.result
        self._session.put(f"{self._prefix}/{record.goal_id}/result", encode(result))

    def _prune_locked(self) -> None:
        now = _time.monotonic()
        expired = [
            gid
            for gid, rec in self._records.items()
            if rec.terminal_at is not None
            and now - rec.terminal_at > self._result_ttl_s
        ]
        for gid in expired:
            del self._records[gid]


class Goal:
    """Client-side handle for a submitted, accepted goal."""

    def __init__(self, client: "ActionClient", goal_id: str, result_subscriber,
                 info: GoalInfo | None = None):
        self._client = client
        self.goal_id = goal_id
        self.info = info  # the reply's self-describing keys
        self._result_subscriber = result_subscriber
        self._result_event = threading.Event()
        self._result: Reply | None = None

    def _on_result_sample(self, sample) -> None:
        try:
            wire = decode(sample.payload)
            self._result = Reply.from_wire(wire)
        except Exception:
            return
        self._result_event.set()

    def result(self, timeout_s: float = 60.0) -> Reply:
        """Wait for the terminal result — the envelope, parsed.

        Subscribes to the retained result key (done at send time) AND polls
        the result queryable every 0.5 s, so a result published before the
        subscription matched is still recovered. ``not_found:unknown_goal``
        while waiting means the server may have restarted; the wait continues
        on the subscriber until the deadline."""
        deadline = _time.monotonic() + timeout_s
        session = self._client._session
        result_key = f"{self._client._prefix}/{self.goal_id}/result"
        while True:
            if self._result_event.wait(timeout=0.5):
                return self._result  # type: ignore[return-value]
            if _time.monotonic() >= deadline:
                raise TimeoutError(
                    f"no result for goal {self.goal_id} within {timeout_s}s"
                )
            try:
                replies = session.get(result_key, timeout=0.5)
                for reply in replies:
                    sample = reply.ok
                    if sample is None:
                        continue
                    parsed = Reply.from_wire(decode(sample.payload))
                    if parsed.error is not None and parsed.error.reason == UNKNOWN_GOAL:
                        continue  # server restart grace: keep waiting
                    self._result = parsed
                    self._result_event.set()
                    return parsed
            except Exception:
                pass

    def value(self, timeout_s: float = 60.0) -> dict:
        """``result()`` for the common case: the value on success, raises
        :class:`ActionFailed` on canceled/failed/aborted."""
        reply = self.result(timeout_s=timeout_s)
        if reply.ok and reply.value is not None:
            return reply.value
        raise ActionFailed(reply.error or WireError("internal", "bad_envelope"))

    def cancel(self, timeout_s: float = 5.0) -> dict:
        """Request cancellation; returns ``{"state": ...}`` (``unknown_goal``
        when the server no longer knows the goal)."""
        session = self._client._session
        req = Request.new({"goal_id": self.goal_id})
        replies = session.get(
            f"{self._client._prefix}/cancel",
            payload=encode(req.to_wire()),
            timeout=timeout_s,
        )
        for reply in replies:
            sample = reply.ok
            if sample is None:
                continue
            parsed = Reply.from_wire(decode(sample.payload))
            if parsed.ok and parsed.value is not None:
                return parsed.value
            return {"state": parsed.error.reason if parsed.error else "error"}
        raise TimeoutError(f"no cancel reply for goal {self.goal_id}")


class ActionClient:
    def __init__(self, session, prefix: str, name: str):
        self._session = session
        self._prefix = prefix
        self._name = name

    def send(
        self,
        goal: dict,
        *,
        client_id: str | None = None,
        goal_id: str | None = None,
        on_feedback: Callable[[dict], None] | None = None,
        timeout_s: float = 5.0,
    ) -> Goal:
        """Submit a goal; raises :class:`ActionRejected` on rejection.

        ``client_id`` travels top-level in the envelope request (the lease
        check reads it there). The goal id is the request's ``req_id``
        (client-minted), so the feedback/result subscribers can be declared
        BEFORE the get is issued — early samples are not lost — and the
        reply's self-describing keys confirm the convention.
        """
        goal_id = goal_id or str(uuid6.uuid7())

        feedback_subscriber = None
        if on_feedback is not None:

            def _on_feedback_sample(sample):
                try:
                    on_feedback(decode(sample.payload))
                except Exception:
                    _log.exception("feedback callback failed")

            feedback_subscriber = self._session.declare_subscriber(
                f"{self._prefix}/{goal_id}/feedback", _on_feedback_sample
            )

        goal_obj: Goal | None = None

        def _on_result_sample(sample):
            if goal_obj is not None:
                goal_obj._on_result_sample(sample)

        result_subscriber = self._session.declare_subscriber(
            f"{self._prefix}/{goal_id}/result", _on_result_sample
        )
        goal_obj = Goal(self, goal_id, result_subscriber)

        req = Request(req_id=goal_id, args=dict(goal), client_id=client_id)
        replies = self._session.get(
            f"{self._prefix}/{self._name}",
            payload=encode(req.to_wire()),
            timeout=timeout_s,
        )
        reply_parsed: Reply | None = None
        for reply in replies:
            sample = reply.ok
            if sample is not None:
                reply_parsed = Reply.from_wire(decode(sample.payload))
                break

        def _drop_subs() -> None:
            if feedback_subscriber is not None:
                feedback_subscriber.undeclare()
            result_subscriber.undeclare()

        if reply_parsed is None:
            _drop_subs()
            raise TimeoutError(f"no reply from action server for {self._name}")
        if not reply_parsed.ok:
            _drop_subs()
            raise ActionRejected(
                reply_parsed.error or WireError("internal", "bad_envelope")
            )
        if reply_parsed.goal is None:
            _drop_subs()
            raise ActionRejected(WireError("internal", "bad_envelope", "expected goal branch"))
        goal_obj.info = reply_parsed.goal
        return goal_obj
