"""The cancellation token every action runs under.

Non-blocking transitions (RFC §3.3): leaving a state cancels its running
action. The runner calls :meth:`ActionContext.cancel`; the token flips, every
registered canceller (e.g. an in-flight arm goal's ``cancel``) fires, and the
action thread unwinds with :class:`ActionCancelled` at its next blocking
proxy call or explicit :meth:`check`.

Proxies find the token of the calling action through :meth:`current` (a
thread-local), so user code never passes it around explicitly.
"""

from __future__ import annotations

import threading
from typing import Callable

from .errors import ActionCancelled

_local = threading.local()


class ActionContext:
    def __init__(self, state_id: str, *, log=None):
        self.state_id = state_id
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self._cancellers: list[Callable[[], None]] = []
        self._log = log

    # ── thread-local binding ─────────────────────────────────────────────

    @classmethod
    def current(cls) -> "ActionContext | None":
        return getattr(_local, "ctx", None)

    def _bind(self) -> None:
        _local.ctx = self

    @staticmethod
    def _unbind() -> None:
        _local.ctx = None

    # ── cancellation ─────────────────────────────────────────────────────

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def check(self) -> None:
        """Raise :class:`ActionCancelled` if the action was cancelled."""
        if self._cancelled.is_set():
            raise ActionCancelled(self.state_id)

    def cancel(self) -> None:
        self._cancelled.set()
        with self._lock:
            cancellers = list(self._cancellers)
            self._cancellers.clear()
        for fn in cancellers:
            try:
                fn()
            except Exception:  # noqa: BLE001 - best effort
                pass

    def on_cancel(self, fn: Callable[[], None]) -> Callable[[], None]:
        """Register a canceller (fires once, immediately if already cancelled).
        Returns a function that unregisters it (call when the work finished)."""
        with self._lock:
            if self._cancelled.is_set():
                fire = True
            else:
                fire = False
                self._cancellers.append(fn)
        if fire:
            fn()

        def unregister() -> None:
            with self._lock:
                try:
                    self._cancellers.remove(fn)
                except ValueError:
                    pass

        return unregister

    def sleep(self, seconds: float) -> None:
        """Interruptible sleep: returns after ``seconds`` or raises on cancel."""
        if self._cancelled.wait(max(0.0, seconds)):
            raise ActionCancelled(self.state_id)

    def log(self, message: str) -> None:
        if self._log is not None:
            self._log(message)
