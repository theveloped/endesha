"""arm_dio against a fake arm on the bus: bit-unpacking + set_do write-through."""

from __future__ import annotations

import time
import uuid

import pytest

from wf.contracts.arm import keys as arm_keys
from wf.contracts.arm.messages import Ack as ArmAck
from wf.contracts.arm.messages import IoState, SetDo
from wf.contracts.control.authority import ControlAuthority
from wf.contracts.control.messages import AcquireControl
from wf.contracts.control import keys as control_keys
from wf.contracts.dio import keys
from wf.contracts.dio.messages import Ack, ChannelsState, SetChannel
from wf.core.codec import decode, encode
from wf.hal.arm_dio import ArmDioBackend
from wf.hal.dio_core import DioCore

CHANNELS = {
    "part_present": {"kind": "di", "bank": "standard", "pin": 3},
    "clamp": {"kind": "do", "bank": "standard", "pin": 1},
    "gripper": {"kind": "do", "bank": "tool", "pin": 0},
    "pressure": {"kind": "ai", "index": 1},
}


class FakeArm:
    """Publishes state/io and answers cmd/set_do like ArmCore would."""

    def __init__(self, session, realm, rid="r1"):
        self.session = session
        self.realm = realm
        self.rid = rid
        self.di = 0
        self.do = 0
        self.ai = [0.0, 2.5]
        self.set_calls: list[SetDo] = []
        self._pub = session.declare_publisher(arm_keys.state_io(realm, rid))
        self._q = session.declare_queryable(arm_keys.cmd_set_do(realm, rid), self._on_set_do)

    def publish(self):
        self._pub.put(encode(IoState(t=1, di=self.di, do_=self.do, ai=self.ai, ao=[]).to_wire()))

    def _on_set_do(self, query):
        req = SetDo.from_wire(decode(query.payload))
        self.set_calls.append(req)
        if req.bank == "standard":
            mask = 1 << req.pin
            self.do = self.do | mask if req.value else self.do & ~mask
            self.publish()
        query.reply(str(query.key_expr), encode(ArmAck(ok=True).to_wire()))

    def close(self):
        self._q.undeclare()


def _ack(session, key, msg) -> Ack:
    for reply in session.get(key, payload=encode(msg.to_wire()), timeout=3.0):
        if reply.ok is not None:
            return Ack.from_wire(decode(reply.ok.payload))
    pytest.fail(f"no reply from {key}")


def _wait(pred, timeout_s=3.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.02)
    return pred()


def test_arm_dio_round_trip():
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    arm = FakeArm(session, realm)
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    authority.start()
    params = {"channels": CHANNELS, "arm": "r1", "poll_hz": 50}
    core = DioCore(session, realm, "io0", params, ArmDioBackend(params))
    try:
        core.start()
        _ack(session, control_keys.cmd_acquire(realm), AcquireControl("op", "alice"))
        assert _wait(lambda: core._lease.holds("op"))

        # arm input rises -> reported through the channel name
        arm.di = 1 << 3
        arm.publish()
        assert _wait(lambda: core.reported("part_present") is True)
        assert core.reported("pressure") == 2.5

        # set standard do -> arm cmd/set_do called and echoed back via state/io
        assert _ack(session, keys.cmd_set(realm, "io0"), SetChannel("op", "clamp", True)).ok
        assert arm.set_calls[-1] == SetDo(bank="standard", pin=1, value=True)
        assert _wait(lambda: core.reported("clamp") is True)

        # tool do is write-only on the arm: reported from the last write
        assert _ack(session, keys.cmd_set(realm, "io0"), SetChannel("op", "gripper", True)).ok
        assert arm.set_calls[-1] == SetDo(bank="tool", pin=0, value=True)
        assert _wait(lambda: core.reported("gripper") is True)

        st = None
        for reply in session.get(keys.state_channels(realm, "io0"), timeout=3.0):
            if reply.ok is not None:
                st = ChannelsState.from_wire(decode(reply.ok.payload))
        assert st is not None and st.channels["part_present"].value is True
    finally:
        core.shutdown()
        authority.close()
        arm.close()
        session.close()


def test_arm_dio_requires_arm_param():
    with pytest.raises(ValueError, match="requires params.arm"):
        ArmDioBackend({})
