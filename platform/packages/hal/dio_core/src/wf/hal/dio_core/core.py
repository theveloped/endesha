"""Shared dio contract core.

``DioCore`` serves the entire ``dio`` contract for one logical device against a
pluggable :class:`DioBackend`: the channel table (from cell ``channels:``),
scale/offset for analog channels, the **force overlay**, the cell-lease check
on ``set``/``force``, and ``state/channels`` publishing (on change + 1 Hz
keepalive). The backend only moves raw values.

Force semantics (PLC style): a forced channel *reports* the forced value no
matter what the backend reads; forcing an OUTPUT additionally writes it and
blocks ``set`` (``forced``) until cleared. Clearing a forced output leaves the
last forced value written.

Lease policy: ``set`` and forcing an OUTPUT need the cell control lease (they
drive actuators). Forcing an INPUT does not — it is a visibly flagged test /
commissioning override (drive a sensor in sim while a program holds the lease).
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import yaml

from wf.contracts.control.watcher import LeaseWatcher
from wf.contracts.dio import keys
from wf.contracts.dio.messages import (
    Ack,
    ChannelDef,
    ChannelsState,
    ChannelValue,
    ForceChannel,
    SetChannel,
    auto_channel_name,
    parse_channels,
)
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.core.time import now_ns

from .backend import DioBackend

_log = get_logger("wf.hal.dio_core")

_DEFAULT_POLL_HZ = 20.0
_KEEPALIVE_S = 1.0


def load_dio_resource(cell_yaml_path: str, resource_id: str) -> dict:
    """``resources[rid].params`` of a realized cell (channels + backend params)."""
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


def _address_key(address: dict) -> tuple:
    return tuple(sorted((str(k), str(v)) for k, v in address.items()))


class DioCore:
    """``lease`` may be a shared :class:`LeaseWatcher` (a host process serving
    several contracts keeps one watcher); when None the core owns one. The
    core declares its own ``dio/{rid}/alive`` liveliness token so a provided
    device (hosted inside another provider's process) is discoverable too."""

    def __init__(
        self,
        session,
        realm: str,
        rid: str,
        params: dict,
        backend: DioBackend,
        *,
        lease: LeaseWatcher | None = None,
    ):
        self.session = session
        self.realm = realm
        self.rid = rid
        self.params = params
        self.backend = backend
        self._poll_s = 1.0 / float(params.get("poll_hz", _DEFAULT_POLL_HZ))
        # Named channels first (cell.yaml order), then one auto channel per
        # physical point nobody named — the raw pin view.
        self.channels: dict[str, ChannelDef] = parse_channels(params.get("channels"))
        named_points = {
            (ch.kind, _address_key(ch.address)) for ch in self.channels.values()
        }
        for kind, address in backend.points():
            if (kind, _address_key(address)) in named_points:
                continue
            name = auto_channel_name(kind, address)
            if name in self.channels:
                continue  # an operator picked the auto name for a different pin
            self.channels[name] = ChannelDef(name=name, kind=kind, address=dict(address), auto=True)

        self._lock = threading.Lock()
        # Engineering-unit values as last read from / written to the backend.
        self._hw: dict[str, bool | float] = {
            name: ch.default_value() for name, ch in self.channels.items()
        }
        self._forced: dict[str, bool | float] = {}

        self._owns_lease = lease is None
        self._lease = lease if lease is not None else LeaseWatcher(session, realm)
        self._pub = session.declare_publisher(keys.state_channels(realm, rid))
        self._queryables: list = []
        self._alive_token = None
        self._stop = threading.Event()
        self._kick = threading.Event()
        self._thread: threading.Thread | None = None

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._queryables = [
            self.session.declare_queryable(keys.cmd_set(self.realm, self.rid), self._on_set),
            self.session.declare_queryable(keys.cmd_force(self.realm, self.rid), self._on_force),
            self.session.declare_queryable(
                keys.state_channels(self.realm, self.rid), self._on_state_query
            ),
        ]
        if self._owns_lease:
            self._lease.start()
        self._alive_token = self.session.liveliness().declare_token(
            keys.alive(self.realm, self.rid)
        )
        self.backend.start(self)
        self._poll_once()
        self.publish()
        self._thread = threading.Thread(target=self._loop, name="dio-core", daemon=True)
        self._thread.start()
        _log.info(
            "dio core up: realm=%s rid=%s channels=%d", self.realm, self.rid, len(self.channels)
        )

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
        _log.info("dio core stopped")

    def notify(self) -> None:
        """Backends call this when inputs changed asynchronously."""
        self._kick.set()

    # ── values ───────────────────────────────────────────────────────────

    def reported(self, name: str):
        with self._lock:
            return self._reported_locked(name)

    def _reported_locked(self, name: str):
        if name in self._forced:
            return self._forced[name]
        return self._hw[name]

    def snapshot(self) -> ChannelsState:
        with self._lock:
            return ChannelsState(
                t=now_ns(),
                channels={
                    name: ChannelValue(
                        kind=ch.kind,
                        value=self._reported_locked(name),
                        forced=name in self._forced,
                        address=ch.address,
                        auto=ch.auto,
                    )
                    for name, ch in self.channels.items()
                },
            )

    def _to_engineering(self, ch: ChannelDef, raw):
        if ch.is_digital:
            return bool(raw)
        return float(raw) * ch.scale + ch.offset

    def _to_raw(self, ch: ChannelDef, value):
        if ch.is_digital:
            return bool(value)
        return (float(value) - ch.offset) / ch.scale

    # ── polling / publishing ─────────────────────────────────────────────

    def _poll_once(self) -> bool:
        """Pull raw values from the backend; True when any reported value changed."""
        try:
            raw = self.backend.read()
        except Exception as exc:
            _log.warning("backend read failed: %r", exc)
            return False
        changed = False
        with self._lock:
            for name, value in raw.items():
                ch = self.channels.get(name)
                if ch is None:
                    continue
                eng = self._to_engineering(ch, value)
                if self._hw.get(name) != eng:
                    self._hw[name] = eng
                    if name not in self._forced:
                        changed = True
        return changed

    def publish(self) -> None:
        state = self.snapshot()
        try:
            self._pub.put(encode(state.to_wire()))
        except Exception as exc:
            _log.warning("publish channels failed: %r", exc)

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

    def _reply(self, query, ack: Ack) -> None:
        query.reply(str(query.key_expr), encode(ack.to_wire()))

    def _on_state_query(self, query) -> None:
        query.reply(str(query.key_expr), encode(self.snapshot().to_wire()))

    def _guard(self, client_id: str | None, name: str, *, lease: bool = True) -> tuple[ChannelDef | None, str | None]:
        ch = self.channels.get(name)
        if ch is None:
            return None, f"unknown_channel:{name}"
        if lease and not self._lease.holds(client_id):
            return None, "no_control"
        return ch, None

    def _on_set(self, query) -> None:
        try:
            req = SetChannel.from_wire(decode(query.payload))
        except Exception as exc:
            self._reply(query, Ack(ok=False, error=f"bad_request:{exc!r}"))
            return
        ch, err = self._guard(req.client_id, req.channel)
        if err is not None:
            self._reply(query, Ack(ok=False, error=err))
            return
        if ch.is_input:
            self._reply(query, Ack(ok=False, error="read_only"))
            return
        with self._lock:
            if req.channel in self._forced:
                self._reply(query, Ack(ok=False, error="forced"))
                return
        try:
            value = ch.coerce(req.value)
            self.backend.write(ch, self._to_raw(ch, value))
        except Exception as exc:
            self._reply(query, Ack(ok=False, error=str(exc)))
            return
        with self._lock:
            self._hw[req.channel] = value
        self.publish()
        self._reply(query, Ack(ok=True))

    def _on_force(self, query) -> None:
        try:
            req = ForceChannel.from_wire(decode(query.payload))
        except Exception as exc:
            self._reply(query, Ack(ok=False, error=f"bad_request:{exc!r}"))
            return
        ch = self.channels.get(req.channel)
        ch, err = self._guard(req.client_id, req.channel, lease=ch is None or not ch.is_input)
        if err is not None:
            self._reply(query, Ack(ok=False, error=err))
            return
        if req.value is None:
            with self._lock:
                self._forced.pop(req.channel, None)
            self.publish()
            self._reply(query, Ack(ok=True))
            return
        try:
            value = ch.coerce(req.value)
            if not ch.is_input:
                self.backend.write(ch, self._to_raw(ch, value))
        except Exception as exc:
            self._reply(query, Ack(ok=False, error=str(exc)))
            return
        with self._lock:
            self._forced[req.channel] = value
            if not ch.is_input:
                self._hw[req.channel] = value
        self.publish()
        self._reply(query, Ack(ok=True))
