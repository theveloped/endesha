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
        "manipulability_floor": 0.02,
        "branch_jump_tol_rad": 0.8,
        "ruckig_defaults": {"vmax": [1.5] * 6, "amax": [3.0] * 6, "jmax": [20.0] * 6},
        "cartesian_defaults": {
            "vmax_lin": 0.25, "amax_lin": 1.0, "jmax_lin": 5.0,
            "vmax_ang": 1.0, "amax_ang": 4.0, "jmax_ang": 20.0,
        },
    }
    return core


def _free_yaw_goal(fk, free=None):
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
            {"type": "movej",
             "target": {"pose": pose, "free": free or {"dof": "yaw"}}}
        ],
    }


# Coarse sweep (few candidates) for the negative tests — the outcome doesn't
# depend on resolution, and it keeps the per-candidate IK count (hence runtime)
# small when every sample fails.
_COARSE_YAW = {"dof": "yaw", "min": -3.14159, "max": 3.14159, "step": 1.05}


def test_loose_goal_uses_nominal_when_feasible(fk, collision):
    core = _core(fk, collision)
    goal = _free_yaw_goal(fk)  # goal pose == current home flange pose

    # Accept must be FAST: it defers sampling/IK to execute (no candidates yet),
    # so it never blocks the client's query timeout.
    reason = core._accept_execute_path(goal)
    assert reason is None
    entry = goal["_resolution"]["waypoints"][-1]
    assert "candidates" not in entry  # deferred to execute

    handle = _FakeHandle(goal)
    core._execute_path(handle)
    assert handle.failed is None
    assert core.backend.ran is not None, "run_path must be called"
    assert len(core.backend.ran["traj"]) > 0
    chosen = core.backend.ran["targets"][-1]
    assert entry["resolved_q"] == chosen
    # Freedom as FALLBACK: the exact (nominal) pose is reachable + collision-free,
    # so it is used directly — the solution is the nominal IK (~HOME_Q), not a
    # swept yaw.
    assert np.allclose(chosen, HOME_Q, atol=1e-2)


def test_loose_goal_unreachable_fails_in_execute(fk, collision):
    core = _core(fk, collision)
    goal = _free_yaw_goal(fk, free=_COARSE_YAW)
    # Push the target far out of reach: no yaw sample can be solved.
    goal["waypoints"][0]["target"]["pose"]["xyz"] = [5.0, 0.0, 0.0]

    assert core._accept_execute_path(goal) is None  # accepted (deferred)
    handle = _FakeHandle(goal)
    core._execute_path(handle)
    assert handle.failed == "no_feasible_goal:0"
    assert core.backend.ran is None


def test_loose_goal_all_finals_blocked_fails_in_execute(fk, collision):
    T = fk.get_ee_transform(HOME_Q)
    from wf.core.scene import SceneObject

    blocker = SceneObject(
        frame=BASE, xyz=[float(v) for v in T[:3, 3]], quat=[0, 0, 0, 1],
        geometry={"type": "box", "size": [0.4, 0.4, 0.4]}, meta={"name": "blk"},
    )
    core = _core(fk, collision, scene=[blocker])
    goal = _free_yaw_goal(fk, free=_COARSE_YAW)

    assert core._accept_execute_path(goal) is None  # accepted (deferred)
    handle = _FakeHandle(goal)
    core._execute_path(handle)
    assert handle.failed == "no_feasible_goal:0"


# ── movel (Cartesian) integration ────────────────────────────────────────


def _movel_goal(fk, dx=0.08):
    from wf.core.frames import rotation_matrix_to_quaternion

    T = fk.get_ee_transform(HOME_Q)
    pose = {
        "frame": BASE,
        "xyz": [float(T[0, 3] + dx), float(T[1, 3]), float(T[2, 3])],
        "quat": rotation_matrix_to_quaternion(T[:3, :3]),
    }
    return {
        "client_id": "c1",
        "waypoints": [{"type": "movel", "target": {"pose": pose}}],
    }


