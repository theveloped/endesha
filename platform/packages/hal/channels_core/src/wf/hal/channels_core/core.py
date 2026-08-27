"""``ChannelsCore``: the contract-agnostic half of dio / tags providers.

Force semantics (PLC style): a forced channel *reports* the forced value no
matter what the backend reads; forcing a WRITABLE channel additionally writes
it and blocks ``set``/``write`` (``forced``) until cleared.

Lease policy: writes and forcing a WRITABLE channel need the cell control
lease (they drive actuators / the PLC). Forcing a READ-ONLY channel does not:
it is a visibly flagged test / commissioning override (drive a sensor in sim
while a program holds the lease).
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

from wf.contracts.control.watcher import LeaseWatcher
from wf.core.audit import QueryAudit
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.core.time import now_ns

from .backend import ChannelsBackend

_log = get_logger("wf.hal.channels_core")

_DEFAULT_POLL_HZ = 20.0
_KEEPALIVE_S = 1.0


def load_resource_params(cell_yaml_path: str, resource_id: str) -> dict:
    """``resources[rid].params`` of a realized cell."""
    path = Path(cell_yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"cell file not found: {cell_yaml_path}")
    cell = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    resources = cell.get("resources") or {}
    if resource_id not in resources:
        available = ", ".join(sorted(resources)) or "<none>"
        raise KeyError(
            f"resource {resource_id!r} not found in {cell_yaml_path} (available: {available})"
        )
    return dict(resources[resource_id].get("params") or {})


class ChannelDefLike(Protocol):
    """What a channel definition must offer (dio ``ChannelDef``, tags ``TagDef``)."""

    name: str
    kind: str  # dio: di/do/ai/ao; tags: bool/int/float/string
    address: dict
    auto: bool

    @property
    def writable(self) -> bool: ...
    def default_value(self) -> Any: ...
    def coerce(self, value): ...
    def to_engineering(self, raw): ...
    def to_raw(self, value): ...


class Schema(Protocol):
    """Contract-specific pieces of a channel device."""

    contract: str
    #: params key holding the named channel mapping (``channels`` / ``tags``)
    params_key: str

    def key_state(self, realm: str, rid: str) -> str: ...
    def key_set(self, realm: str, rid: str) -> str: ...
    def key_force(self, realm: str, rid: str) -> str: ...
    def key_alive(self, realm: str, rid: str) -> str: ...
    def parse(self, raw: object) -> dict[str, ChannelDefLike]: ...
    def auto_def(self, kind: str, address: dict) -> ChannelDefLike: ...
    def state_wire(self, t: int, values: list[tuple[ChannelDefLike, Any, bool]]) -> dict: ...
    def parse_set(self, payload: dict) -> tuple[str | None, str, Any]: ...
    def parse_force(self, payload: dict) -> tuple[str | None, str, Any]: ...
    def ack_wire(self, ok: bool, error: str | None) -> dict: ...


def _address_key(address: dict) -> tuple:
    return tuple(sorted((str(k), str(v)) for k, v in address.items()))


class ChannelsCore:
    """``lease`` may be a shared :class:`LeaseWatcher` (a host process serving
    several contracts keeps one watcher); when None the core owns one. The
    core declares its own ``{contract}/{rid}/alive`` liveliness token so a
    provided device (hosted inside another provider's process) is discoverable."""

    def __init__(
        self,
        session,
        realm: str,
        rid: str,
        params: dict,
        backend: ChannelsBackend,
        schema: Schema,
        *,
        lease: LeaseWatcher | None = None,
        on_change: Callable[[str, Any, Any], None] | None = None,
    ):
        self.session = session
        self.realm = realm
        self.rid = rid
        self.params = params
        self.backend = backend
        self.schema = schema
        self._audit = QueryAudit(session, realm, f"{schema.contract}:{rid}")
        self._on_change = on_change
        self._poll_s = 1.0 / float(params.get("poll_hz", _DEFAULT_POLL_HZ))
        # Named channels first (cell.yaml order), then one auto channel per raw
        # point nobody named — the raw device view.
        self.channels: dict[str, ChannelDefLike] = schema.parse(params.get(schema.params_key))
        # Identity of a raw point = (kind, address): di 0 and do 0 share an
        # address but are different pins.
        named = {(ch.kind, _address_key(ch.address)) for ch in self.channels.values()}
        for kind, address in backend.points():
            if (kind, _address_key(address)) in named:
                continue
            auto = schema.auto_def(kind, address)
            if auto.name in self.channels:
                continue  # an operator picked the auto name for a different point
            self.channels[auto.name] = auto

        self._lock = threading.Lock()
        # Hosts (a device HAL built on top of this table) block on ``changed``.
        self.changed = threading.Condition(self._lock)
        self._hw: dict[str, Any] = {name: ch.default_value() for name, ch in self.channels.items()}
        self._forced: dict[str, Any] = {}

        self._owns_lease = lease is None
        self._lease = lease if lease is not None else LeaseWatcher(session, realm)
        self._pub = session.declare_publisher(schema.key_state(realm, rid))
        self._queryables: list = []
        self._alive_token = None
        self._stop = threading.Event()
        self._kick = threading.Event()
        self._thread: threading.Thread | None = None

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        s = self.schema
        self._queryables = [
            self.session.declare_queryable(s.key_set(self.realm, self.rid), self._audit.wrap(self._on_set)),
            self.session.declare_queryable(s.key_force(self.realm, self.rid), self._audit.wrap(self._on_force)),
            self.session.declare_queryable(s.key_state(self.realm, self.rid), self._on_state_query),
        ]
        if self._owns_lease:
            self._lease.start()
        self._alive_token = self.session.liveliness().declare_token(s.key_alive(self.realm, self.rid))
        self.backend.start(self)
        self._poll_once()
        self.publish()
        self._thread = threading.Thread(target=self._loop, name=f"{s.contract}-core", daemon=True)
        self._thread.start()
        _log.info("%s core up: realm=%s rid=%s channels=%d", s.contract, self.realm, self.rid, len(self.channels))

    def run_forever(self) -> None:
        try:
            while not self._stop.wait(1.0):
                pass
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._stop.set()
        self._kick.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        try:
            self.backend.shutdown()
        except Exception:
            _log.exception("backend shutdown failed")
        if self._owns_lease:
            self._lease.close()
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
        _log.info("%s core stopped", self.schema.contract)

    def notify(self) -> None:
        """Backends call this when values changed asynchronously."""
        self._kick.set()

    # ── values ───────────────────────────────────────────────────────────

    def reported(self, name: str):
        with self._lock:
            return self._reported_locked(name)

    def _reported_locked(self, name: str):
        if name in self._forced:
            return self._forced[name]
        return self._hw[name]

    def snapshot_wire(self) -> dict:
        with self._lock:
            values = [
                (ch, self._reported_locked(name), name in self._forced)
                for name, ch in self.channels.items()
            ]
        return self.schema.state_wire(now_ns(), values)

    # ── host API (a device HAL hosting this table in-process) ────────────

    def write(self, name: str, value) -> Any:
        """Host-side write: no lease check (the host is the device), still
        refused while the channel is forced (``RuntimeError('forced')``) and
        for read-only channels. Returns the coerced value."""
        ch = self.channels.get(name)
        if ch is None:
            raise KeyError(f"unknown_channel:{name}")
        if not ch.writable:
            raise RuntimeError(f"read_only:{name}")
        with self._lock:
            if name in self._forced:
                raise RuntimeError(f"forced:{name}")
        value = ch.coerce(value)
        self.backend.write(ch, ch.to_raw(value))
        with self._lock:
            self._hw[name] = value
            self.changed.notify_all()
        self.publish()
        return value

    def wait_until(self, pred: Callable[[Callable[[str], Any]], bool], timeout_s: float | None,
                   *, cancel: threading.Event | None = None, tick_s: float = 0.1) -> bool:
        """Block until ``pred(get)`` is true (``get(name)`` -> reported value),
        the timeout passes (False) or ``cancel`` is set (False)."""
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        with self.changed:
            while True:
                if pred(self._reported_locked):
                    return True
                if cancel is not None and cancel.is_set():
                    return False
                if self._stop.is_set():
                    return False
                if deadline is not None:
                    left = deadline - time.monotonic()
                    if left <= 0:
                        return False
                    self.changed.wait(min(tick_s, left))
                else:
                    self.changed.wait(tick_s)

    # ── polling / publishing ─────────────────────────────────────────────

    def _poll_once(self) -> bool:
        try:
            raw = self.backend.read()
        except Exception as exc:
            _log.warning("backend read failed: %r", exc)
            return False
        changed = False
        changes: list[tuple[str, Any, Any]] = []
        with self._lock:
            for name, value in raw.items():
                ch = self.channels.get(name)
                if ch is None:
                    continue
                try:
                    eng = ch.to_engineering(value)
                except Exception:
                    continue
                old = self._hw.get(name)
                if old != eng:
                    self._hw[name] = eng
                    if name not in self._forced:
                        changed = True
                        changes.append((name, old, eng))
            if changed:
                self.changed.notify_all()
        if self._on_change is not None:
            for name, old, new in changes:
                try:
                    self._on_change(name, old, new)
                except Exception:
                    _log.debug("on_change hook failed", exc_info=True)
        return changed

    def publish(self) -> None:
        try:
            self._pub.put(encode(self.snapshot_wire()))
        except Exception as exc:
            _log.warning("publish failed: %r", exc)

    def _loop(self) -> None:
        last_pub = time.monotonic()
        while not self._stop.is_set():
            self._kick.wait(self._poll_s)
            self._kick.clear()
            if self._stop.is_set():
                break
            changed = self._poll_once()
            now = time.monotonic()
            if changed or now - last_pub >= _KEEPALIVE_S:
                self.publish()
                last_pub = now

    # ── queryables ───────────────────────────────────────────────────────

    def _reply(self, query, ok: bool, error: str | None = None) -> None:
        query.reply(str(query.key_expr), encode(self.schema.ack_wire(ok, error)))

    def _on_state_query(self, query) -> None:
        query.reply(str(query.key_expr), encode(self.snapshot_wire()))

    def _guard(self, client_id, name: str, *, lease: bool = True):
        ch = self.channels.get(name)
        if ch is None:
            return None, f"unknown_channel:{name}"
        if lease and not self._lease.holds(client_id):
            return None, "no_control"
        return ch, None

    def _on_set(self, query) -> None:
        try:
            client_id, name, value = self.schema.parse_set(decode(query.payload))
        except Exception as exc:
            self._reply(query, False, f"bad_request:{exc!r}")
            return
        ch, err = self._guard(client_id, name)
        if err is not None:
            self._reply(query, False, err)
            return
        if not ch.writable:
            self._reply(query, False, "read_only")
            return
        with self._lock:
            if name in self._forced:
                self._reply(query, False, "forced")
                return
        try:
            value = ch.coerce(value)
            self.backend.write(ch, ch.to_raw(value))
        except Exception as exc:
            self._reply(query, False, str(exc))
            return
        with self._lock:
            self._hw[name] = value
            self.changed.notify_all()
        self.publish()
        self._reply(query, True)

    def _on_force(self, query) -> None:
        try:
            client_id, name, value = self.schema.parse_force(decode(query.payload))
        except Exception as exc:
            self._reply(query, False, f"bad_request:{exc!r}")
            return
        ch0 = self.channels.get(name)
        ch, err = self._guard(client_id, name, lease=ch0 is None or ch0.writable)
        if err is not None:
            self._reply(query, False, err)
            return
        if value is None:
            with self._lock:
                self._forced.pop(name, None)
                self.changed.notify_all()
            self.publish()
            self._reply(query, True)
            return
        try:
            value = ch.coerce(value)
            if ch.writable:
                self.backend.write(ch, ch.to_raw(value))
        except Exception as exc:
            self._reply(query, False, str(exc))
            return
        with self._lock:
            self._forced[name] = value
            if ch.writable:
                self._hw[name] = value
            self.changed.notify_all()
        self.publish()
        self._reply(query, True)
