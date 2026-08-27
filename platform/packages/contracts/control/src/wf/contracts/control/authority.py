"""The single lease authority of a cell (hosted by the supervisor).

Serves the ``control`` contract on top of :class:`wf.core.lease.ControlLease`:
grants/renews/releases over queryables, publishes ``state/owner`` on every
change and as a 1 Hz keepalive (so late subscribers and lazy expiry are both
covered), answers it on demand via a queryable, and holds the ``control/alive``
liveliness token that providers use to tell "no authority" from "no holder".
"""

from __future__ import annotations

import threading

from wf.core.audit import QueryAudit
from wf.core.codec import decode, encode
from wf.core.lease import ControlLease
from wf.core.log import get_logger
from wf.core.time import now_ns

from . import keys
from .messages import AcquireControl, ControlAck, ControlOwner, ControlOwnerState

_log = get_logger("wf.contracts.control.authority")
_TICK_S = 1.0


def _owner_msg(owner: dict | None) -> ControlOwner | None:
    return None if owner is None else ControlOwner.from_wire(owner)


class ControlAuthority:
    def __init__(self, session, realm: str, *, ttl_s: float = 30.0):
        self.session = session
        self.realm = realm
        self._audit = QueryAudit(session, realm, "control")
        self._lease = ControlLease(ttl_s)
        self._pub = session.declare_publisher(keys.state_owner(realm))
        self._queryables: list = []
        self._alive_token = None
        self._stop = threading.Event()
        self._ticker: threading.Thread | None = None
        self._pub_lock = threading.Lock()

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._queryables = [
            self.session.declare_queryable(keys.cmd_acquire(self.realm), self._audit.wrap(self._on_acquire)),
            self.session.declare_queryable(keys.cmd_release(self.realm), self._audit.wrap(self._on_release)),
            self.session.declare_queryable(keys.state_owner(self.realm), self._on_owner_query),
        ]
        self._alive_token = self.session.liveliness().declare_token(keys.alive(self.realm))
        self._publish()
        self._ticker = threading.Thread(
            target=self._tick_loop, name="control-authority", daemon=True
        )
        self._ticker.start()
        _log.info("control authority up: realm=%s ttl=%.1fs", self.realm, self._lease._ttl_ns / 1e9)

    def close(self) -> None:
        self._stop.set()
        if self._ticker is not None:
            self._ticker.join(timeout=2.0)
            self._ticker = None
        for q in self._queryables:
            try:
                q.undeclare()
            except Exception:
                pass
        self._queryables = []
        if self._alive_token is not None:
            try:
                self._alive_token.undeclare()
            except Exception:
                pass
            self._alive_token = None

    # ── introspection ────────────────────────────────────────────────────

    def owner(self) -> dict | None:
        return self._lease.owner()

    def holds(self, client_id: str) -> bool:
        return self._lease.holds(client_id)

    # ── queryables ───────────────────────────────────────────────────────

    def _on_acquire(self, query) -> None:
        key = str(query.key_expr)
        try:
            req = AcquireControl.from_wire(decode(query.payload))
            owner, err = self._lease.acquire(req.client_id, req.user)
            if err is None:
                self._publish()
            holder = owner if owner is not None else self._lease.owner()
            ack = ControlAck(ok=err is None, owner=_owner_msg(holder), error=err)
            query.reply(key, encode(ack.to_wire()))
        except Exception as exc:
            query.reply(key, encode(ControlAck(ok=False, error=repr(exc)).to_wire()))

    def _on_release(self, query) -> None:
        key = str(query.key_expr)
        try:
            cid = decode(query.payload).get("client_id")
            released = self._lease.release(cid)
            if released:
                self._publish()
            ack = ControlAck(
                ok=True,
                owner=_owner_msg(self._lease.owner()),
                error=None if released else "not_holder",
            )
            query.reply(key, encode(ack.to_wire()))
        except Exception as exc:
            query.reply(key, encode(ControlAck(ok=False, error=repr(exc)).to_wire()))

    def _on_owner_query(self, query) -> None:
        query.reply(str(query.key_expr), encode(self._state().to_wire()))

    # ── publish ──────────────────────────────────────────────────────────

    def _state(self) -> ControlOwnerState:
        return ControlOwnerState(t=now_ns(), owner=_owner_msg(self._lease.owner()))

    def _publish(self) -> None:
        with self._pub_lock:
            try:
                self._pub.put(encode(self._state().to_wire()))
            except Exception as exc:
                _log.warning("publish control owner failed: %r", exc)

    def _tick_loop(self) -> None:
        # 1 Hz keepalive; lazy expiry shows up as owner -> None.
        while not self._stop.wait(_TICK_S):
            self._publish()
