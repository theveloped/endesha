"""WasherCore over the sim PLC, end to end on the bus: phases, the four
actions, cancel stops the door, recipes, lease gating, the provided tags
device (German auto names + cell names), fault + reset."""

from __future__ import annotations

import time
import uuid

import pytest

from wf.contracts.control import keys as control_keys
from wf.contracts.control.authority import ControlAuthority
from wf.contracts.control.messages import AcquireControl
from wf.contracts.tags import keys as tags_keys
from wf.contracts.tags.messages import ForceTag, TagsState
from wf.core.envelope import request as envelope_request
from wf.contracts.washer import keys
from wf.contracts.washer.messages import Ack, Recipe, RecipeReply, RecipeStep, SetRecipe, WasherStatus
from wf.core.action import ActionClient, ActionRejected
from wf.core.codec import decode, encode
from wf.hal.ecoclean import EcocleanSimBackend, WasherCore

zenoh = pytest.importorskip("zenoh")

PARAMS = {
    "time_scale": 0.05,  # 3 s door -> 150 ms; 90 s recipe -> 4.5 s
    "door_travel_s": 3.0,
    "settle_s": 0.02,
    "provides": {
        "plc0": {
            "contract": "tags",
            "tags": {"machine_ready": {"tag": "ReadyToLoad"}, "fault_no": {"tag": "stoernummer"}},
        }
    },
}


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
        time.sleep(0.02)
    return pred()


class Rig:
    def __init__(self, params=PARAMS):
        self.session = zenoh.open(zenoh.Config())
        self.realm = f"t{uuid.uuid4().hex[:8]}"
        self.authority = ControlAuthority(self.session, self.realm, ttl_s=30.0)
        self.authority.start()
        self.backend = EcocleanSimBackend(params)
        self.core = WasherCore(self.session, self.realm, "washer0", params, self.backend)
        self.core.start()
        _query(self.session, control_keys.cmd_acquire(self.realm), AcquireControl("op", "alice").to_wire())
        assert _wait(lambda: self.core._lease.holds("op"))

    def close(self):
        self.core.shutdown()
        self.authority.close()
        self.session.close()

    def status(self) -> WasherStatus:
        return WasherStatus.from_wire(_query(self.session, keys.state_status(self.realm, "washer0"), {}))

    def phase(self) -> str:
        return self.status().phase

    def action(self, name, *, client_id="op", timeout_s=20.0, **goal) -> dict:
        client = ActionClient(self.session, keys.action_prefix(self.realm, "washer0"), name)
        g = client.send({"client_id": client_id, **goal})
        return g.result(timeout_s=timeout_s)


@pytest.fixture
def rig():
    r = Rig()
    yield r
    r.close()


def test_full_cycle(rig):
    assert _wait(lambda: rig.phase() == "ready_to_load")
    st = rig.status()
    assert st.door == "closed" and st.connected and st.auto and st.program == "Standard"

    assert rig.action("open_door")["state"] == "succeeded"
    assert rig.phase() == "door_open"
    # the handshake left the machine as the old controller did
    assert rig.core.get("LoadRequest") is True and rig.core.get("PermissionToClose") is False

    # a wrong-phase action is rejected before it runs
    with pytest.raises(ActionRejected, match="wrong_phase:door_open"):
        rig.action("open_door")

    res = rig.action("start_wash", program=3)
    assert res["state"] == "succeeded", res
    assert rig.phase() == "washing"
    assert rig.status().program_no == 3
    assert rig.core.get("LoadComplete") is False  # cleared once the door closed
    # recipe: steps 1 (60 s) + 2 (30 s) => 90 s * 0.05 = 4.5 s
    assert _wait(lambda: rig.phase() == "ready_to_unload", timeout_s=15.0)

    assert rig.action("open_door")["state"] == "succeeded"
    assert rig.phase() == "door_open"
    assert rig.status().ready_to_load and not rig.status().ready_to_unload
    assert rig.core.get("UnLoadComplete") is False and rig.core.get("LoadRequest") is True

    assert rig.action("close_door")["state"] == "succeeded"
    assert rig.phase() == "ready_to_load"


def test_cancel_stops_the_door_and_stop_door_cmd():
    rig = Rig({**PARAMS, "door_travel_s": 60.0})  # 3 s door at 0.05
    try:
        _cancel_case(rig)
    finally:
        rig.close()


