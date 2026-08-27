"""Child logs and lifecycle events on the bus.

``LogHub`` republishes every captured stdout/stderr line of a supervised child
on ``{realm}/supervisor/{node}/log/{service}`` and keeps a per-service ring
buffer for late joiners. ``EventLog`` does the same for lifecycle events
(started / exited / stopped / spawn_failed / source_switched / ...) on
``{realm}/supervisor/{node}/events``. Both are ordinary realm topics, so the
recorder captures them and replay debugging includes them for free.
"""

from __future__ import annotations

import re
import threading
from collections import deque

import zenoh

from wf.contracts.supervisor import keys as sup_keys
from wf.core.codec import encode
from wf.core.log import get_logger
from wf.core.time import now_ns

_log = get_logger("wf.services.supervisor.telemetry")

_LEVEL_RE = re.compile(r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b")
_LEVELS = {"DEBUG": "debug", "INFO": "info", "WARNING": "warning", "ERROR": "error", "CRITICAL": "error"}


def parse_level(line: str, stream: str) -> str:
    """Best-effort level from a ``wf.core.log``-formatted line; tracebacks are
    errors, anything else defaults to info (stdout) / warning (stderr noise is
    normal: our services log INFO to stderr, so no stderr penalty)."""
    m = _LEVEL_RE.search(line[:96])
    if m is not None:
        return _LEVELS[m.group(1)]
    if line.startswith(("Traceback (most recent call last)", "Exception", "Error")):
        return "error"
    return "info"


def _safe_chunk(name: str) -> str:
    """A service name as a single zenoh key chunk (``hal:io0`` -> ``hal.io0``)."""
    return re.sub(r"[/*$?#:]", ".", name)


class LogHub:
    """Per-service ring buffers + live publication of captured child output."""

    def __init__(self, session: zenoh.Session, realm: str, node: str = "main", maxlen: int = 300) -> None:
        self._session = session
        self._realm = realm
        self._node = node
        self._maxlen = maxlen
        self._lock = threading.Lock()
        self._rings: dict[str, deque] = {}

    def line(self, service: str, stream: str, raw: str) -> None:
        text = raw.rstrip("\r\n")
        if text == "":
            return
        service = _safe_chunk(service)
        record = {
            "t": now_ns(),
            "level": parse_level(text, stream),
            "stream": stream,
            "source": service,
            "message": text,
        }
        with self._lock:
            ring = self._rings.get(service)
            if ring is None:
                ring = self._rings[service] = deque(maxlen=self._maxlen)
            ring.append(record)
        try:
            self._session.put(sup_keys.supervisor_log(self._realm, service, self._node), encode(record))
        except Exception:  # noqa: BLE001
            _log.debug("log publish failed", exc_info=True)

    def rings(self) -> dict[str, list[dict]]:
        with self._lock:
            return {service: list(ring) for service, ring in self._rings.items()}

    def on_log_query(self, query: zenoh.Query) -> None:
        """Reply one ``{lines: [...]}`` per service the selector matches."""
        for service, lines in self.rings().items():
            key = sup_keys.supervisor_log(self._realm, service, self._node)
            try:
                if query.key_expr.intersects(zenoh.KeyExpr(key)):
                    query.reply(key, encode({"lines": lines}))
            except Exception:  # noqa: BLE001
                _log.debug("log query reply failed", exc_info=True)


class EventLog:
    """Ring buffer + live publication of supervisor lifecycle events."""

    def __init__(self, session: zenoh.Session, realm: str, node: str = "main", maxlen: int = 200) -> None:
        self._session = session
        self._key = sup_keys.supervisor_events(realm, node)
        self._lock = threading.Lock()
        self._ring: deque = deque(maxlen=maxlen)

    def emit(self, kind: str, service: str | None = None, **detail) -> None:
        record = {"t": now_ns(), "kind": kind, "service": service, **detail}
        with self._lock:
            self._ring.append(record)
        try:
            self._session.put(self._key, encode(record))
        except Exception:  # noqa: BLE001
            _log.debug("event publish failed", exc_info=True)

    def on_events_query(self, query: zenoh.Query) -> None:
        with self._lock:
            events = list(self._ring)
        try:
            query.reply(self._key, encode({"events": events}))
        except Exception:  # noqa: BLE001
            _log.debug("events query reply failed", exc_info=True)
