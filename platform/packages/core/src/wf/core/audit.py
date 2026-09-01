"""Query/reply audit: observability for zenoh command queryables.

Zenoh queries are point-to-point — a passive ``{realm}/**`` subscriber (the
Topics page, the recorder) never sees them. ``QueryAudit`` wraps a queryable
handler so every handled query is *echoed* as an ordinary sample on
``{realm}/audit/{service}``: ``{t, service, key, params, request, reply, ok,
duration_ms}``. The command mechanism stays query/reply — the echo is pure
observability, so replaying a recording never re-executes a command, but the
recorder still captures who commanded what.

Usage — instead of ``session.declare_queryable(key, handler)``::

    audit = QueryAudit(session, realm, "config")
    session.declare_queryable(key, audit.wrap(handler))

The wrapper is failure-proof: audit errors never disturb the handler, and
oversized request/reply values are truncated in the echo. The audit key is
also queryable — ``{records: [...]}``, the last ``maxlen`` echoes — so a
late-joining viewer (the Queries page) starts with history.
"""

from __future__ import annotations

import json
import re
import threading
from collections import deque
from typing import Callable

import zenoh

from .codec import decode, encode
from .keys import key as make_key, realm_prefix
from .log import get_logger
from .time import now_ns

_log = get_logger("wf.core.audit")

_MAX_VALUE_CHARS = 2048


def audit_key(realm: str, service: str) -> str:
    """``{realm}/audit/{service}`` — the service's query/reply echo stream."""
    return make_key(realm_prefix(realm), "audit", re.sub(r"[/*$?#:]", ".", service))


def _bounded(value):
    """The value itself, or a truncated repr when its JSON form is huge."""
    try:
        text = json.dumps(value, default=repr)
    except Exception:  # noqa: BLE001
        text = repr(value)
    if len(text) <= _MAX_VALUE_CHARS:
        return value
    return {"_truncated": text[:_MAX_VALUE_CHARS]}


def _decoded(payload) -> object:
    if payload is None:
        return None
    try:
        return decode(payload)
    except Exception:  # noqa: BLE001
        return {"_undecodable_bytes": len(bytes(payload.to_bytes()))}


class _RecordingQuery:
    """Delegates to the real ``zenoh.Query`` while remembering the first
    reply's payload for the audit record."""

    def __init__(self, query: zenoh.Query) -> None:
        self._query = query
        self.reply_payload = None
        self.replied = False

    def reply(self, key_expr, payload, **kwargs):
        if not self.replied:
            self.replied = True
            self.reply_payload = payload
        return self._query.reply(key_expr, payload, **kwargs)

    def __getattr__(self, item):
        return getattr(self._query, item)


class QueryAudit:
    """Echoes handled queries of one service onto ``{realm}/audit/{service}``
    and serves the last ``maxlen`` echoes to queries on the same key."""

    def __init__(self, session: zenoh.Session, realm: str, service: str, *, maxlen: int = 200) -> None:
        self._session = session
        self._key = audit_key(realm, service)
        self._service = service
        self._lock = threading.Lock()
        self._ring: deque = deque(maxlen=maxlen)
        self._queryable = None
        try:
            self._queryable = session.declare_queryable(self._key, self._on_history_query)
        except Exception:  # noqa: BLE001
            _log.debug("audit history queryable failed", exc_info=True)

    def close(self) -> None:
        if self._queryable is not None:
            try:
                self._queryable.undeclare()
            except Exception:  # noqa: BLE001
                pass
            self._queryable = None

    def _on_history_query(self, query: zenoh.Query) -> None:
        with self._lock:
            records = list(self._ring)
        try:
            query.reply(self._key, encode({"records": records}))
        except Exception:  # noqa: BLE001
            _log.debug("audit history reply failed", exc_info=True)

    def wrap(self, handler: Callable[[zenoh.Query], None]) -> Callable[[zenoh.Query], None]:
        def wrapped(query: zenoh.Query) -> None:
            t0 = now_ns()
            recording = _RecordingQuery(query)
            error: str | None = None
            try:
                handler(recording)
            except Exception as exc:  # noqa: BLE001
                error = repr(exc)
                raise
            finally:
                try:
                    self._publish(recording, t0, error)
                except Exception:  # noqa: BLE001
                    _log.debug("audit publish failed", exc_info=True)

        return wrapped

    def _publish(self, recording: _RecordingQuery, t0: int, error: str | None) -> None:
        request = _decoded(recording._query.payload)  # noqa: SLF001
        reply = _decoded(recording.reply_payload) if recording.replied else None
        # Replies are the wire-contract envelope: `ok` is authoritative.
        # (Legacy non-envelope replies record ok=None until their contract
        # migrates — no sniffing, per wire-contract RFC review decision 6.)
        ok = None
        if error is not None:
            ok = False
        elif isinstance(reply, dict) and "ok" in reply:
            ok = bool(reply["ok"])
        params = str(recording._query.parameters)  # noqa: SLF001
        record = {
            "t": t0,
            "service": self._service,
            "key": str(recording._query.key_expr),  # noqa: SLF001
            "params": params if params else None,
            "request": _bounded(request),
            "reply": _bounded(reply),
            "ok": ok,
            "error": error,
            "duration_ms": (now_ns() - t0) / 1e6,
        }
        with self._lock:
            self._ring.append(record)
        self._session.put(self._key, encode(record))
