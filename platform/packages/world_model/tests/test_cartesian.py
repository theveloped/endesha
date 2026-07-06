"""generate_cartesian_trajectory tests: straight-line geometry, orientation
slerp, joint-speed cap, and the singularity / reachability guards."""

from __future__ import annotations

import numpy as np
import pytest

from wf.core.frames import (
    make_transform,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_rotvec,
    rpy_to_matrix,
    transform_to_xyz_quat,
)
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.cartesian import (
    CartesianTrajectoryError,
    generate_cartesian_trajectory,
)
from wf.world_model.fk import UrdfFk

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
DT = 0.005

CART_LIMITS = {
    "vmax_lin": 0.25, "amax_lin": 1.0, "jmax_lin": 5.0,
    "vmax_ang": 1.0, "amax_ang": 4.0, "jmax_ang": 20.0,
}


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


@pytest.fixture(scope="module")
def limits(fk):
    ordered = [fk.get_joint_limits()[n] for n in fk.JOINT_ORDER]
    return [lo for lo, _ in ordered], [hi for _, hi in ordered]


def _gen(fk, limits, T0, T1, *, manip_floor=1e-3, vmax_joint=None, branch_tol=0.6):
    jmin, jmax = limits
    return generate_cartesian_trajectory(
        T0, T1, DT, fk=fk, q_seed=HOME_Q, jmin=jmin, jmax=jmax, tcp_T=np.eye(4),
        cart_limits=CART_LIMITS, vmax_joint=vmax_joint or [1.5] * 6,
        manip_floor=manip_floor, branch_tol=branch_tol,
    )


def test_straight_line_stays_on_the_line(fk, limits):
    T0 = fk.get_ee_transform(HOME_Q)
    T1 = T0.copy()
    T1[0, 3] += 0.1  # 10 cm along base-x
    traj, wp_idx = _gen(fk, limits, T0, T1)
    assert wp_idx == [len(traj)]
    p0, p1 = T0[:3, 3], T1[:3, 3]
    line = p1 - p0
    line_len = np.linalg.norm(line)
    for q in traj:
        p = fk.get_ee_transform(q)[:3, 3]
        # perpendicular distance from the ideal p0->p1 segment
        t = np.dot(p - p0, line) / line_len**2
        perp = np.linalg.norm((p - p0) - t * line)
        assert perp < 1e-3, f"deviates {perp*1e3:.2f} mm off the line"
    # Endpoint lands on the goal.
    assert np.linalg.norm(fk.get_ee_transform(traj[-1])[:3, 3] - p1) < 2e-3


def test_orientation_slerps_to_goal(fk, limits):
    T0 = fk.get_ee_transform(HOME_Q)
    T1 = T0.copy()
    T1[:3, :3] = rpy_to_matrix([0, 0, 0.3]) @ T0[:3, :3]  # +0.3 rad yaw (base)
    traj, _ = _gen(fk, limits, T0, T1)
    R_end = fk.get_ee_transform(traj[-1])[:3, :3]
    err = np.linalg.norm(rotation_matrix_to_rotvec(T1[:3, :3] @ R_end.T))
    assert err < 1e-2


def test_joint_speed_cap_slows_the_move(fk, limits):
    T0 = fk.get_ee_transform(HOME_Q)
    T1 = T0.copy()
    T1[0, 3] += 0.1
    fast, _ = _gen(fk, limits, T0, T1, vmax_joint=[1.5] * 6)
    slow, _ = _gen(fk, limits, T0, T1, vmax_joint=[0.05] * 6)
    # A tighter joint-speed cap forces a longer (more sample) trajectory.
    assert len(slow) > len(fast)


def test_singularity_floor_rejects(fk, limits):
    T0 = fk.get_ee_transform(HOME_Q)
    T1 = T0.copy()
    T1[0, 3] += 0.1
    # An unreachably-high manipulability floor: every config is "too singular".
    with pytest.raises(CartesianTrajectoryError, match="singularity"):
        _gen(fk, limits, T0, T1, manip_floor=100.0)


def test_unreachable_target_rejects(fk, limits):
    T0 = fk.get_ee_transform(HOME_Q)
    T1 = T0.copy()
    T1[0, 3] += 5.0  # way out of reach
    with pytest.raises(CartesianTrajectoryError):
        _gen(fk, limits, T0, T1)


def test_zero_move_returns_seed(fk, limits):
    T0 = fk.get_ee_transform(HOME_Q)
    traj, wp_idx = _gen(fk, limits, T0, T0.copy())
    assert traj == [HOME_Q]
    assert wp_idx == [1]
