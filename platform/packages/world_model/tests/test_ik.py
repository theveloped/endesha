"""IK solver tests: FK round-trips from perturbed seeds, unreachable -> None.

The assertion is on the RESULTING POSE (FK of the solution within tolerance
of the target), not on q' == q — DLS may legitimately land on an equivalent
joint-space branch.
"""

from __future__ import annotations

import numpy as np
import pytest

from wf.core.frames import rotation_matrix_to_rotvec
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.fk import UrdfFk
from wf.world_model.ik import solve_ik

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]

_POS_TOL = 1e-4
_ROT_TOL = 1e-3


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


@pytest.fixture(scope="module")
def limits(fk) -> tuple[list[float], list[float]]:
    all_limits = fk.get_joint_limits()
    ordered = [all_limits[name] for name in fk.JOINT_ORDER]
    return [lo for lo, _ in ordered], [hi for _, hi in ordered]


def _pose_close(fk, q, T_target) -> bool:
    T = fk.get_ee_transform(q)
    pos_err = np.linalg.norm(T_target[:3, 3] - T[:3, 3])
    rot_err = np.linalg.norm(
        rotation_matrix_to_rotvec(T_target[:3, :3] @ T[:3, :3].T)
    )
    return pos_err < _POS_TOL and rot_err < _ROT_TOL


@pytest.mark.parametrize(
    "dq",
    [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.3, 0.0, -0.3, 0.0, 0.3, 0.0],
        [-0.3, 0.3, 0.0, -0.3, 0.0, 0.3],
        [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
        [-0.3, -0.3, 0.3, 0.3, -0.3, -0.3],
    ],
)
def test_solve_ik_recovers_fk_pose(fk, limits, dq):
    jmin, jmax = limits
    q = [float(np.clip(h + d, lo + 0.1, hi - 0.1))
         for h, d, lo, hi in zip(HOME_Q, dq, jmin, jmax)]
    T_target = fk.get_ee_transform(q)
    seed = [v + 0.05 * (1 if i % 2 == 0 else -1) for i, v in enumerate(q)]
    q_sol = solve_ik(fk, T_target, seed, jmin, jmax)
    assert q_sol is not None
    assert len(q_sol) == 6
    assert _pose_close(fk, q_sol, T_target)


def test_solve_ik_unreachable_returns_none(fk, limits):
    jmin, jmax = limits
    T_target = np.eye(4)
    T_target[:3, 3] = [5.0, 0.0, 0.0]  # 5 m away — far outside the i10 reach
    assert solve_ik(fk, T_target, HOME_Q, jmin, jmax) is None


def test_solve_ik_recovers_from_pinned_wrist_branch(fk, limits):
    """Regression: tool-down pose at table+[0,0,0.3] stalls the raw home
    seed with j6 pinned at a limit; the ±0.4 perturbed-seed retries must
    recover it."""
    from wf.core.frames import make_transform, rpy_to_matrix

    jmin, jmax = limits
    T_target = make_transform(rpy_to_matrix([np.pi, 0.0, 0.0]), [0.6, 0.0, 0.3])
    q_sol = solve_ik(fk, T_target, HOME_Q, jmin, jmax)
    assert q_sol is not None
    assert _pose_close(fk, q_sol, T_target)
