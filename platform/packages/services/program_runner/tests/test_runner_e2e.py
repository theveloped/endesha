"""Runner end-to-end over an in-process zenoh session: authority + simulated
arm (with its provided dio) + a config store answering named poses + the
runner hosting a small program from a temp programs dir.

Covers: load/start (lease acquired by the program), channel-edge trigger,
motion through the arm, cancel-on-Hold (action re-runs after Unhold),
program completion -> Complete, Stop from Held, external event, action error
-> Aborted with reason, safety abort on protective stop, unknown load errors.
"""

from __future__ import annotations

import textwrap
import time
import uuid

import pytest

from wf.contracts.arm import keys as arm_keys
from wf.contracts.control import keys as control_keys
from wf.contracts.control.authority import ControlAuthority
from wf.contracts.control.messages import ControlOwnerState
from wf.contracts.dio import keys as dio_keys
from wf.contracts.dio.messages import ChannelsState, ForceChannel
from wf.core.envelope import request as envelope_request
from wf.contracts.program import keys
from wf.contracts.program.messages import Ack, Catalog, EventRequest, LoadRequest, ProgramState
from wf.core.codec import decode, encode
from wf.hal.arm_core import ArmCore
from wf.hal.arm_sim.backend import SimArmBackend
from wf.hal.arm_sim.config import load_resource
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.services.config import keys as config_keys
from wf.services.program_runner.service import ProgramRunner

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
NEAR_Q = [0.05, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]

PROVIDES = {
    "io0": {
        "contract": "dio",
        "layout": {"di": 4, "do": 4, "tool_do": 0, "ai": 0, "ao": 0},
        "channels": {
            "part_present": {"kind": "di", "bank": "standard", "pin": 0},
            "clamp": {"kind": "do", "bank": "standard", "pin": 0},
        },
    }
}

DEVICES = [
    {"id": "r1", "contract": "arm", "model": "sim", "active": "sim", "config": {}, "sources": []},
    {"id": "io0", "contract": "dio", "model": None, "active": "sim", "config": {"channels": PROVIDES["io0"]["channels"]}, "sources": [], "provided_by": "r1"},
]

PROGRAM_SRC = textwrap.dedent(
    '''
    from wf.program import Program, State, on_channel

    class TestPick(Program):
        """test program"""
        program_name = "tp"
        roles = {"arm": "arm", "io": "dio"}
        params = {"cycles": 1, "fail": False}
        triggers = [on_channel("io", "part_present", edge="rising", event="part")]

        waiting = State(initial=True)
        working = State()
        done = State(final=True)

        part = waiting.to(working)
        finished = working.to(done, cond="enough") | working.to(waiting)
        kick = waiting.to(working)   # external event path

        def __init__(self, roles, params, runtime):
            self.count = 0
            self.runs = 0
            super().__init__(roles, params, runtime)

        def enough(self):
            return self.count >= int(self.p["cycles"])

        def run_working(self, ctx):
            self.runs += 1
            self.log(f"working run {self.runs}")
            if self.p["fail"]:
                raise RuntimeError("boom")
            self.m.io.set("clamp", True)
            self.m.arm.move_j("near")
            self.m.arm.move_j("home")
            self.m.io.set("clamp", False)
            self.count += 1
            self.emit("finished")

    PROGRAM = TestPick
    '''
)


class FakeConfig:
    """Answers config/poses/{name} and config/programs/tp/poses/{name} queries
    (the config service's job). ``program_poses`` shadow cell poses for tp."""

    def __init__(self, session, program_poses: dict | None = None):
        self.program_poses = dict(program_poses or {})
        self.q = session.declare_queryable(config_keys.poses_glob(), self._on_query)
        self.pq = session.declare_queryable(config_keys.programs_glob(), self._on_program_query)

    def _on_query(self, query):
        key = str(query.key_expr)
        name = key.rsplit("/", 1)[-1]
        poses = {"home": HOME_Q, "near": NEAR_Q}
        if name in poses:
            query.reply(key, encode({"q": poses[name]}))

    def _on_program_query(self, query):
        key = str(query.key_expr)
        name = key.rsplit("/", 1)[-1]
        if key.startswith("config/programs/tp/poses/") and name in self.program_poses:
            query.reply(key, encode({"q": self.program_poses[name]}))

    def close(self):
        self.q.undeclare()
        self.pq.undeclare()


def _ack(session, key, payload) -> Ack:
    for reply in session.get(key, payload=encode(payload), timeout=5.0):
        if reply.ok is not None:
            return Ack.from_wire(decode(reply.ok.payload))
    pytest.fail(f"no reply from {key}")


def _state(session, realm) -> ProgramState:
    for reply in session.get(keys.state(realm), timeout=3.0):
        if reply.ok is not None:
            return ProgramState.from_wire(decode(reply.ok.payload))
    pytest.fail("no program state")


