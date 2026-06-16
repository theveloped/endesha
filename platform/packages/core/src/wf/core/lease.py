"""Generic single-holder arbitration lease (L0, design §7.2).

A :class:`ControlLease` grants exclusive control to one ``client_id`` at a
time. Grants expire after ``ttl_s`` wall-clock seconds; a holder renews by
re-acquiring (same ``client_id``) before expiry. No robot/UI knowledge lives
here — the arm drivers compose one to arbitrate jog + execute_path.
"""

from __future__ import annotations

import threading

from .time import now_ns


class ControlLease:
    """Thread-safe exclusive lease keyed by ``client_id``.

    All timestamps are integer nanoseconds (wall clock). Expiry is lazy:
    :meth:`owner`/:meth:`holds`/:meth:`acquire` evaluate it on read.
    """

    def __init__(self, ttl_s: float = 30.0):
        self._ttl_ns = int(ttl_s * 1e9)
        self._lock = threading.Lock()
        self._owner: dict | None = None  # ControlOwner.to_wire() shape

    def _expired(self, owner: dict, now: int) -> bool:
        return now >= owner["expires_at"]

    def acquire(self, client_id: str, user: str) -> tuple[dict | None, str | None]:
        """Grant or renew the lease.

        Returns ``(owner_dict, None)`` on grant — a fresh grant, or a renewal
        by the same ``client_id`` (keeps ``granted_at``, bumps ``expires_at``).
        Returns ``(None, "held_by:{user}")`` when a different, unexpired client
        holds it.
        """
        now = now_ns()
        with self._lock:
            cur = self._owner
            if cur is not None and not self._expired(cur, now):
                if cur["client_id"] == client_id:
                    cur = {**cur, "user": user, "expires_at": now + self._ttl_ns}
                    self._owner = cur
                    return dict(cur), None
                return None, f"held_by:{cur['user']}"
            owner = {
                "client_id": client_id,
                "user": user,
                "granted_at": now,
                "expires_at": now + self._ttl_ns,
            }
            self._owner = owner
            return dict(owner), None

    def release(self, client_id: str) -> bool:
        """Free the lease iff ``client_id`` is the current owner."""
        with self._lock:
            cur = self._owner
            if cur is not None and cur["client_id"] == client_id:
                self._owner = None
                return True
            return False

    def owner(self) -> dict | None:
        """Current owner dict, or ``None`` when free or expired."""
        now = now_ns()
        with self._lock:
            cur = self._owner
            if cur is None:
                return None
            if self._expired(cur, now):
                self._owner = None
                return None
            return dict(cur)

    def holds(self, client_id: str) -> bool:
        """True iff ``client_id`` is the current valid (unexpired) owner."""
        now = now_ns()
        with self._lock:
            cur = self._owner
            if cur is None:
                return False
            if self._expired(cur, now):
                self._owner = None
                return False
            return cur["client_id"] == client_id
