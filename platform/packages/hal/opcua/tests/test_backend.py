"""OpcuaBackend against an in-process asyncua server: subscription-driven
reads, typed writes (Int16 stays Int16), watchdog toggle, resolution of
inventory names, and reconnect after the server restarts."""

from __future__ import annotations

import asyncio
import socket
import threading
import time
import uuid

import pytest

from wf.contracts.control import keys as control_keys
from wf.contracts.control.authority import ControlAuthority
from wf.contracts.control.messages import AcquireControl
from wf.contracts.tags import keys
from wf.contracts.tags.messages import WriteTag
from wf.core.envelope import Reply, request as envelope_request
from wf.core.codec import decode, encode
from wf.hal.opcua import OpcuaBackend
from wf.hal.tags_core import TagsCore

asyncua = pytest.importorskip("asyncua")
from asyncua import Server, ua  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class MiniPlc:
    """A tiny OPC-UA server on its own thread: ns=2 with a few variables."""

    def __init__(self, port: int):
        self.port = port
        self.endpoint = f"opc.tcp://127.0.0.1:{port}/wf/"
        self.nodes: dict[str, str] = {}
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._server: Server | None = None
        self._vars: dict = {}
        self._values_seen: list = []

    def start(self):
        self._thread.start()
        assert self._ready.wait(15), "server did not start"

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=10)

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main())

    async def _main(self):
        server = Server()
        await server.init()
        server.set_endpoint(self.endpoint)
        server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
        idx = await server.register_namespace("wf-test")
        obj = await server.nodes.objects.add_object(idx, "PLC")
        self._vars["ReadyToLoad"] = await obj.add_variable(idx, "ReadyToLoad", False)
        self._vars["LoadRequest"] = await obj.add_variable(idx, "LoadRequest", False)
        self._vars["WashProgram"] = await obj.add_variable(idx, "WashProgram", ua.Variant(0, ua.VariantType.Int16))
        self._vars["Kommentar"] = await obj.add_variable(idx, "Kommentar", "none")
        self._vars["WatchDogExt"] = await obj.add_variable(idx, "WatchDogExt", False)
        for name in ("LoadRequest", "WashProgram", "Kommentar", "WatchDogExt"):
            await self._vars[name].set_writable()
        self.nodes = {name: var.nodeid.to_string() for name, var in self._vars.items()}
        self._server = server
        async with server:
            self._ready.set()
            while not self._stop.is_set():
                await asyncio.sleep(0.05)
        # asyncua leaves session/subscription loops behind: cancel them so the
        # loop closes quietly.
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    def set(self, name: str, value):
        fut = asyncio.run_coroutine_threadsafe(self._vars[name].write_value(value), self._loop)
        fut.result(timeout=5)

    def get(self, name: str):
        fut = asyncio.run_coroutine_threadsafe(self._vars[name].read_value(), self._loop)
        return fut.result(timeout=5)

    def get_variant_type(self, name: str):
        fut = asyncio.run_coroutine_threadsafe(self._vars[name].read_data_type_as_variant_type(), self._loop)
        return fut.result(timeout=5)


def _ack(session, key, client_id, msg) -> Reply:
    return envelope_request(session, key, msg.to_wire(), client_id=client_id, timeout_s=5.0)


def _wait(pred, timeout_s=8.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.05)
    return pred()


@pytest.fixture
def plc():
    p = MiniPlc(_free_port())
    p.start()
    yield p
    p.stop()


def test_opcua_round_trip(plc):
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    authority.start()
    params = {
        "endpoint": plc.endpoint,
        "inventory": {
            "ReadyToLoad": {"node": plc.nodes["ReadyToLoad"], "type": "bool", "access": "r"},
            "LoadRequest": {"node": plc.nodes["LoadRequest"], "type": "bool", "access": "rw"},
            "WashProgram": {"node": plc.nodes["WashProgram"], "type": "int", "access": "rw"},
            "Kommentar": {"node": plc.nodes["Kommentar"], "type": "string", "access": "rw"},
            "WatchDogExt": {"node": plc.nodes["WatchDogExt"], "type": "bool", "access": "rw"},
        },
        "tags": {"ready": {"tag": "ReadyToLoad"}, "load_request": {"tag": "LoadRequest"}},
        "watchdog": {"tag": "WatchDogExt", "period_s": 0.2},
        "poll_hz": 50,
    }
    backend = OpcuaBackend(params)
    core = TagsCore(session, realm, "plc0", params, backend)
    try:
        core.start()
        assert _wait(lambda: backend.connected), "never connected"
        # control still speaks its legacy dialect (envelope migration is per
        # contract); acquire the lease with a plain query.
        for _ in session.get(control_keys.cmd_acquire(realm),
                             payload=encode(AcquireControl("op", "alice").to_wire()),
                             timeout=3.0):
            pass
        assert _wait(lambda: core._lease.holds("op"))

        # inventory -> auto tags; initial values read
        assert core.reported("wash_program") == 0 and core.reported("kommentar") == "none"

        # server-side change -> subscription -> core
        plc.set("ReadyToLoad", True)
        assert _wait(lambda: core.reported("ready") is True)

        # typed write: Int16 stays Int16 on the server; string and bool too
        assert _ack(session, keys.cmd_write(realm, "plc0"), "op", WriteTag("wash_program", 7)).ok
        assert _wait(lambda: plc.get("WashProgram") == 7)
        assert plc.get_variant_type("WashProgram") == ua.VariantType.Int16
        assert _ack(session, keys.cmd_write(realm, "plc0"), "op", WriteTag("kommentar", "prog B")).ok
        assert _wait(lambda: plc.get("Kommentar") == "prog B")
        assert _ack(session, keys.cmd_write(realm, "plc0"), "op", WriteTag("load_request", True)).ok
        assert _wait(lambda: plc.get("LoadRequest") is True)
        # read-only stays read-only
        assert _ack(session, keys.cmd_write(realm, "plc0"), "op", WriteTag("ready", False)).error.reason == "read_only"

        # watchdog toggles on the server
        seen = set()
        for _ in range(12):
            seen.add(plc.get("WatchDogExt"))
            time.sleep(0.1)
        assert seen == {True, False}
    finally:
        core.shutdown()
        authority.close()
        session.close()


def test_opcua_reconnects_after_server_restart():
    zenoh = pytest.importorskip("zenoh")
    port = _free_port()
    plc = MiniPlc(port)
    plc.start()
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    params = {
        "endpoint": plc.endpoint,
        "inventory": {"ReadyToLoad": {"node": plc.nodes["ReadyToLoad"], "type": "bool", "access": "r"}},
        "poll_hz": 50,
    }
    backend = OpcuaBackend(params)
    core = TagsCore(session, realm, "plc0", params, backend)
    try:
        core.start()
        assert _wait(lambda: backend.connected)
        plc.stop()
        assert _wait(lambda: not backend.connected, timeout_s=20.0), "did not notice the drop"
        plc2 = MiniPlc(port)
        plc2.start()
        try:
            assert _wait(lambda: backend.connected, timeout_s=30.0), "did not reconnect"
            plc2.set("ReadyToLoad", True)
            assert _wait(lambda: core.reported("ready_to_load") is True)
        finally:
            plc2.stop()
    finally:
        core.shutdown()
        session.close()
