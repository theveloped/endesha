"""WasherCore over the live (OPC-UA) backend against an in-process asyncua
server that exposes the Ecoclean node ids: an open_door handshake reaches the
server's variables (typed), the status follows server-side changes, the
watchdog toggles, and the recipe is read from the real nodes."""

from __future__ import annotations

import asyncio
import socket
import threading
import time
import uuid

import pytest

from wf.contracts.control import keys as control_keys
from wf.contracts.control.authority import ControlAuthority
from wf.core.envelope import request as envelope_request
from wf.contracts.washer import keys
from wf.contracts.washer.messages import RecipeReply, WasherStatus
from wf.core.action import ActionClient
from wf.core.codec import decode, encode
from wf.hal.ecoclean import WasherCore, make_live_backend
from wf.hal.ecoclean import inventory as inv

asyncua = pytest.importorskip("asyncua")
zenoh = pytest.importorskip("zenoh")
from asyncua import Server, ua  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class EcocleanPlcServer:
    """asyncua server with the Ecoclean inventory at its real ns=4 node ids
    (namespace index forced to 4 by registering filler namespaces)."""

    def __init__(self, port: int):
        self.endpoint = f"opc.tcp://127.0.0.1:{port}/ecoclean/"
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._vars: dict[str, object] = {}

    def start(self):
        self._thread.start()
        assert self._ready.wait(20), "server did not start"

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
        idx = await server.register_namespace("filler-2")
        while idx < 4:
            idx = await server.register_namespace(f"filler-{idx + 1}")
        assert idx == 4
        obj = await server.nodes.objects.add_object(idx, "Ecoclean")
        for display, decl in inv.inventory_dict().items():
            i = int(decl["node"].split("i=")[1])
            nodeid = ua.NodeId(i, idx)
            if decl["type"] == "bool":
                init = ua.Variant(False, ua.VariantType.Boolean)
            elif decl["type"] == "int":
                init = ua.Variant(0, ua.VariantType.Int16)
            else:
                init = ua.Variant("", ua.VariantType.String)
            var = await obj.add_variable(nodeid, display, init)
            if decl["access"] == "rw":
                await var.set_writable()
            self._vars[display] = var
        await self._vars["DoorClosed"].write_value(True)
        await self._vars["ReadyToLoad"].write_value(True)
        await self._vars["Auto"].write_value(True)
        await self._vars["Kommentar"].write_value("Standard")
        await self._vars["Programmfolgen[0].BEH"].write_value(ua.Variant(2, ua.VariantType.Int16))
        await self._vars["Programmfolgen[0].ZEIT"].write_value(ua.Variant(45, ua.VariantType.Int16))
        await self._vars["UPM"].write_value(ua.Variant(5, ua.VariantType.Int16))
        async with server:
            self._ready.set()
            while not self._stop.is_set():
                await asyncio.sleep(0.05)
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    def set(self, display: str, value):
        fut = asyncio.run_coroutine_threadsafe(self._vars[display].write_value(value), self._loop)
        fut.result(timeout=5)

    def get(self, display: str):
        fut = asyncio.run_coroutine_threadsafe(self._vars[display].read_value(), self._loop)
        return fut.result(timeout=5)

    def vtype(self, display: str):
        fut = asyncio.run_coroutine_threadsafe(self._vars[display].read_data_type_as_variant_type(), self._loop)
        return fut.result(timeout=5)


def _query(session, key, payload):
    for reply in session.get(key, payload=encode(payload), timeout=5.0):
        if reply.ok is not None:
            return decode(reply.ok.payload)
    pytest.fail(f"no reply from {key}")


def _wait(pred, timeout_s=10.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.05)
    return pred()


def test_live_handshake_against_opcua_server():
    plc = EcocleanPlcServer(_free_port())
    plc.start()
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    authority.start()
    params = {
        "endpoint": plc.endpoint,
        "watchdog": {"tag": "WatchDogExt", "period_s": 0.2},
        "settle_s": 0.05,
        "poll_hz": 50,
        "provides": {"plc0": {"contract": "tags", "tags": {"machine_ready": {"tag": "ReadyToLoad"}}}},
    }
    backend = make_live_backend(params)
    core = WasherCore(session, realm, "washer0", params, backend)
    try:
        core.start()
        assert _wait(lambda: backend.connected, timeout_s=15.0), "never connected"
        envelope_request(session, control_keys.cmd_acquire(realm),
                         {"user": "alice"}, client_id="op")
        assert _wait(lambda: core._lease.holds("op"))

        def status() -> WasherStatus:
            return WasherStatus.from_wire(_query(session, keys.state_status(realm, "washer0"), {}))

        assert _wait(lambda: status().phase == "ready_to_load")
        assert status().program == "Standard" and status().connected

        # open_door: PermissionToClose + LoadRequest reach the server; we play the PLC
        client = ActionClient(session, keys.action_prefix(realm, "washer0"), "open_door")
        goal = client.send({"client_id": "op"})
        assert _wait(lambda: plc.get("LoadRequest") is True and plc.get("PermissionToClose") is True)
        assert _wait(lambda: status().detail == "waiting for door open")
        plc.set("DoorClosed", False)
        time.sleep(0.2)
        assert _wait(lambda: status().door == "moving")
        plc.set("DoorOpen", True)
        res = goal.result(timeout_s=10.0)
        assert res["state"] == "succeeded", res
        assert _wait(lambda: status().phase == "door_open")
        assert _wait(lambda: plc.get("PermissionToClose") is False)

        # start_wash with a program number: typed Int16 write on the real node
        client = ActionClient(session, keys.action_prefix(realm, "washer0"), "start_wash")
        goal = client.send({"client_id": "op", "program": 2})
        assert _wait(lambda: plc.get("WashProgram") == 2 and plc.get("LoadComplete") is True)
        assert plc.vtype("WashProgram") == ua.VariantType.Int16
        plc.set("DoorOpen", False)
        plc.set("DoorClosed", True)
        assert _wait(lambda: plc.get("LoadComplete") is False)
        plc.set("ReadyToLoad", False)
        plc.set("WashingInProgress", True)
        assert goal.result(timeout_s=10.0)["state"] == "succeeded"
        assert _wait(lambda: status().phase == "washing")

        # watchdog toggles on the server
        seen = set()
        for _ in range(12):
            seen.add(plc.get("WatchDogExt"))
            time.sleep(0.1)
        assert seen == {True, False}

        # recipe read from the real nodes
        reply = RecipeReply.from_wire(
            envelope_request(session, keys.cmd_get_recipe(realm, "washer0"), {}).value)
        assert reply.recipe.name == "Standard"
        assert reply.recipe.steps[0].cleaning == 2 and reply.recipe.steps[0].time_s == 45
        assert reply.recipe.params["rpm"] == 5

        # server-side fault -> phase fault
        plc.set("GeneralFault", True)
        plc.set("stoernummer", ua.Variant(7, ua.VariantType.Int16))
        assert _wait(lambda: status().phase == "fault" and status().fault_code == 7)
    finally:
        core.shutdown()
        authority.close()
        session.close()
        plc.stop()