def _wait_unit(session, realm, unit: str, timeout_s=15.0) -> ProgramState:
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        last = _state(session, realm)
        if last.unit == unit:
            return last
        time.sleep(0.05)
    pytest.fail(f"unit never reached {unit}; last={last}")


def _wait(pred, timeout_s=10.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.05)
    return pred()


def _owner(session, realm):
    for reply in session.get(control_keys.state_owner(realm), timeout=2.0):
        if reply.ok is not None:
            return ControlOwnerState.from_wire(decode(reply.ok.payload)).owner
    return None


def _clamp(session, realm):
    for reply in session.get(dio_keys.state_channels(realm, "io0"), timeout=2.0):
        if reply.ok is not None:
            return ChannelsState.from_wire(decode(reply.ok.payload)).channels["clamp"].value
    return None


def _force_part(session, realm, value):
    reply = envelope_request(session, dio_keys.cmd_force(realm, "io0"),
                             ForceChannel("part_present", value).to_wire(), client_id="tester")
    assert reply.ok, reply.error


@pytest.fixture
def cell(tmp_path):
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    authority.start()
    config = FakeConfig(session)
    cell_yaml = tmp_path / "cell.yaml"
    cell_yaml.write_text("resources: {r1: {contract: arm, params: {}}}\n", encoding="utf-8")
    params = load_resource(str(cell_yaml), "r1")
    params["urdf"] = BUNDLED_URDF
    params["provides"] = PROVIDES
    backend = SimArmBackend(HOME_Q)
    arm = ArmCore(session, realm, "r1", params, backend)
    arm.start()
    programs = tmp_path / "programs"
    programs.mkdir()
    (programs / "tp.py").write_text(PROGRAM_SRC, encoding="utf-8")
    (programs / "broken.py").write_text("import nonexistent_module_xyz\n", encoding="utf-8")
    runner = ProgramRunner(session, realm, str(programs), devices=DEVICES)
    runner.start()
    time.sleep(0.3)
    yield session, realm, runner, arm, backend
    runner.shutdown()
    arm.shutdown()
    time.sleep(0.1)
    config.close()
    authority.close()
    session.close()


def test_catalog_lists_good_and_broken(cell):
    session, realm, runner, arm, backend = cell
    for reply in session.get(keys.catalog(realm), timeout=3.0):
        if reply.ok is not None:
            cat = Catalog.from_wire(decode(reply.ok.payload))
            break
    else:
        pytest.fail("no catalog")
    by_name = {p.name: p for p in cat.programs}
    assert by_name["tp"].roles == {"arm": "arm", "io": "dio"}
    assert by_name["tp"].params == {"cycles": 1, "fail": False}
    assert by_name["broken"].error and "nonexistent_module_xyz" in by_name["broken"].error


def test_load_errors(cell):
    session, realm, runner, arm, backend = cell
    assert _ack(session, keys.cmd_load(realm), LoadRequest("nope").to_wire()).error == "unknown_program:nope"
    assert _ack(session, keys.cmd_load(realm), LoadRequest("broken").to_wire()).error.startswith("program_broken:")
    assert _ack(session, keys.cmd_load(realm), LoadRequest("tp", params={"zzz": 1}).to_wire()).error == "unknown_params:zzz"
    assert _ack(session, keys.cmd_load(realm), LoadRequest("tp", bindings={"arm": "io0"}).to_wire()).error.startswith("bind:arm:contract_mismatch")
    assert _ack(session, keys.cmd(realm, "start"), {}).error == "no_program_loaded"


