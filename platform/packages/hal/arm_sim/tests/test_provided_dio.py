"""One HAL, two contracts: an ArmCore + SimArmBackend process ALSO serves its
IO bank as a `dio` device (`provides.io0`) — named channels + raw pins, set
through the arm's set_do, force for the (static) sim inputs, cell-lease gated.
Runs over an in-process zenoh session."""

from __future__ import annotations

import time
import uuid

import pytest

from wf.contracts.arm import keys as arm_keys
from wf.contracts.arm.messages import IoState
from wf.contracts.control import keys as control_keys
from wf.contracts.control.authority import ControlAuthority
from wf.contracts.dio import keys as dio_keys
from wf.contracts.dio.messages import ChannelsState, ForceChannel, SetChannel
from wf.core.envelope import Reply, request as envelope_request
from wf.core.codec import decode, encode
from wf.hal.arm_core import ArmCore
from wf.hal.arm_sim.backend import SimArmBackend
from wf.hal.arm_sim.config import load_resource
from wf.hal.aubo_i10 import BUNDLED_URDF

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]

PROVIDES = {
    "io0": {
        "contract": "dio",
        "layout": {"di": 4, "do": 4, "tool_do": 2, "ai": 0, "ao": 0},
        "channels": {
            "part_present": {"kind": "di", "bank": "standard", "pin": 0},
            "clamp": {"kind": "do", "bank": "standard", "pin": 1},
            "gripper": {"kind": "do", "bank": "tool", "pin": 0},
        },
    }
}


def _ack(session, key, client_id, msg) -> Reply:
    return envelope_request(session, key, msg.to_wire(), client_id=client_id, timeout_s=3.0)


def _state(session, realm) -> ChannelsState:
    for reply in session.get(dio_keys.state_channels(realm, "io0"), timeout=3.0):
        if reply.ok is not None:
            return ChannelsState.from_wire(decode(reply.ok.payload))
    pytest.fail("no dio state")


def _wait(pred, timeout_s=3.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.02)
    return pred()


def test_arm_process_serves_dio_device(tmp_path):
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    authority.start()

    cell = tmp_path / "cell.yaml"
    cell.write_text("resources: {r1: {contract: arm, params: {}}}\n", encoding="utf-8")
    params = load_resource(str(cell), "r1")
    params["urdf"] = BUNDLED_URDF
    params["provides"] = PROVIDES
    core = ArmCore(session, realm, "r1", params, SimArmBackend(HOME_Q))
    try:
        core.start()
        envelope_request(session, control_keys.cmd_acquire(realm),
                         {"user": "alice"}, client_id="op", timeout_s=3.0)
        assert _wait(lambda: core._lease.holds("op"))

        # Named channels + auto channels for every unmapped physical point.
        st = _state(session, realm)
        names = set(st.channels)
        assert {"part_present", "clamp", "gripper"} <= names
        assert {"di1", "di2", "di3", "do0", "do2", "do3", "tool_do1"} <= names
        assert "di0" not in names and "do1" not in names  # mapped -> no auto twin
        assert st.channels["di3"].auto and st.channels["di3"].address == {"bank": "standard", "pin": 3}
        assert st.channels["clamp"].auto is False

        # dio alive token exists next to the arm's.
        tokens = [r.ok for r in session.liveliness().get(dio_keys.alive(realm, "io0"), timeout=2.0) if r.ok]
        assert tokens

        # set through the arm: the arm's own state/io reflects the DO bit.
        seen: list[IoState] = []
        sub = session.declare_subscriber(
            arm_keys.state_io(realm, "r1"), lambda s: seen.append(IoState.from_wire(decode(s.payload)))
        )
        try:
            assert _ack(session, dio_keys.cmd_set(realm, "io0"), "op", SetChannel("clamp", True)).ok
            assert _wait(lambda: any(io.do_ >> 1 & 1 for io in seen))
            assert _wait(lambda: _state(session, realm).channels["clamp"].value is True)
            # raw pin do2 via its auto name
            assert _ack(session, dio_keys.cmd_set(realm, "io0"), "op", SetChannel("do2", True)).ok
            assert _wait(lambda: any(io.do_ >> 2 & 1 for io in seen))
        finally:
            sub.undeclare()

        # sim DIs are static zeros -> force drives them
        assert _ack(session, dio_keys.cmd_force(realm, "io0"), "op", ForceChannel("part_present", True)).ok
        cv = _state(session, realm).channels["part_present"]
        assert cv.value is True and cv.forced

        # lease-gated
        ack = _ack(session, dio_keys.cmd_set(realm, "io0"), "intruder", SetChannel("clamp", False))
        assert not ack.ok and ack.error.reason == "no_control"
    finally:
        core.shutdown()
        time.sleep(0.1)  # let the sim tick thread observe the stop before the session closes
        authority.close()
        session.close()