def test_movel_accepts_and_executes_straight_line(fk, collision):
    core = _core(fk, collision)
    goal = _movel_goal(fk)

    reason = core._accept_execute_path(goal)
    assert reason is None
    assert goal["_resolution"]["waypoints"][0]["type"] == "movel"

    handle = _FakeHandle(goal)
    core._execute_path(handle)
    assert handle.failed is None
    ran = core.backend.ran
    assert ran is not None and len(ran["traj"]) > 0
    # The executed TCP endpoint sits on a straight line +8 cm along base-x.
    p_start = fk.get_ee_transform(HOME_Q)[:3, 3]
    p_end = fk.get_ee_transform(ran["traj"][-1])[:3, 3]
    assert p_end[0] == pytest.approx(p_start[0] + 0.08, abs=2e-3)
    assert p_end[1] == pytest.approx(p_start[1], abs=2e-3)
    assert p_end[2] == pytest.approx(p_start[2], abs=2e-3)
    # Midpoint stays on the line (Cartesian-straight, not joint-straight).
    p_mid = fk.get_ee_transform(ran["traj"][len(ran["traj"]) // 2])[:3, 3]
    assert p_mid[1] == pytest.approx(p_start[1], abs=1e-3)
    assert p_mid[2] == pytest.approx(p_start[2], abs=1e-3)


# ── movel + free (path-loose) integration ────────────────────────────────


def _path_loose_goal(fk, dx=0.06):
    from wf.core.frames import rotation_matrix_to_quaternion

    T = fk.get_ee_transform(HOME_Q)
    pose = {
        "frame": BASE,
        "xyz": [float(T[0, 3] + dx), float(T[1, 3]), float(T[2, 3])],
        "quat": rotation_matrix_to_quaternion(T[:3, :3]),
    }
    return {
        "client_id": "c1",
        "waypoints": [
            {"type": "movel", "target": {"pose": pose, "free": {"dof": "yaw"}}}
        ],
    }


def test_path_loose_accepts_and_executes(fk, collision):
    core = _core(fk, collision)
    goal = _path_loose_goal(fk)

    reason = core._accept_execute_path(goal)
    assert reason is None
    assert "path_loose" in goal["_resolution"]["waypoints"][-1]

    handle = _FakeHandle(goal)
    core._execute_path(handle)
    assert handle.failed is None
    ran = core.backend.ran
    assert ran is not None and len(ran["traj"]) > 0
    # TCP reaches the goal position (yaw free along the path).
    p_start = fk.get_ee_transform(HOME_Q)[:3, 3]
    xs = [fk.get_ee_transform(q)[0, 3] for q in ran["traj"]]
    p_end = fk.get_ee_transform(ran["traj"][-1])[:3, 3]
    assert np.linalg.norm(p_end - (p_start + np.array([0.06, 0, 0]))) < 5e-3
    # FLUID: the TCP advances monotonically along the straight line — no
    # back-and-forth (the symptom that motivated dropping the DP corridor).
    assert all(b >= a - 1e-4 for a, b in zip(xs, xs[1:]))
    # And no branch flip between samples.
    for a, b in zip(ran["traj"], ran["traj"][1:]):
        assert max(abs(x - y) for x, y in zip(a, b)) < 0.8


def test_path_loose_unreachable_fails_in_execute(fk, collision):
    core = _core(fk, collision)
    goal = _path_loose_goal(fk)
    goal["waypoints"][0]["target"]["free"] = _COARSE_YAW
    goal["waypoints"][0]["target"]["pose"]["xyz"] = [5.0, 0.0, 0.0]
    # Accept defers (fast); the movel fallback finds no feasible orientation to
    # an unreachable goal and fails in execute.
    assert core._accept_execute_path(goal) is None
    handle = _FakeHandle(goal)
    core._execute_path(handle)
    assert handle.failed == "movel:no_feasible_path"
    assert core.backend.ran is None
