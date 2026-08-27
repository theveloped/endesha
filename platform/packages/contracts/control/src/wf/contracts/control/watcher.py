"""Provider-side lease checker.

A provider never grants control; it asks :meth:`LeaseWatcher.holds` before
accepting a guarded command. The watcher mirrors ``state/owner`` (subscription
+ one query at start so a late joiner is not blind), validates ``expires_at``
against the local clock, and tracks the authority's ``control/alive`` token.
No authority => nobody holds the lease.

Duck-compatible with :class:`wf.core.lease.ControlLease` (``holds``/``owner``)
so unit tests can substitute a local lease.
"""

from __future__ import annotations

import threading

import zenoh

from wf.core.codec import decode
from wf.core.log import get_logger
from wf.core.time import now_ns

from . import keys
from .messages import ControlOwnerState

_log = get_logger("wf.contracts.control.watcher")


class LeaseWatcher:
    def __init__(self, session, realm: str):
        self.session = session
        self.realm = realm
        self._lock = threading.Lock()
        self._owner: dict | None = None
        self._authority_alive = False
        self._sub = None
        self._live_sub = None

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._sub = self.session.declare_subscriber(
            keys.state_owner(self.realm), self._on_owner_sample
        )
        try:
            self._live_sub = self.session.liveliness().declare_subscriber(
                keys.alive(self.realm), self._on_liveliness, history=True
            )
        except Exception as exc:  # pragma: no cover - zenoh binding drift
            _log.warning("liveliness subscriber unavailable (%r); assuming authority alive", exc)
            self._authority_alive = True
        # Late joiner: pull the current owner once (the queryable answers even
        # when nothing has been published since we subscribed).
        try:
            for reply in self.session.get(keys.state_owner(self.realm), timeout=1.0):
                if reply.ok is not None:
                    self._on_owner_sample(reply.ok)
                    break
        except Exception as exc:
            _log.debug("initial owner query failed: %r", exc)

    def close(self) -> None:
        for sub in (self._sub, self._live_sub):
            if sub is not None:
                try:
                    sub.undeclare()
                except Exception:
                    pass
        self._sub = None
        self._live_sub = None

    # ── callbacks ────────────────────────────────────────────────────────

    def _on_owner_sample(self, sample) -> None:
        try:
            state = ControlOwnerState.from_wire(decode(sample.payload))
        except Exception as exc:
            _log.warning("bad control owner sample: %r", exc)
            return
        with self._lock:
            self._owner = None if state.owner is None else state.owner.to_wire()

    def _on_liveliness(self, sample) -> None:
        alive = sample.kind == zenoh.SampleKind.PUT
        with self._lock:
            self._authority_alive = alive
        if not alive:
            _log.warning("control authority gone; all guarded commands will be rejected")

    # ── queries ──────────────────────────────────────────────────────────

    @property
    def authority_alive(self) -> bool:
        with self._lock:
            return self._authority_alive

    def owner(self) -> dict | None:
        """Current unexpired owner dict, or None (also None without an authority)."""
        with self._lock:
            if not self._authority_alive or self._owner is None:
                return None
            if now_ns() >= self._owner["expires_at"]:
                return None
            return dict(self._owner)

    def holds(self, client_id: str | None) -> bool:
        if not client_id:
            return False
        owner = self.owner()
        return owner is not None and owner["client_id"] == client_id