def test_run_to_completion_with_trigger_hold_and_lease(cell):
    session, realm, runner, arm, backend = cell
    assert _ack(session, keys.cmd_load(realm), LoadRequest("tp", params={"cycles": 2}).to_wire()).ok
    st = _state(session, realm)
    assert st.unit == "idle" and st.program == "tp" and st.bindings == {"arm": "r1", "io": "io0"}

    assert _ack(session, keys.cmd(realm, "start"), {}).ok
    st = _wait_unit(session, realm, "execute")
    assert st.program_states == ["waiting"] and st.actions == []
    owner = _owner(session, realm)
    assert owner is not None and owner.client_id.startswith("program:tp:")

    # trigger: part_present rising -> working (action runs: clamp on, moves)
    _force_part(session, realm, True)
    assert _wait(lambda: "working" in _state(session, realm).program_states)
    assert _wait(lambda: _clamp(session, realm) is True, timeout_s=5.0)

    # HOLD mid-action: action cancelled (goal cancelled), unit Held, program state kept
    assert _ack(session, keys.cmd(realm, "hold"), {}).ok
    st = _wait_unit(session, realm, "held")
    assert st.program_states == ["working"] and st.actions == []
    assert not backend.core.action_server.active_goal_id or _wait(lambda: arm.action_server.active_goal_id is None, 5.0)

    # UNHOLD: the interrupted state's action re-runs from the top and finishes
    assert _ack(session, keys.cmd(realm, "unhold"), {}).ok
    _wait_unit(session, realm, "execute")
    assert _wait(lambda: "waiting" in _state(session, realm).program_states, timeout_s=20.0)
    assert runner._program.runs == 2  # first run cancelled, second completed
    assert runner._program.count == 1

    # second part -> completes -> Complete; lease released
    _force_part(session, realm, False)
    _force_part(session, realm, True)
    st = _wait_unit(session, realm, "complete", timeout_s=30.0)
    assert st.program_states == ["done"]
    assert _wait(lambda: _owner(session, realm) is None, timeout_s=5.0)

    # reset -> idle, program instance gone, spec kept
    assert _ack(session, keys.cmd(realm, "reset"), {}).ok
    st = _wait_unit(session, realm, "idle")
    assert st.program == "tp" and st.program_states == []
    _force_part(session, realm, None)


def test_external_event_and_stop(cell):
    session, realm, runner, arm, backend = cell
    assert _ack(session, keys.cmd_load(realm), LoadRequest("tp", params={"cycles": 5}).to_wire()).ok
    assert _ack(session, keys.cmd(realm, "start"), {}).ok
    _wait_unit(session, realm, "execute")
    assert _ack(session, keys.cmd_event(realm), EventRequest("nope").to_wire()).error == "unknown_event:nope"
    assert _ack(session, keys.cmd_event(realm), EventRequest("kick").to_wire()).ok
    assert _wait(lambda: "working" in _state(session, realm).program_states)
    assert _ack(session, keys.cmd(realm, "stop"), {}).ok
    st = _wait_unit(session, realm, "stopped")
    assert st.actions == []
    assert _wait(lambda: _owner(session, realm) is None, 5.0)
    # a program event while stopped is refused
    assert _ack(session, keys.cmd_event(realm), EventRequest("kick").to_wire()).error == "invalid_in_state:stopped"
    assert _ack(session, keys.cmd(realm, "reset"), {}).ok
    _wait_unit(session, realm, "idle")


def test_action_error_aborts_with_reason(cell):
    session, realm, runner, arm, backend = cell
    assert _ack(session, keys.cmd_load(realm), LoadRequest("tp", params={"fail": True}).to_wire()).ok
    assert _ack(session, keys.cmd(realm, "start"), {}).ok
    _wait_unit(session, realm, "execute")
    assert _ack(session, keys.cmd_event(realm), EventRequest("kick").to_wire()).ok
    st = _wait_unit(session, realm, "aborted")
    assert st.reason is not None and st.reason.startswith("action_crash:working:") and "boom" in st.reason
    assert not runner.unit.accepts("start")
    assert _ack(session, keys.cmd(realm, "clear"), {}).ok
    _wait_unit(session, realm, "stopped")
    assert _ack(session, keys.cmd(realm, "reset"), {}).ok
    _wait_unit(session, realm, "idle")


def test_program_scoped_pose_shadows_cell_pose(cell):
    """RFC §3.7: config/programs/{name}/poses/{p} wins over config/poses/{p}."""
    session, realm, runner, arm, backend = cell
    shadow_q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.3]
    cfg = FakeConfig(session, program_poses={"near": shadow_q})
    try:
        assert _ack(session, keys.cmd_load(realm), LoadRequest("tp").to_wire()).ok
        assert _ack(session, keys.cmd(realm, "start"), {}).ok
        _wait_unit(session, realm, "execute")
        assert _ack(session, keys.cmd_event(realm), EventRequest("kick").to_wire()).ok
        # the "near" move must go to the program-scoped q (joint 5 = 0.3)
        assert _wait(lambda: backend.core.backend.latest_q() is not None and abs(backend.core.backend.latest_q()[5] - 0.3) < 0.02, timeout_s=15.0)
        _wait_unit(session, realm, "complete", timeout_s=30.0)
    finally:
        cfg.close()


def test_protective_stop_aborts(cell):
    session, realm, runner, arm, backend = cell
    assert _ack(session, keys.cmd_load(realm), LoadRequest("tp").to_wire()).ok
    assert _ack(session, keys.cmd(realm, "start"), {}).ok
    _wait_unit(session, realm, "execute")
    # Fake an arm safety stop by publishing status ourselves.
    arm.publish_status(mode="Simulated", servo_on=True, estop=False, protective_stop=True, speed_scale=1.0, error=None)
    st = _wait_unit(session, realm, "aborted")
    assert st.reason == "safety:protective_stop"
