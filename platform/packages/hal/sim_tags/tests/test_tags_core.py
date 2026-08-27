"""TagsCore + SimTagsBackend over an in-process zenoh session: inventory
resolution (named + auto tags), typed write, read-only, force policy, script."""

from __future__ import annotations

import time
import uuid

import pytest

from wf.contracts.control import keys as control_keys
from wf.contracts.control.authority import ControlAuthority
from wf.contracts.control.messages import AcquireControl
from wf.contracts.tags import keys
from wf.contracts.tags.messages import Ack, ForceTag, TagsState, WriteTag
from wf.core.codec import decode, encode
from wf.hal.sim_tags import SimTagsBackend
from wf.hal.tags_core import TagsCore

INVENTORY = {
    "ReadyToLoad": {"type": "bool", "access": "r", "node": "ns=4;i=85"},
    "DoorOpen": {"type": "bool", "access": "r", "node": "ns=4;i=88"},
    "LoadRequest": {"type": "bool", "access": "rw", "node": "ns=4;i=118"},
    "WashProgram": {"type": "int", "access": "rw", "node": "ns=4;i=134"},
    "Kommentar": {"type": "string", "access": "rw", "node": "ns=4;i=77"},
}

PARAMS = {
    "inventory": INVENTORY,
    "tags": {
        "ready_to_load": {"tag": "ReadyToLoad"},
        "load_request": {"tag": "LoadRequest"},
        "wash_program": {"tag": "WashProgram"},
        "temp": {"node": "ns=4;i=200", "type": "float", "access": "r"},
    },
    "poll_hz": 50,
    "script": {"steps": [{"at_s": 0.3, "set": {"DoorOpen": True}}]},
}


def _ack(session, key, msg) -> Ack:
    for reply in session.get(key, payload=encode(msg.to_wire()), timeout=3.0):
        if reply.ok is not None:
            return Ack.from_wire(decode(reply.ok.payload))
    pytest.fail(f"no reply from {key}")


def _state(session, realm) -> TagsState:
    for reply in session.get(keys.state_tags(realm, "plc0"), timeout=3.0):
        if reply.ok is not None:
            return TagsState.from_wire(decode(reply.ok.payload))
    pytest.fail("no state")


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
    backend = SimTagsBackend(PARAMS)
    core = TagsCore(session, realm, "plc0", PARAMS, backend)
    core.start()
    _ack(session, control_keys.cmd_acquire(realm), AcquireControl("op", "alice"))
    assert _wait(lambda: core._lease.holds("op"))
    yield session, realm, core, backend
    core.shutdown()
    authority.close()
    session.close()


def test_resolution_named_and_auto(stack):
    session, realm, core, backend = stack
    st = _state(session, realm)
    names = set(st.tags)
    # named (resolved from inventory) + raw-address + auto for the rest
    assert {"ready_to_load", "load_request", "wash_program", "temp"} <= names
    assert {"door_open", "kommentar"} <= names
    assert "ready_to_load" in names and "load_request" in names
    assert st.tags["ready_to_load"].address == {"tag": "ReadyToLoad", "node": "ns=4;i=85"}
    assert st.tags["ready_to_load"].access == "r" and st.tags["ready_to_load"].auto is False
    assert st.tags["door_open"].auto and st.tags["door_open"].address["node"] == "ns=4;i=88"
    assert st.tags["kommentar"].type == "string" and st.tags["kommentar"].value == ""
    assert st.tags["wash_program"].type == "int" and st.tags["wash_program"].access == "rw"
    assert st.tags["temp"].value == 0.0


def test_write_typed_and_read_only(stack):
    session, realm, core, backend = stack
    assert _ack(session, keys.cmd_write(realm, "plc0"), WriteTag("op", "wash_program", 7)).ok
    assert core.reported("wash_program") == 7
    ack = _ack(session, keys.cmd_write(realm, "plc0"), WriteTag("op", "wash_program", 2.5))
    assert not ack.ok and "expects an int" in ack.error
    ack = _ack(session, keys.cmd_write(realm, "plc0"), WriteTag("op", "ready_to_load", True))
    assert not ack.ok and ack.error == "read_only"
    assert _ack(session, keys.cmd_write(realm, "plc0"), WriteTag("op", "kommentar", "prog A")).ok
    assert core.reported("kommentar") == "prog A"
    ack = _ack(session, keys.cmd_write(realm, "plc0"), WriteTag("intruder", "load_request", True))
    assert not ack.ok and ack.error == "no_control"


def test_force_policy_and_script(stack):
    session, realm, core, backend = stack
    # read-only tag: force needs no lease
    assert _ack(session, keys.cmd_force(realm, "plc0"), ForceTag("nobody", "ready_to_load", True)).ok
    assert core.reported("ready_to_load") is True and _state(session, realm).tags["ready_to_load"].forced
    # rw tag: force needs the lease
    ack = _ack(session, keys.cmd_force(realm, "plc0"), ForceTag("nobody", "load_request", True))
    assert not ack.ok and ack.error == "no_control"
    assert _ack(session, keys.cmd_force(realm, "plc0"), ForceTag("op", "load_request", True)).ok
    ack = _ack(session, keys.cmd_write(realm, "plc0"), WriteTag("op", "load_request", False))
    assert not ack.ok and ack.error == "forced"
    assert _ack(session, keys.cmd_force(realm, "plc0"), ForceTag("op", "load_request", None)).ok
    # the script drove DoorOpen (auto tag door_open) high
    assert _wait(lambda: core.reported("door_open") is True, timeout_s=3.0)


def test_unknown_inventory_tag_rejected():
    from wf.contracts.tags.messages import parse_tags
    from wf.hal.tags_core.core import resolve_tags

    with pytest.raises(ValueError, match="unknown inventory tag"):
        resolve_tags(parse_tags({"x": {"tag": "Nope"}}), [], explicit={"x": {"tag": "Nope"}})