def _cancel_case(rig):
    assert _wait(lambda: rig.phase() == "ready_to_load")
    client = ActionClient(rig.session, keys.action_prefix(rig.realm, "washer0"), "open_door")
    goal = client.send({"client_id": "op"})
    assert _wait(lambda: rig.status().door == "moving", timeout_s=5.0)
    goal.cancel()
    res = goal.result(timeout_s=5.0)
    assert res["state"] == "canceled"
    # permission released -> door stays where it is
    assert rig.core.get("PermissionToClose") is False
    time.sleep(0.3)
    assert rig.status().door == "moving" and rig.phase() == "door_moving"
    assert rig.status().sequence is None
    # reset re-arms permission -> the door finishes its travel
    assert rig.action("reset")["state"] == "succeeded"
    assert _wait(lambda: rig.phase() == "door_open", timeout_s=8.0)
    # stop_door is a plain lease-gated command
    ack = Ack.from_wire(_query(rig.session, keys.cmd_stop_door(rig.realm, "washer0"), {"client_id": "op"}))
    assert ack.ok and rig.core.get("PermissionToClose") is False
    ack = Ack.from_wire(_query(rig.session, keys.cmd_stop_door(rig.realm, "washer0"), {"client_id": "bob"}))
    assert ack.error == "no_control"


def test_lease_gating(rig):
    assert _wait(lambda: rig.phase() == "ready_to_load")
    with pytest.raises(ActionRejected, match="no_control"):
        rig.action("open_door", client_id="bob")


def test_recipe_round_trip_and_validation(rig):
    reply = RecipeReply.from_wire(_query(rig.session, keys.cmd_get_recipe(rig.realm, "washer0"), {}))
    assert reply.ok and reply.recipe.name == "Standard" and reply.schema.steps == 10
    assert reply.recipe.steps[0] == RecipeStep(cleaning=1, time_s=60)
    assert reply.recipe.params["rpm"] == 4

    new = Recipe(name="Quick", steps=[RecipeStep(1, 20, 2, 0, True), RecipeStep(4, 40)], params={"rpm": 6, "swing_angle": 45})
    ack = Ack.from_wire(_query(rig.session, keys.cmd_set_recipe(rig.realm, "washer0"), SetRecipe("op", new).to_wire()))
    assert ack.ok, ack
    reply = RecipeReply.from_wire(_query(rig.session, keys.cmd_get_recipe(rig.realm, "washer0"), {}))
    assert reply.recipe.name == "Quick"
    assert reply.recipe.steps[:2] == new.steps and reply.recipe.steps[2] == RecipeStep()
    assert reply.recipe.params["rpm"] == 6 and reply.recipe.params["swing_angle"] == 45
    assert rig.status().program == "Quick"
    # the raw PLC variables moved too (visible on the provided tags device)
    st = TagsState.from_wire(_query(rig.session, tags_keys.state_tags(rig.realm, "plc0"), {}))
    assert st.tags["programmfolgen_0_zeit"].value == 20 and st.tags["kommentar"].value == "Quick"

    bad = Recipe(name="Bad", steps=[RecipeStep(1, 5000)])
    ack = Ack.from_wire(_query(rig.session, keys.cmd_set_recipe(rig.realm, "washer0"), SetRecipe("op", bad).to_wire()))
    assert ack.error == "bad_recipe:steps[0].time_s > 600"
    ack = Ack.from_wire(_query(rig.session, keys.cmd_set_recipe(rig.realm, "washer0"), SetRecipe("bob", new).to_wire()))
    assert ack.error == "no_control"


def test_provided_tags_device_and_fault(rig):
    st = TagsState.from_wire(_query(rig.session, tags_keys.state_tags(rig.realm, "plc0"), {}))
    # cell names + German auto names
    assert st.tags["machine_ready"].value is True and st.tags["machine_ready"].auto is False
    assert st.tags["door_closed"].auto is True and st.tags["door_closed"].value is True
    assert "load_request" in st.tags and "programmfolgen_9_abpump" in st.tags
    assert "ready_to_load" not in st.tags  # named -> no auto twin

    # force a fault on the read-only PLC line (no lease needed) -> phase fault
    ack = envelope_request(rig.session, tags_keys.cmd_force(rig.realm, "plc0"),
                           ForceTag("general_fault", True).to_wire(), client_id="nobody")
    assert ack.ok, ack.error
    assert _wait(lambda: rig.phase() == "fault")
    with pytest.raises(ActionRejected, match="wrong_phase:fault"):
        rig.action("open_door")
    envelope_request(rig.session, tags_keys.cmd_force(rig.realm, "plc0"),
                     ForceTag("general_fault", None).to_wire(), client_id="nobody")
    assert _wait(lambda: rig.phase() == "ready_to_load")


def test_sim_fault_injection_and_reset():
    rig = Rig({**PARAMS, "fault_at_s": 20})
    try:
        assert _wait(lambda: rig.phase() == "ready_to_load")
        assert rig.action("open_door")["state"] == "succeeded"
        assert rig.action("start_wash")["state"] == "succeeded"
        assert _wait(lambda: rig.phase() == "fault", timeout_s=10.0)
        assert rig.status().fault_code == 42
        assert rig.action("reset")["state"] == "succeeded"
        assert _wait(lambda: not rig.status().fault)
    finally:
        rig.close()
