"""Unit tests for the pure sim state (no zenoh, no threads).

Goal validation moved to the shared ``wf.world_model.validate.resolve_goal``
(tested in ``packages/world_model/tests/test_validate.py``). Bus-level
lifecycle (streams, actions, cancel/busy) is covered by the arm conformance
suite run against the live driver process.
"""

from __future__ import annotations

import math

import pytest

from wf.hal.arm_sim.sim import SimArm, pose_from_transform
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.fk import UrdfFk

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


@pytest.fixture()
def arm(fk) -> SimArm:
    return SimArm(fk, HOME_Q)


# ── set_do ───────────────────────────────────────────────────────────────


def test_set_do_standard_sets_and_clears_bit(arm):
    arm.set_do("standard", 3, 1)
    assert arm.do_bits == 1 << 3
    arm.set_do("standard", 3, 0)
    assert arm.do_bits == 0


def test_set_do_tool_does_not_touch_standard_bank(arm):
    arm.set_do("tool", 2, 1)
    assert arm.do_bits == 0
    assert arm.tool_do_bits == 1 << 2


@pytest.mark.parametrize(
    ("bank", "pin", "value"),
    [
        ("standard", 16, 1),  # pin out of range (0-15)
        ("tool", 4, 1),  # pin out of range (0-3)
        ("bogus", 0, 1),  # unknown bank
        ("standard", 0, 2),  # bad value
    ],
)
def test_set_do_rejects_bad_input(arm, bank, pin, value):
    with pytest.raises(ValueError):
        arm.set_do(bank, pin, value)


# ── flange_pose ──────────────────────────────────────────────────────────


def test_flange_pose_frame_and_unit_quaternion(arm):
    pose = arm.flange_pose("r1")
    assert pose.frame == "arm/r1/base"
    norm = math.sqrt(sum(v * v for v in pose.quat))
    assert abs(norm - 1.0) < 1e-6


def test_flange_pose_tracks_joint_state(arm):
    home_xyz = arm.flange_pose("r1").xyz
    arm.set_q([0.0] * 6)
    zero_xyz = arm.flange_pose("r1").xyz
    assert any(abs(a - b) > 1e-3 for a, b in zip(home_xyz, zero_xyz))


# ── pose_from_transform ──────────────────────────────────────────────────


def test_pose_from_transform_matches_flange_pose(arm):
    T = arm.fk.get_ee_transform(arm.q)
    pose = pose_from_transform(T, "arm/r1/base")
    ref = arm.flange_pose("r1")
    assert pose.frame == ref.frame
    assert pose.xyz == ref.xyz
    assert pose.quat == ref.quat
