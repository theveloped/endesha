"""resolve_goal tests (pure parts only — no zenoh).

The q-form validation cases are ported verbatim from the deleted
``arm_sim/sim.py::validate_goal`` tests (same reason-string asserts).
"""

from __future__ import annotations

import numpy as np
import pytest

from wf.core.frames import (
    invert_transform,
    make_transform,
    rotation_matrix_to_quaternion,
    rotation_matrix_to_rotvec,
)
from wf.core.frametree import FrameDef, FrameTree
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.fk import UrdfFk
from wf.world_model.validate import TCP_FLANGE, resolve_goal, tcp_transform

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
_MARGIN = 0.01

_TABLE_XYZ = [0.6, 0.0, 0.0]


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


@pytest.fixture(scope="module")
def limits(fk) -> tuple[list[float], list[float]]:
    all_limits = fk.get_joint_limits()
    ordered = [all_limits[name] for name in fk.JOINT_ORDER]
    return [lo for lo, _ in ordered], [hi for _, hi in ordered]


@pytest.fixture()
def tree() -> FrameTree:
    return FrameTree(
        {
            "arm/r1/base": FrameDef(parent="world", xyz=[0, 0, 0], quat=[0, 0, 0, 1]),
            "table": FrameDef(parent="world", xyz=_TABLE_XYZ, quat=[0, 0, 0, 1]),
        }
    )


def _goal(waypoints) -> dict:
    return {"waypoints": waypoints}


def _resolve(goal, fk, limits, tree, *, tcp_name=TCP_FLANGE, tcp_T=None):
    jmin, jmax = limits
    return resolve_goal(
        goal,
        fk=fk,
        rid="r1",
        q_start=HOME_Q,
        jmin=jmin,
        jmax=jmax,
        margin=_MARGIN,
        tree=tree,
        tcp_name=tcp_name,
        tcp_T=np.eye(4) if tcp_T is None else tcp_T,
    )


# ── q-form (ported from the deleted validate_goal tests) ─────────────────


def test_accepts_movej_near_home(fk, limits, tree):
    goal = _goal([{"type": "movej", "target": {"q": HOME_Q}}])
    reason, resolution = _resolve(goal, fk, limits, tree)
    assert reason is None
    assert resolution["waypoints"][0]["resolved_q"] == HOME_Q
    assert resolution["active_tcp"] == TCP_FLANGE
    assert resolution["frames_used"] == {}
    assert goal["_resolution"] is resolution


def test_empty_path(fk, limits, tree):
    reason, _ = _resolve(_goal([]), fk, limits, tree)
    assert reason == "empty_path"


def test_unsupported_waypoint_type(fk, limits, tree):
    goal = _goal([{"type": "movel", "target": {"q": HOME_Q}}])
    reason, _ = _resolve(goal, fk, limits, tree)
    assert reason == "unsupported_waypoint_type"


def test_target_outside_limits(fk, limits, tree):
    q = list(HOME_Q)
    q[0] = limits[1][0] + 1.0  # 1 rad past the upper limit
    goal = _goal([{"type": "movej", "target": {"q": q}}])
    reason, _ = _resolve(goal, fk, limits, tree)
    assert reason == "target_outside_limits"


def test_bad_goal(fk, limits, tree):
    reason, _ = _resolve("garbage", fk, limits, tree)
    assert reason.startswith("bad_goal")


def test_both_q_and_pose_rejected(fk, limits, tree):
    goal = _goal(
        [
            {
                "type": "movej",
                "target": {
                    "q": HOME_Q,
                    "pose": {"frame": "table", "xyz": [0, 0, 0.3], "quat": [0, 0, 0, 1]},
                },
            }
        ]
    )
    reason, _ = _resolve(goal, fk, limits, tree)
    assert reason == "bad_goal: target must have exactly one of q|pose"


# ── pose form ────────────────────────────────────────────────────────────


def test_pose_target_happy_path_injects_q(fk, limits, tree):
    T_home = fk.get_ee_transform(HOME_Q)
    pose = {
        "frame": "arm/r1/base",
        "xyz": [float(v) for v in T_home[:3, 3]],
        "quat": rotation_matrix_to_quaternion(T_home[:3, :3]),
    }
    goal = _goal([{"type": "movej", "target": {"pose": pose}}])
    reason, resolution = _resolve(goal, fk, limits, tree)
    assert reason is None
    q = goal["waypoints"][0]["target"]["q"]
    assert len(q) == 6
    # FK of the injected q lands back on the requested pose.
    T_sol = fk.get_ee_transform(q)
    assert np.linalg.norm(T_sol[:3, 3] - T_home[:3, 3]) < 1e-3
    # Original pose is kept alongside the injected q.
    assert goal["waypoints"][0]["target"]["pose"] == pose
    assert resolution["waypoints"][0]["resolved_q"] == q


def test_pose_target_unknown_frame(fk, limits, tree):
    goal = _goal(
        [
            {
                "type": "movej",
                "target": {"pose": {"frame": "nope", "xyz": [0, 0, 0], "quat": [0, 0, 0, 1]}},
            }
        ]
    )
    reason, _ = _resolve(goal, fk, limits, tree)
    assert reason == "frame_unknown:nope"


def test_pose_target_unreachable_is_ik_failure(fk, limits, tree):
    goal = _goal(
        [
            {
                "type": "movej",
                "target": {"pose": {"frame": "table", "xyz": [5, 0, 0], "quat": [0, 0, 0, 1]}},
            }
        ]
    )
    reason, _ = _resolve(goal, fk, limits, tree)
    assert reason == "ik_failure:0"


