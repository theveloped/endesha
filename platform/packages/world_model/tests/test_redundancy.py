"""resolve_redundant_path: on-branch theta(s) corridor, guards, and knots."""

from __future__ import annotations

import numpy as np
import pytest

from wf.contracts.arm.messages import Freedom
from wf.core.frametree import FrameDef, FrameTree
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.collision import CollisionModel
from wf.world_model.fk import UrdfFk
from wf.world_model.redundancy import RedundancyError, resolve_redundant_path

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
BASE = "arm/r1/base"


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


@pytest.fixture(scope="module")
def collision() -> CollisionModel:
    return CollisionModel(BUNDLED_URDF, BUNDLED_URDF.parent.parent)


@pytest.fixture(scope="module")
def limits(fk):
    ordered = [fk.get_joint_limits()[n] for n in fk.JOINT_ORDER]
    return [lo for lo, _ in ordered], [hi for _, hi in ordered]


@pytest.fixture()
def tree() -> FrameTree:
    return FrameTree(
        {"arm/r1/base": FrameDef(parent="world", xyz=[0, 0, 0], quat=[0, 0, 0, 1])}
    )


def _solve(fk, collision, limits, tree, T0, T1, **kw):
    jmin, jmax = limits
    opts = dict(
        fk=fk, q_start=HOME_Q, jmin=jmin, jmax=jmax, tcp_T=np.eye(4),
        collision=collision, scene=[], tree=tree, base_frame=BASE,
        manip_floor=0.02, branch_tol=0.8, step_m=0.02, step_rad=0.1,
    )
    opts.update(kw)
    return resolve_redundant_path(T0, T1, Freedom(dof="yaw"), **opts)


def test_finds_on_branch_corridor(fk, collision, limits, tree):
    T0 = fk.get_ee_transform(HOME_Q)
    T1 = T0.copy()
    T1[0, 3] += 0.06  # 6 cm along base-x, yaw free along the way
    knots = _solve(fk, collision, limits, tree, T0, T1)
    assert len(knots) >= 3
    assert knots[0] == HOME_Q  # path starts at the current config
    # On one branch: consecutive knots never jump beyond the tolerance.
    for a, b in zip(knots, knots[1:]):
        assert max(abs(x - y) for x, y in zip(a, b)) <= 0.8 + 1e-9
    # The final TCP position lands on the goal (yaw free, position constrained).
    assert np.linalg.norm(fk.get_ee_transform(knots[-1])[:3, 3] - T1[:3, 3]) < 5e-3


def test_singularity_floor_blocks_corridor(fk, collision, limits, tree):
    T0 = fk.get_ee_transform(HOME_Q)
    T1 = T0.copy()
    T1[0, 3] += 0.06
    with pytest.raises(RedundancyError):
        _solve(fk, collision, limits, tree, T0, T1, manip_floor=100.0)


def test_zero_branch_tolerance_blocks_corridor(fk, collision, limits, tree):
    T0 = fk.get_ee_transform(HOME_Q)
    T1 = T0.copy()
    T1[0, 3] += 0.06
    # No joint motion allowed between stations -> no corridor.
    with pytest.raises(RedundancyError):
        _solve(fk, collision, limits, tree, T0, T1, branch_tol=0.0)


def test_zero_length_move_returns_seed(fk, collision, limits, tree):
    T0 = fk.get_ee_transform(HOME_Q)
    knots = _solve(fk, collision, limits, tree, T0, T0.copy())
    assert knots == [HOME_Q]
