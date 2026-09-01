"""DioCore over an in-process zenoh session: force overlay, lease gate,
read-only inputs, scale/offset, publish-on-change."""

from __future__ import annotations

import time
import uuid

import pytest

from wf.contracts.control import keys as control_keys
from wf.contracts.control.authority import ControlAuthority
from wf.contracts.dio import keys
from wf.contracts.dio.messages import ChannelsState, ForceChannel, SetChannel
from wf.core.envelope import Reply, request as envelope_request
from wf.core.codec import decode, encode
from wf.hal.dio_core import DioBackend, DioCore

CHANNELS = {
    "part_present": {"kind": "di", "pin": 3},
    "clamp": {"kind": "do", "pin": 0},
    "pressure": {"kind": "ai", "index": 0, "unit": "bar", "scale": 0.1, "offset": -1.0},
    "valve": {"kind": "ao", "index": 0},
}


class FakeBackend(DioBackend):
    def __init__(self):
        self.raw = {"part_present": False, "pressure": 20.0}
        self.writes: list[tuple[str, object]] = []
        self.core = None

    def start(self, core):
        self.core = core

    def shutdown(self):
        pass

    def read(self):
        return dict(self.raw)

    def write(self, channel, raw):
        if channel.name == "valve" and raw > 100:
            raise RuntimeError("valve_overrange")
        self.writes.append((channel.name, raw))
        self.raw[channel.name] = raw


def _ack(session, key, client_id, msg) -> Reply:
    return envelope_request(session, key, msg.to_wire(), client_id=client_id, timeout_s=3.0)


def _state(session, realm, rid) -> ChannelsState:
    for reply in session.get(keys.state_channels(realm, rid), timeout=3.0):
        if reply.ok is not None:
            return ChannelsState.from_wire(decode(reply.ok.payload))
    pytest.fail("no state reply")


def _wait(pred, timeout_s=3.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.02)
    return pred()


@pytest.fixture
def stack():
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    authority.start()
    backend = FakeBackend()
    core = DioCore(session, realm, "io0", {"channels": CHANNELS, "poll_hz": 50}, backend)
    core.start()
    envelope_request(session, control_keys.cmd_acquire(realm),
                     {"user": "alice"}, client_id="op", timeout_s=3.0)
    assert _wait(lambda: core._lease.holds("op"))
    yield session, realm, core, backend
    core.shutdown()
    authority.close()
    session.close()


def test_initial_state_and_scaling(stack):
    session, realm, core, backend = stack
    st = _state(session, realm, "io0")
    assert st.channels["part_present"].value is False
    assert st.channels["clamp"].value is False and st.channels["clamp"].kind == "do"
    assert st.channels["pressure"].value == pytest.approx(20.0 * 0.1 - 1.0)
    assert all(not cv.forced for cv in st.channels.values())


def test_set_output_and_read_only_input(stack):
    session, realm, core, backend = stack
    assert _ack(session, keys.cmd_set(realm, "io0"), "op", SetChannel("clamp", True)).ok
    assert backend.writes == [("clamp", True)]
    assert _state(session, realm, "io0").channels["clamp"].value is True

    ack = _ack(session, keys.cmd_set(realm, "io0"), "op", SetChannel("part_present", True))
    assert not ack.ok and ack.error.reason == "read_only"

    ack = _ack(session, keys.cmd_set(realm, "io0"), "op", SetChannel("nope", True))
    assert not ack.ok and ack.error.reason == "unknown_channel" and ack.error.detail == "nope"

    ack = _ack(session, keys.cmd_set(realm, "io0"), "op", SetChannel("clamp", 0.5))
    assert not ack.ok and ack.error.reason == "bad_value" and "expects a bool" in ack.error.detail

    # analog write is de-scaled to raw: value 4.0 bar -> raw (4.0 - -1)/0.1 = 50
    assert _ack(session, keys.cmd_set(realm, "io0"), "op", SetChannel("valve", 4.0)).ok
    assert backend.writes[-1] == ("valve", pytest.approx(4.0))  # valve has no scale
    ack = _ack(session, keys.cmd_set(realm, "io0"), "op", SetChannel("valve", 500.0))
    assert not ack.ok and ack.error.reason == "write_failed" and "valve_overrange" in ack.error.detail


def test_lease_gate(stack):
    session, realm, core, backend = stack
    ack = _ack(session, keys.cmd_set(realm, "io0"), "intruder", SetChannel("clamp", True))
    assert not ack.ok and ack.error.reason == "no_control"
    ack = _ack(session, keys.cmd_force(realm, "io0"), "intruder", ForceChannel("clamp", True))
    assert not ack.ok and ack.error.reason == "no_control"
    assert backend.writes == []
    # forcing an INPUT is a flagged test override: no lease needed
    assert _ack(session, keys.cmd_force(realm, "io0"), "intruder", ForceChannel("part_present", True)).ok
    assert core.reported("part_present") is True
    assert _ack(session, keys.cmd_force(realm, "io0"), "intruder", ForceChannel("part_present", None)).ok


def test_force_input_overrides_backend_and_publishes(stack):
    session, realm, core, backend = stack
    seen: list[ChannelsState] = []
    sub = session.declare_subscriber(
        keys.state_channels(realm, "io0"),
        lambda s: seen.append(ChannelsState.from_wire(decode(s.payload))),
    )
    try:
        assert _ack(session, keys.cmd_force(realm, "io0"), "op", ForceChannel("part_present", True)).ok
        assert _wait(lambda: any(s.channels["part_present"].value is True and s.channels["part_present"].forced for s in seen))
        # backend still says False; reported stays forced True
        assert backend.raw["part_present"] is False
        assert core.reported("part_present") is True

        # clearing returns to the backend value
        assert _ack(session, keys.cmd_force(realm, "io0"), "op", ForceChannel("part_present", None)).ok
        assert _wait(lambda: core.reported("part_present") is False)
        st = _state(session, realm, "io0")
        assert st.channels["part_present"].forced is False
    finally:
        sub.undeclare()


def test_force_output_writes_and_blocks_set(stack):
    session, realm, core, backend = stack
    assert _ack(session, keys.cmd_force(realm, "io0"), "op", ForceChannel("clamp", True)).ok
    assert backend.writes == [("clamp", True)]
    ack = _ack(session, keys.cmd_set(realm, "io0"), "op", SetChannel("clamp", False))
    assert not ack.ok and ack.error.reason == "forced"
    assert _ack(session, keys.cmd_force(realm, "io0"), "op", ForceChannel("clamp", None)).ok
    assert _ack(session, keys.cmd_set(realm, "io0"), "op", SetChannel("clamp", False)).ok
    assert backend.writes[-1] == ("clamp", False)


def test_backend_change_is_published_via_notify(stack):
    session, realm, core, backend = stack
    seen: list[ChannelsState] = []
    sub = session.declare_subscriber(
        keys.state_channels(realm, "io0"),
        lambda s: seen.append(ChannelsState.from_wire(decode(s.payload))),
    )
    try:
        backend.raw["part_present"] = True
        core.notify()
        assert _wait(lambda: any(s.channels["part_present"].value is True for s in seen))
    finally:
        sub.undeclare()