def test_pose_target_records_frames_used(fk, limits, tree):
    T_home = fk.get_ee_transform(HOME_Q)
    # Express the home flange pose in the table frame.
    xyz_in_table = [float(v) for v in (T_home[:3, 3] - np.asarray(_TABLE_XYZ))]
    goal = _goal(
        [
            {
                "type": "movej",
                "target": {
                    "pose": {
                        "frame": "table",
                        "xyz": xyz_in_table,
                        "quat": rotation_matrix_to_quaternion(T_home[:3, :3]),
                    }
                },
            }
        ]
    )
    reason, resolution = _resolve(goal, fk, limits, tree)
    assert reason is None
    assert set(resolution["frames_used"]) == {"table", "arm/r1/base"}
    assert resolution["frames_used"]["table"]["xyz"] == _TABLE_XYZ


def test_tcp_composition_backs_off_flange(fk, limits, tree):
    """Target pose with a 0.12 m z TCP: resolved flange FK ≈ pose @ inv(tcp_T)."""
    tcp_def = {"xyz": [0.0, 0.0, 0.12], "quat": [0.0, 0.0, 0.0, 1.0]}
    tcp_T = tcp_transform(tcp_def)

    T_home = fk.get_ee_transform(HOME_Q)
    # Ask the TCP TIP to sit where the flange is now, expressed in table frame.
    xyz_in_table = [float(v) for v in (T_home[:3, 3] - np.asarray(_TABLE_XYZ))]
    quat = rotation_matrix_to_quaternion(T_home[:3, :3])
    goal = _goal(
        [
            {
                "type": "movej",
                "target": {"pose": {"frame": "table", "xyz": xyz_in_table, "quat": quat}},
            }
        ]
    )
    reason, resolution = _resolve(
        goal, fk, limits, tree, tcp_name="tool0", tcp_T=tcp_T
    )
    assert reason is None
    assert resolution["active_tcp"] == "tool0"
    T_expected_flange = T_home @ invert_transform(tcp_T)
    T_sol = fk.get_ee_transform(goal["waypoints"][0]["target"]["q"])
    assert np.linalg.norm(T_sol[:3, 3] - T_expected_flange[:3, 3]) < 1e-3
    assert (
        np.linalg.norm(
            rotation_matrix_to_rotvec(T_expected_flange[:3, :3] @ T_sol[:3, :3].T)
        )
        < 1e-2
    )


# ── loose end goal (free block) ──────────────────────────────────────────


def _pose_at_home(fk):
    T = fk.get_ee_transform(HOME_Q)
    return {
        "frame": "arm/r1/base",
        "xyz": [float(v) for v in T[:3, 3]],
        "quat": rotation_matrix_to_quaternion(T[:3, :3]),
    }


def test_free_on_last_waypoint_records_constrained(fk, limits, tree):
    pose = _pose_at_home(fk)
    goal = _goal(
        [{"type": "movej", "target": {"pose": pose, "free": {"dof": "yaw"}}}]
    )
    reason, resolution = _resolve(goal, fk, limits, tree)
    assert reason is None
    entry = resolution["waypoints"][-1]
    assert "constrained" in entry
    assert "resolved_q" not in entry  # deferred to the gate
    assert entry["constrained"]["free"]["dof"] == "yaw"
    assert entry["seed_q"] == HOME_Q
    assert "q" not in goal["waypoints"][0]["target"]  # no q injected


def test_free_on_non_last_waypoint_rejected(fk, limits, tree):
    pose = _pose_at_home(fk)
    goal = _goal(
        [
            {"type": "movej", "target": {"pose": pose, "free": {"dof": "yaw"}}},
            {"type": "movej", "target": {"q": HOME_Q}},
        ]
    )
    reason, _ = _resolve(goal, fk, limits, tree)
    assert reason == "unsupported_constraint"


def test_free_requires_pose_not_q(fk, limits, tree):
    goal = _goal(
        [{"type": "movej", "target": {"q": HOME_Q, "free": {"dof": "yaw"}}}]
    )
    reason, _ = _resolve(goal, fk, limits, tree)
    # q+pose mutual-exclusion fires first; either way it's a bad_goal.
    assert reason.startswith("bad_goal")


def test_free_malformed_is_bad_goal(fk, limits, tree):
    pose = _pose_at_home(fk)
    goal = _goal(
        [{"type": "movej", "target": {"pose": pose, "free": {"dof": "spin"}}}]
    )
    reason, _ = _resolve(goal, fk, limits, tree)
    assert reason.startswith("bad_goal")


def test_multi_waypoint_seed_chains(fk, limits, tree):
    """Waypoint 1 (pose) seeds from waypoint 0's given q."""
    q0 = [v + 0.2 for v in HOME_Q]
    T_q0 = fk.get_ee_transform(q0)
    pose = {
        "frame": "arm/r1/base",
        "xyz": [float(v) for v in T_q0[:3, 3]],
        "quat": rotation_matrix_to_quaternion(T_q0[:3, :3]),
    }
    goal = _goal(
        [
            {"type": "movej", "target": {"q": q0}},
            {"type": "movej", "target": {"pose": pose}},
        ]
    )
    reason, resolution = _resolve(goal, fk, limits, tree)
    assert reason is None
    q1 = resolution["waypoints"][1]["resolved_q"]
    # Seeded from q0 and the pose IS q0's pose -> the solution stays near q0.
    assert max(abs(a - b) for a, b in zip(q0, q1)) < 0.05
