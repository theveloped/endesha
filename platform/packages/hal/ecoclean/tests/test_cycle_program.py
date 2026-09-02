"""The shipped ``deploy/ecoclean/programs/ecoclean_cycle.py`` under the program
runner against the sim washer: load -> open -> operator "loaded" -> wash ->
open -> operator "unloaded" -> close -> complete; the HMI labels reach the
catalog; a Stop mid-door releases the permission (door stops)."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

import pytest

from wf.contracts.control.authority import ControlAuthority
from wf.contracts.program import keys
from wf.contracts.program.messages import Catalog, EventRequest, LoadRequest, ProgramState
from wf.core.envelope import request as envelope_request
from wf.contracts.washer import keys as washer_keys
from wf.contracts.washer.messages import WasherStatus
from wf.core.codec import decode, encode
from wf.hal.ecoclean import EcocleanSimBackend, WasherCore
from wf.services.program_runner.service import ProgramRunner

zenoh = pytest.importorskip("zenoh")

PROGRAMS_DIR = Path(__file__).resolve().parents[4] / "deploy" / "ecoclean" / "programs"

PARAMS = {
    "time_scale": 0.05,
    "door_travel_s": 3.0,
    "wash_time_s": 40,  # 2 s
    "settle_s": 0.02,
    "provides": {"plc0": {"contract": "tags", "tags": {}}},
}
DEVICES = [
    {"id": "washer0", "contract": "washer", "model": "sim", "active": "sim", "config": {}, "sources": []},
    {"id": "plc0", "contract": "tags", "model": None, "active": "sim", "config": {}, "sources": [], "provided_by": "washer0"},
]


def _query(session, key, payload):
    for reply in session.get(key, payload=encode(payload), timeout=5.0):
        if reply.ok is not None:
            return decode(reply.ok.payload)
    pytest.fail(f"no reply from {key}")


def _ack(session, key, payload):
    return envelope_request(session, key, payload, timeout_s=5.0)


def _state(session, realm) -> ProgramState:
    return ProgramState.from_wire(_query(session, keys.state(realm), {}))


def _wait(pred, timeout_s=15.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.05)
    return pred()


def _wait_prog_state(session, realm, name, timeout_s=15.0):
    assert _wait(lambda: name in _state(session, realm).program_states, timeout_s), \
        f"program never reached {name}: {_state(session, realm)}"


@pytest.fixture
def cell():
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    authority.start()
    backend = EcocleanSimBackend(PARAMS)
    washer = WasherCore(session, realm, "washer0", PARAMS, backend)
    washer.start()
    runner = ProgramRunner(session, realm, str(PROGRAMS_DIR), devices=DEVICES)
    runner.start()
    time.sleep(0.3)
    yield session, realm, washer
    runner.shutdown()
    washer.shutdown()
    time.sleep(0.1)
    authority.close()
    session.close()


def _phase(session, realm) -> str:
    return WasherStatus.from_wire(_query(session, washer_keys.state_status(realm, "washer0"), {})).phase


def test_cycle_program_end_to_end(cell):
    session, realm, washer = cell
    cat = Catalog.from_wire(_query(session, keys.catalog(realm), {}))
    entry = next(p for p in cat.programs if p.name == "ecoclean_cycle")
    assert entry.error is None, entry.error
    assert entry.roles == {"washer": "washer"}
    assert entry.hmi["loaded"].startswith("Basket loaded")

    assert _ack(session, keys.cmd_load(realm), LoadRequest("ecoclean_cycle", params={"cycles": 1}).to_wire()).ok
    assert _ack(session, keys.cmd(realm, "start"), {}).ok
    _wait_prog_state(session, realm, "loading")
    assert _phase(session, realm) == "door_open"
    # the operator's buttons: the runner tells the HMI it waits for these events
    st = _state(session, realm)
    waited = {w["event"] for w in st.waiting_for if w["kind"] == "event"}
    assert {"loaded", "skip"} <= waited

    assert _ack(session, keys.cmd_event(realm), EventRequest("loaded").to_wire()).ok
    _wait_prog_state(session, realm, "washing")
    assert _wait(lambda: _phase(session, realm) == "washing")
    _wait_prog_state(session, realm, "unloading", timeout_s=30.0)
    assert _phase(session, realm) == "door_open"
    assert _ack(session, keys.cmd_event(realm), EventRequest("unloaded").to_wire()).ok
    assert _wait(lambda: _state(session, realm).unit == "complete", 20.0), _state(session, realm)
    assert _phase(session, realm) == "ready_to_load"


def test_stop_mid_door_releases_permission():
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    authority.start()
    params = {**PARAMS, "door_travel_s": 80.0}  # 4 s door
    backend = EcocleanSimBackend(params)
    washer = WasherCore(session, realm, "washer0", params, backend)
    washer.start()
    runner = ProgramRunner(session, realm, str(PROGRAMS_DIR), devices=DEVICES)
    runner.start()
    try:
        time.sleep(0.3)
        assert _ack(session, keys.cmd_load(realm), LoadRequest("ecoclean_cycle").to_wire()).ok
        assert _ack(session, keys.cmd(realm, "start"), {}).ok
        assert _wait(lambda: _phase(session, realm) == "door_moving", 10.0)
        assert _ack(session, keys.cmd(realm, "stop"), {}).ok
        assert _wait(lambda: _state(session, realm).unit == "stopped", 10.0)
        assert _wait(lambda: washer.get("PermissionToClose") is False, 5.0)
        assert washer.status.sequence is None
        time.sleep(0.5)
        assert _phase(session, realm) == "door_moving"  # stayed put
    finally:
        runner.shutdown()
        washer.shutdown()
        authority.close()
        session.close()
