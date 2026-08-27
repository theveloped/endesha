"""sim_dio: script parsing + scripted input drives the core."""

from __future__ import annotations

import time
import uuid

import pytest

from wf.contracts.dio import keys
from wf.contracts.dio.messages import ChannelsState
from wf.core.codec import decode
from wf.hal.dio_core import DioCore
from wf.hal.sim_dio import SimDioBackend, parse_script


def test_parse_script():
    steps, loop = parse_script(
        {"steps": [{"at_s": 2, "set": {"a": True}}, {"at_s": 0.5, "set": {"b": 1.5}}]}
    )
    assert steps == [(0.5, {"b": 1.5}), (2.0, {"a": True})]
    assert loop is False
    assert parse_script(None) == ([], False)


@pytest.mark.parametrize(
    "raw",
    [
        [],
        {"steps": {}},
        {"steps": [{"at_s": -1}]},
        {"steps": [{"at_s": 1, "set": []}]},
        {"loop": True, "steps": []},
    ],
)
def test_parse_script_rejects(raw):
    with pytest.raises(ValueError, match="bad_script"):
        parse_script(raw)


def test_scripted_input_reaches_the_bus():
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    params = {
        "channels": {"part_present": {"kind": "di", "pin": 0}, "clamp": {"kind": "do", "pin": 0}},
        "script": {"steps": [{"at_s": 0.2, "set": {"part_present": True}}]},
    }
    seen: list[ChannelsState] = []
    sub = session.declare_subscriber(
        keys.state_channels(realm, "io0"),
        lambda s: seen.append(ChannelsState.from_wire(decode(s.payload))),
    )
    core = DioCore(session, realm, "io0", params, SimDioBackend(params))
    try:
        core.start()
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and not any(
            s.channels["part_present"].value is True for s in seen
        ):
            time.sleep(0.02)
        assert any(s.channels["part_present"].value is True for s in seen)
        assert seen[0].channels["part_present"].value is False  # published initial state first
    finally:
        core.shutdown()
        sub.undeclare()
        session.close()
