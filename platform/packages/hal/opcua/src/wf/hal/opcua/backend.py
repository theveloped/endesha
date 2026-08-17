"""OpcuaBackend: the tags contract over an OPC-UA server (asyncua).

Cell params::

    endpoint: opc.tcp://192.168.0.1:4840
    username: ecoclean            # optional
    password: "..."               # optional
    timeout_s: 5.0
    inventory:                    # the controller's variables (display name -> node/type/access)
      ReadyToLoad: { node: "ns=4;i=85", type: bool, access: r }
      LoadRequest: { node: "ns=4;i=118", type: bool, access: rw }
    watchdog:                     # optional: toggle a bool tag so the PLC knows we are alive
      tag: WatchDogExt            # inventory display name (or a cell tag name)
      period_s: 0.5
    subscription_ms: 100

The client runs on its own thread with its own asyncio loop. A single
subscription over every known node feeds a value cache (``read()`` returns
it) and ``core.notify()``; writes go through ``run_coroutine_threadsafe`` with
the ua VariantType read from the node's DataType at connect (so ``int`` tags
write as Int16/Int32/… exactly as the server declares them). Connection loss
is retried with backoff; the core keeps publishing the last known values.
"""

from __future__ import annotations

import asyncio
import threading
import time

from asyncua import Client, ua

from wf.contracts.tags.messages import TagDef
from wf.core.log import get_logger
from wf.hal.sim_tags.backend import parse_inventory
from wf.hal.tags_core import TagsBackend

_log = get_logger("wf.hal.opcua")

_RECONNECT_S = (1.0, 2.0, 5.0, 10.0, 30.0)


class OpcuaBackend(TagsBackend):
    def __init__(self, params: dict):
        self.endpoint = params.get("endpoint")
        if not isinstance(self.endpoint, str) or not self.endpoint.startswith("opc.tcp://"):
            raise ValueError("bad_params:opcua requires endpoint 'opc.tcp://host:port'")
        self.username = params.get("username")
        self.password = params.get("password")
        self.timeout_s = float(params.get("timeout_s", 5.0))
        self.subscription_ms = int(params.get("subscription_ms", 100))
        self._inventory = parse_inventory(params.get("inventory"))
        wd = params.get("watchdog") or {}
        self._watchdog_tag = wd.get("tag")
        self._watchdog_period = float(wd.get("period_s", 0.5))

        self.core = None
        self._lock = threading.Lock()
        self._values: dict[str, object] = {}  # node id -> last value
        self._node_of: dict[str, str] = {}  # channel name -> node id
        self._name_of: dict[str, str] = {}  # node id -> channel name
        self._vtype: dict[str, ua.VariantType] = {}  # node id -> variant type
        self._connected = threading.Event()
        self._stop = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client: Client | None = None
        self._watchdog_state = False

    # ── TagsBackend ──────────────────────────────────────────────────────

    def inventory(self) -> list[TagDef]:
        return list(self._inventory)

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    def start(self, core) -> None:
        self.core = core
        for name, td in core.channels.items():
            node = td.address.get("node")
            if node is None:
                _log.warning("tag %s has no node address; ignored by opcua backend", name)
                continue
            self._node_of[name] = str(node)
            self._name_of[str(node)] = name
        self._thread = threading.Thread(target=self._thread_main, name="opcua-client", daemon=True)
        self._thread.start()

    def shutdown(self) -> None:
        self._stop.set()
        if self._loop is not None:
            self._loop.call_soon_threadsafe(lambda: None)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def read(self) -> dict:
        with self._lock:
            values = dict(self._values)
        return {name: values[node] for name, node in self._node_of.items() if node in values}

    def write(self, channel, raw) -> None:
        node = self._node_of.get(channel.name)
        if node is None:
            raise RuntimeError(f"no_node:{channel.name}")
        if not self._connected.is_set() or self._loop is None:
            raise RuntimeError("opcua_disconnected")
        fut = asyncio.run_coroutine_threadsafe(self._write(node, raw), self._loop)
        fut.result(timeout=self.timeout_s)
        with self._lock:
            self._values[node] = raw

    # ── asyncio side ─────────────────────────────────────────────────────

    def _thread_main(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run())
        finally:
            self._loop.close()

    async def _run(self) -> None:
        attempt = 0
        while not self._stop.is_set():
            try:
                await self._session()
                attempt = 0
            except Exception as exc:  # noqa: BLE001
                self._connected.clear()
                delay = _RECONNECT_S[min(attempt, len(_RECONNECT_S) - 1)]
                attempt += 1
                _log.warning("opcua %s: %r; reconnecting in %.0fs", self.endpoint, exc, delay)
                for _ in range(int(delay * 10)):
                    if self._stop.is_set():
                        return
                    await asyncio.sleep(0.1)

    async def _session(self) -> None:
        client = Client(self.endpoint, timeout=self.timeout_s)
        if self.username:
            client.set_user(self.username)
        if self.password:
            client.set_password(self.password)
        async with client:
            self._client = client
            nodes = {}
            for node_id in self._name_of:
                node = client.get_node(node_id)
                try:
                    self._vtype[node_id] = await node.read_data_type_as_variant_type()
                except Exception:  # noqa: BLE001 - keep going, write() will fall back
                    pass
                nodes[node_id] = node
            # initial read
            for node_id, node in nodes.items():
                try:
                    value = await node.read_value()
                except Exception as exc:  # noqa: BLE001
                    _log.warning("initial read %s failed: %r", node_id, exc)
                    continue
                with self._lock:
                    self._values[node_id] = value
            handler = _SubHandler(self)
            sub = await client.create_subscription(self.subscription_ms, handler)
            if nodes:
                await sub.subscribe_data_change(list(nodes.values()))
            self._connected.set()
            _log.info("opcua connected: %s (%d nodes)", self.endpoint, len(nodes))
            if self.core is not None:
                self.core.notify()
            wd_node = self._watchdog_node()
            next_wd = time.monotonic()
            while not self._stop.is_set():
                await asyncio.sleep(0.1)
                if wd_node is not None and time.monotonic() >= next_wd:
                    self._watchdog_state = not self._watchdog_state
                    await self._write(wd_node, self._watchdog_state)
                    next_wd = time.monotonic() + self._watchdog_period
                # cheap liveness probe every ~5 s: a failed read raises -> reconnect
                if int(time.monotonic() * 10) % 50 == 0:
                    await client.check_connection()
            self._connected.clear()

    def _watchdog_node(self) -> str | None:
        if not self._watchdog_tag:
            return None
        if self._watchdog_tag in self._node_of:
            return self._node_of[self._watchdog_tag]
        for inv in self._inventory:
            if inv.name == self._watchdog_tag:
                return str(inv.address.get("node"))
        _log.warning("watchdog tag %s not found; watchdog disabled", self._watchdog_tag)
        return None

    async def _write(self, node_id: str, raw) -> None:
        assert self._client is not None
        node = self._client.get_node(node_id)
        vtype = self._vtype.get(node_id)
        if vtype is None:
            await node.write_value(raw)
        else:
            await node.write_value(ua.DataValue(ua.Variant(raw, vtype)))

    def _on_change(self, node_id: str, value) -> None:
        with self._lock:
            self._values[node_id] = value
        if self.core is not None:
            self.core.notify()


class _SubHandler:
    def __init__(self, backend: OpcuaBackend):
        self._b = backend

    def datachange_notification(self, node, val, data) -> None:  # asyncua callback name
        try:
            self._b._on_change(node.nodeid.to_string(), val)
        except Exception:
            _log.debug("datachange handling failed", exc_info=True)
