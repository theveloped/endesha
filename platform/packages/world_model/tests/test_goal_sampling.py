"""goal_sampling tests: expand_freedom sweep math + candidate_qs pruning."""

from __future__ import annotations

import math

import numpy as np
import pytest

from wf.contracts.arm.messages import Freedom, Pose
from wf.core.frames import (
    quaternion_to_rotation_matrix,
    rotation_matrix_to_quaternion,
    rpy_to_matrix,
)
from wf.core.frametree import FrameDef, FrameTree
from wf.core.scene import SceneObject
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.collision import CollisionModel
from wf.world_model.fk import UrdfFk
from wf.world_model.goal_sampling import candidate_qs, expand_freedom

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
BASE = "arm/r1/base"
_MARGIN = 0.01


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


@pytest.fixture(scope="module")
def model() -> CollisionModel:
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


def _identity_pose() -> Pose:
    return Pose(frame=BASE, xyz=[0.4, 0.0, 0.5], quat=[0.0, 0.0, 0.0, 1.0])


# ── expand_freedom ─────────────────────────────────────────────────────────


def test_free_yaw_full_circle_count():
    # 360 deg / 5 deg = 72 samples; endpoint excluded (duplicate of start),
    # 0 already present -> exactly 72.
    poses = expand_freedom(_identity_pose(), Freedom(dof="yaw"))
    assert len(poses) == 72


def test_ranged_pitch_inclusive_endpoints_and_nominal():
    free = Freedom(dof="pitch", min=-math.radians(10), max=math.radians(10),
                   step=math.radians(5))
    poses = expand_freedom(_identity_pose(), free)
    # -10,-5,0,5,10 deg -> 5 samples, both ends present, nominal (0) present.
    assert len(poses) == 5
    quats = [p.quat for p in poses]
    assert any(np.allclose(q, [0, 0, 0, 1], atol=1e-9) for q in quats)


def test_reference_vs_tool_differ_for_tilted_pose():
    # A base pose already rotated 90 deg about x, then sweep pitch (about y).
    R0 = rpy_to_matrix([math.pi / 2, 0, 0])
    pose = Pose(frame=BASE, xyz=[0.4, 0, 0.5],
                quat=rotation_matrix_to_quaternion(R0))
    free_ref = Freedom(dof="pitch", frame="reference", min=0.5, max=0.5001, step=0.5)
    free_tool = Freedom(dof="pitch", frame="tool", min=0.5, max=0.5001, step=0.5)
    ref = expand_freedom(pose, free_ref, max_candidates=8)
    tool = expand_freedom(pose, free_tool, max_candidates=8)
    # The theta=0.5 candidate must differ between reference- and tool-frame axes.
    r05 = next(p for p in ref if not np.allclose(p.quat, pose.quat, atol=1e-6))
    t05 = next(p for p in tool if not np.allclose(p.quat, pose.quat, atol=1e-6))
    assert not np.allclose(r05.quat, t05.quat, atol=1e-3)


def test_tool_frame_translation_moves_along_rotated_axis():
    # Pose rotated 90 deg about z: tool-x points along base-y.
    R0 = rpy_to_matrix([0, 0, math.pi / 2])
    pose = Pose(frame=BASE, xyz=[0.4, 0.0, 0.5],
                quat=rotation_matrix_to_quaternion(R0))
    free = Freedom(dof="x", frame="tool", min=0.1, max=0.1001, step=0.1)
    poses = expand_freedom(pose, free, max_candidates=8)
    moved = next(p for p in poses if not np.allclose(p.xyz, pose.xyz, atol=1e-9))
    # +0.1 along tool-x == +0.1 along base-y.
    assert np.allclose(moved.xyz, [0.4, 0.1, 0.5], atol=1e-6)


def test_max_candidates_overflow_raises():
    free = Freedom(dof="yaw", min=-math.pi, max=math.pi, step=math.radians(1))
    with pytest.raises(ValueError):
        expand_freedom(_identity_pose(), free, max_candidates=100)


# ── candidate_qs ───────────────────────────────────────────────────────────


def test_candidate_qs_prunes_and_sorts(fk, model, limits, tree):
    jmin, jmax = limits
    # A reachable free-yaw goal at the home flange pose: many candidates solve.
    T = fk.get_ee_transform(HOME_Q)
    pose = Pose(frame=BASE, xyz=[float(v) for v in T[:3, 3]],
                quat=rotation_matrix_to_quaternion(T[:3, :3]))
    poses = expand_freedom(pose, Freedom(dof="yaw"))
    qs = candidate_qs(
        poses, fk=fk, q_seed=HOME_Q, jmin=jmin, jmax=jmax, margin=_MARGIN,
        tree=tree, base_frame=BASE, tcp_T=np.eye(4), collision=model, scene=[],
    )
    assert len(qs) > 0
    # Sorted ascending by distance from the seed.
    d = [float(np.sum((np.asarray(q) - np.asarray(HOME_Q)) ** 2)) for q in qs]
    assert d == sorted(d)


def test_candidate_qs_drops_final_pose_collisions(fk, model, limits, tree):
    jmin, jmax = limits
    T = fk.get_ee_transform(HOME_Q)
    pose = Pose(frame=BASE, xyz=[float(v) for v in T[:3, 3]],
                quat=rotation_matrix_to_quaternion(T[:3, :3]))
    poses = expand_freedom(pose, Freedom(dof="yaw"))
    # A box sitting on the flange makes every final pose collide.
    blocker = SceneObject(
        frame=BASE, xyz=[float(v) for v in T[:3, 3]], quat=[0, 0, 0, 1],
        geometry={"type": "box", "size": [0.3, 0.3, 0.3]}, meta={"name": "blk"},
    )
    qs = candidate_qs(
        poses, fk=fk, q_seed=HOME_Q, jmin=jmin, jmax=jmax, margin=_MARGIN,
        tree=tree, base_frame=BASE, tcp_T=np.eye(4), collision=model,
        scene=[blocker],
    )
    assert qs == []
