"""Retained-value consumption (wire-contract RFC §3.1).

A retained key is published latest-wins *and* answers queries with the
identical payload. The one subtle bug-shape when consuming it is ordering,
codified here once instead of per consumer:

**subscribe first, seed with a query second, deltas win over the seed** —
a sample that arrives through the subscription before (or while) the seed
query returns makes the seed stale, so the seed is dropped.
"""

from __future__ import annotations

import threading
from typing import Callable

from .codec import decode
from .log import get_logger

_log = get_logger("wf.core.retained")


class RetainedSubscription:
    """Handle returned by :func:`subscribe_retained`; ``close()`` to stop."""

    def __init__(self, session, key: str, on_value: Callable[[dict], None], *,
                 seed_timeout_s: float = 5.0) -> None:
        self._lock = threading.Lock()
        self._on_value = on_value
        self._got_delta = False
        self._closed = False
        # Subscribe FIRST so nothing published during the seed query is lost.
        self._sub = session.declare_subscriber(key, self._on_sample)
        try:
            for reply in session.get(key, timeout=seed_timeout_s):
                if reply.ok is None:
                    continue
                seed = decode(reply.ok.payload)
                with self._lock:
                    # Deltas win: drop the seed if the stream already spoke.
                    if self._got_delta or self._closed:
                        return
                self._deliver(seed)
                return
        except Exception:  # noqa: BLE001
            _log.debug("retained seed query failed for %s", key, exc_info=True)

    def _on_sample(self, sample) -> None:
        try:
            value = decode(sample.payload)
        except Exception:  # noqa: BLE001
            _log.debug("retained sample decode failed", exc_info=True)
            return
        with self._lock:
            if self._closed:
                return
            self._got_delta = True
        self._deliver(value)

    def _deliver(self, value: dict) -> None:
        try:
            self._on_value(value)
        except Exception:  # noqa: BLE001
            _log.debug("retained on_value callback failed", exc_info=True)

    def close(self) -> None:
        with self._lock:
            self._closed = True
        try:
            self._sub.undeclare()
        except Exception:  # noqa: BLE001
            pass


def subscribe_retained(session, key: str, on_value: Callable[[dict], None], *,
                       seed_timeout_s: float = 5.0) -> RetainedSubscription:
    """Follow a retained key with correct seed ordering. ``on_value`` gets
    every payload (the seed at most once, never after a delta)."""
    return RetainedSubscription(session, key, on_value, seed_timeout_s=seed_timeout_s)
