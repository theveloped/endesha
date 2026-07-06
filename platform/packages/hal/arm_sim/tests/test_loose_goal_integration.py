"""Loose-goal (free-DOF) integration over the ArmCore accept+execute seam.

Drives ``_accept_execute_path`` -> ``_execute_path`` without zenoh: an ArmCore
is built via ``object.__new__`` wired with a fake backend (records ``run_path``
instead of streaming) and fake session/live layers. The sampling + IK + prune
math is proven in ``world_model/tests/test_goal_sampling.py``; this checks the
driver glue — deferred resolution, accept-time pruning, and fastest-candidate
selection at execute.
"""

from __future__ import annotations

import threading

import numpy as np
import pytest

from wf.contracts.arm import keys
from wf.core.frametree import FrameDef, FrameTree
from wf.core.lease import ControlLease
from wf.hal.arm_core import ArmCore
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.collision import CollisionModel
from wf.world_model.fk import UrdfFk
from wf.world_model.validate import TCP_FLANGE

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
BASE = "arm/r1/base"
DT = 0.005


class _FakeBackend:
    def __init__(self):
        self.ran = None

    def motion_block_reason(self, for_goal=True):
        return None

    def latest_q(self):
        return list(HOME_Q)

    def run_path(self, handle, traj, wp_idx, targets, snapshot):
        self.ran = {"traj": traj, "wp_idx": wp_idx, "targets": targets,
                    "snapshot": snapshot}


class _FakeSession:
    def __init__(self):
        self.puts = []

    def put(self, key, payload):
        self.puts.append((key, payload))


class _FakeLive:
    def __init__(self, value):
        self._value = value

    def refresh_static(self, session):
        pass

    def snapshot(self):
        return self._value


class _FakeHandle:
    def __init__(self, goal):
        self.goal = goal
        self.goal_id = "g1"
        self.failed = None

    def fail(self, error=None):
        self.failed = error


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


@pytest.fixture(scope="module")
def collision() -> CollisionModel:
    return CollisionModel(BUNDLED_URDF, BUNDLED_URDF.parent.parent)


def _core(fk, collision, scene=None):
    core = object.__new__(ArmCore)
    core.rid = "r1"
    core.realm = "test"
    core.driver_version = "t"
    core.base_frame = keys.base_frame("r1")
    core.fk = fk
    core.collision = collision
    core.servo_dt = DT
    core.session = _FakeSession()
    core.backend = _FakeBackend()
    tree = FrameTree(
        {"arm/r1/base": FrameDef(parent="world", xyz=[0, 0, 0], quat=[0, 0, 0, 1])}
    )
    core._live_frames = _FakeLive(tree)
    core._live_scene = _FakeLive(scene or [])
    core._tcp_lock = threading.Lock()
    core._active_tcp = (TCP_FLANGE, np.eye(4))
    core._jog_lock = threading.Lock()
    core._jog_active = False
    core._external_stop = threading.Event()
    core._lease = ControlLease(30.0)
    core._lease.acquire("c1", "tester")
    limits = fk.get_joint_limits()
    ordered = [limits[name] for name in fk.JOINT_ORDER]
    core.jmin = [lo for lo, _ in ordered]
    core.jmax = [hi for _, hi in ordered]
    core.params = {
        "joint_limit_margin_rad": 0.01,
        "max_goal_candidates": 256,
        "ruckig_defaults": {"vmax": [1.5] * 6, "amax": [3.0] * 6, "jmax": [20.0] * 6},
    }
    return core


def _free_yaw_goal(fk):
    T = fk.get_ee_transform(HOME_Q)
    from wf.core.frames import rotation_matrix_to_quaternion

    pose = {
        "frame": BASE,
        "xyz": [float(v) for v in T[:3, 3]],
        "quat": rotation_matrix_to_quaternion(T[:3, :3]),
    }
    return {
        "client_id": "c1",
        "waypoints": [
            {"type": "movej", "target": {"pose": pose, "free": {"dof": "yaw"}}}
        ],
    }


def test_loose_goal_accepts_and_executes_fastest(fk, collision):
    core = _core(fk, collision)
    goal = _free_yaw_goal(fk)

    reason = core._accept_execute_path(goal)
    assert reason is None
    entry = goal["_resolution"]["waypoints"][-1]
    assert entry["candidates"], "gate must leave pruned candidates"

    handle = _FakeHandle(goal)
    core._execute_path(handle)
    assert handle.failed is None
    assert core.backend.ran is not None, "run_path must be called"
    traj = core.backend.ran["traj"]
    assert len(traj) > 0
    # The executed final target is one of the accepted candidates.
    chosen = core.backend.ran["targets"][-1]
    assert any(np.allclose(chosen, c, atol=1e-9) for c in entry["candidates"])
    # Snapshot records the chosen pose provenance.
    assert entry["resolved_q"] == chosen


def test_loose_goal_unreachable_is_no_feasible_goal(fk, collision):
    core = _core(fk, collision)
    goal = _free_yaw_goal(fk)
    # Push the target far out of reach: no yaw sample can be solved.
    goal["waypoints"][0]["target"]["pose"]["xyz"] = [5.0, 0.0, 0.0]

    reason = core._accept_execute_path(goal)
    assert reason == "no_feasible_goal:0"


def test_loose_goal_all_finals_blocked_is_no_feasible_goal(fk, collision):
    T = fk.get_ee_transform(HOME_Q)
    from wf.core.scene import SceneObject

    blocker = SceneObject(
        frame=BASE, xyz=[float(v) for v in T[:3, 3]], quat=[0, 0, 0, 1],
        geometry={"type": "box", "size": [0.4, 0.4, 0.4]}, meta={"name": "blk"},
    )
    core = _core(fk, collision, scene=[blocker])
    goal = _free_yaw_goal(fk)

    reason = core._accept_execute_path(goal)
    assert reason == "no_feasible_goal:0"
