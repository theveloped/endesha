"""Action pattern: goal lifecycle per design Appendix A.

Wire protocol (prefix = e.g. ``live/arm/r1/action``):

- Goal submit (queryable per action name): client GETs ``{prefix}/{name}``
  with payload ``{"goal_id": str, "goal": dict}``. ``goal_id`` is always
  client-generated UUIDv7. Reply: ``{"goal_id", "accepted": bool,
  "reason": str|None, "state": str}``.
- Feedback (best-effort pub): key ``{prefix}/{goal_id}/feedback``, payload
  ``{"t": ns, "goal_id", "state", "progress": float, "data": dict}``.
- Result (pub + queryable on the same key — the queryable is the source of
  truth): key ``{prefix}/{goal_id}/result``, payload ``{"t": ns, "goal_id",
  "state", "ok": bool, "error": str|None, "data": dict}``. A query for an
  expired/never-seen goal replies ``{"goal_id", "state": "unknown_goal",
  "ok": false, "error": "unknown_goal"}``.
- Cancel (one queryable per prefix, shared by all actions): key
  ``{prefix}/cancel``, payload ``{"goal_id"}``; reply ``{"goal_id", "state"}``
  (state after the cancel request; ``unknown_goal`` if not found).

Server semantics enforced here (HALs cannot diverge):

- One worker thread per :class:`ActionServer`; goals execute strictly
  serially. At most one active (non-terminal) goal across all registered
  actions — a new goal while one is active is rejected with reason ``"busy"``
  before ``on_accept`` is consulted. No queueing.
- Idempotency: a resubmitted known ``goal_id`` replies ``{"accepted": true,
  "state": <current>}`` without re-executing — including terminal goals still
  inside the TTL window. Rejected goals are NOT recorded, so a goal_id that
  was rejected (e.g. ``busy``) may be resubmitted and re-evaluated.
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
from .log import get_logger
from .time import now_ns

_log = get_logger("wf.core.action")

UNKNOWN_GOAL = "unknown_goal"


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
    """Raised by :meth:`ActionClient.send` when the server rejects the goal."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class _GoalRecord:
    __slots__ = (
        "goal_id",
        "name",
        "goal",
        "state",
        "cancel_requested",
        "result",
        "terminal_at",
    )

    def __init__(self, goal_id: str, name: str, goal: dict):
        self.goal_id = goal_id
        self.name = name
        self.goal = goal
        self.state = GoalState.ACCEPTED
        self.cancel_requested = False
        self.result: dict | None = None
        self.terminal_at: float | None = None  # time.monotonic() at terminal


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
        on_accept: Callable[[dict], str | None],
        on_execute: Callable[[GoalHandle], None],
    ) -> None:
        """Register an action. ``on_accept`` returns None to accept or a
        machine-readable rejection reason string."""
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

    def _on_goal_query(self, name: str, query) -> None:
        key = str(query.key_expr)
        try:
            payload = decode(query.payload)
            goal_id = payload["goal_id"]
            goal = payload.get("goal") or {}
        except Exception as exc:
            query.reply(
                key,
                encode(
                    {
                        "goal_id": None,
                        "accepted": False,
                        "reason": f"bad_request: {exc!r}",
                        "state": GoalState.REJECTED.value,
                    }
                ),
            )
            return

        on_accept, on_execute = self._handlers[name]

        with self._lock:
            self._prune_locked()

            existing = self._records.get(goal_id)
            if existing is not None:
                # Idempotent resubmission: reply current state, no re-execution.
                query.reply(
                    key,
                    encode(
                        {
                            "goal_id": goal_id,
                            "accepted": True,
                            "reason": None,
                            "state": existing.state.value,
                        }
                    ),
                )
                return

            if self._active is not None:
                query.reply(
                    key,
                    encode(
                        {
                            "goal_id": goal_id,
                            "accepted": False,
                            "reason": "busy",
                            "state": GoalState.REJECTED.value,
                        }
                    ),
                )
                return

            try:
                reason = on_accept(goal)
            except Exception as exc:
                reason = f"accept_error: {exc!r}"
            if reason is not None:
                # Rejected goals are not recorded (the same goal_id may retry).
                query.reply(
                    key,
                    encode(
                        {
                            "goal_id": goal_id,
                            "accepted": False,
                            "reason": reason,
                            "state": GoalState.REJECTED.value,
                        }
                    ),
                )
                return

            record = _GoalRecord(goal_id, name, goal)
            self._records[goal_id] = record
            self._active = record
            self._queue.put((record, on_execute))

        query.reply(
            key,
            encode(
                {
                    "goal_id": goal_id,
                    "accepted": True,
                    "reason": None,
                    "state": GoalState.ACCEPTED.value,
                }
            ),
        )

    def _on_cancel_query(self, query) -> None:
        key = str(query.key_expr)
        try:
            goal_id = decode(query.payload)["goal_id"]
        except Exception:
            query.reply(key, encode({"goal_id": None, "state": UNKNOWN_GOAL}))
            return
        with self._lock:
            record = self._records.get(goal_id)
            if record is None:
                query.reply(key, encode({"goal_id": goal_id, "state": UNKNOWN_GOAL}))
                return
            if record.state not in TERMINAL_STATES:
                record.cancel_requested = True
                record.state = GoalState.CANCELING
            state = record.state.value
        query.reply(key, encode({"goal_id": goal_id, "state": state}))

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
            query.reply(
                key,
                encode(
                    {
                        "goal_id": goal_id,
                        "state": UNKNOWN_GOAL,
                        "ok": False,
                        "error": UNKNOWN_GOAL,
                    }
                ),
            )
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
        payload = {
            "t": now_ns(),
            "goal_id": record.goal_id,
            "state": record.state.value,
            "progress": progress,
            "data": data,
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
            record.result = {
                "t": now_ns(),
                "goal_id": record.goal_id,
                "state": state.value,
                "ok": state == GoalState.SUCCEEDED,
                "error": error,
                "data": data,
            }
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

    def __init__(self, client: "ActionClient", goal_id: str, result_subscriber):
        self._client = client
        self.goal_id = goal_id
        self._result_subscriber = result_subscriber
        self._result_event = threading.Event()
        self._result: dict | None = None

    def _on_result_sample(self, sample) -> None:
        try:
            self._result = decode(sample.payload)
        except Exception:
            return
        self._result_event.set()

    def result(self, timeout_s: float = 60.0) -> dict:
        """Wait for the terminal result.

        Subscribes to the result key (done at send time) AND polls the result
        queryable every 0.5 s, so a result published before the subscription
        matched is still recovered.
        """
        deadline = _time.monotonic() + timeout_s
        session = self._client._session
        result_key = f"{self._client._prefix}/{self.goal_id}/result"
        terminal_values = {s.value for s in TERMINAL_STATES}
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
                    payload = decode(sample.payload)
                    if payload.get("state") in terminal_values:
                        self._result = payload
                        self._result_event.set()
                        return payload
                    # unknown_goal while waiting: server may have restarted;
                    # keep waiting on the subscriber until the deadline.
            except Exception:
                pass

    def cancel(self, timeout_s: float = 5.0) -> dict:
        """Request cancellation; returns the server's ``{goal_id, state}`` reply."""
        session = self._client._session
        replies = session.get(
            f"{self._client._prefix}/cancel",
            payload=encode({"goal_id": self.goal_id}),
            timeout=timeout_s,
        )
        for reply in replies:
            sample = reply.ok
            if sample is not None:
                return decode(sample.payload)
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
        goal_id: str | None = None,
        on_feedback: Callable[[dict], None] | None = None,
        timeout_s: float = 5.0,
    ) -> Goal:
        """Submit a goal; raises :class:`ActionRejected` on rejection.

        The feedback subscriber is declared before the get is issued so early
        feedback is not lost.
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

        replies = self._session.get(
            f"{self._prefix}/{self._name}",
            payload=encode({"goal_id": goal_id, "goal": goal}),
            timeout=timeout_s,
        )
        reply_payload = None
        for reply in replies:
            sample = reply.ok
            if sample is not None:
                reply_payload = decode(sample.payload)
                break
        if reply_payload is None:
            if feedback_subscriber is not None:
                feedback_subscriber.undeclare()
            result_subscriber.undeclare()
            raise TimeoutError(f"no reply from action server for {self._name}")
        if not reply_payload.get("accepted"):
            if feedback_subscriber is not None:
                feedback_subscriber.undeclare()
            result_subscriber.undeclare()
            raise ActionRejected(reply_payload.get("reason") or "rejected")
        return goal_obj
