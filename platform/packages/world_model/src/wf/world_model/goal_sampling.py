"""Loose-goal sampling: expand one free/ranged DOF into candidate poses and
prune them by IK + final-pose collision (design: loose end-goal, phase 1).

A ``movej`` pose target may leave one DOF free (a full or ranged rotation, or a
ranged translation; see :class:`wf.contracts.arm.messages.Freedom`). This module
turns that into a discrete set of fully-defined candidate poses
(:func:`expand_freedom`) and keeps the ones that are reachable and collision-free
at the final pose (:func:`candidate_qs`). The surviving joint goals are handed
to the driver, which plans a Ruckig trajectory per candidate and executes the
fastest collision-free one.

The per-station reuse of these two functions is what phase 3 (path-loose movel)
builds on — same sampling + prune, run at every station of a Cartesian path.
"""

from __future__ import annotations

import numpy as np

from wf.contracts.arm.messages import Freedom, Pose
from wf.core.frames import (
    invert_transform,
    make_transform,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_quaternion,
    rpy_to_matrix,
)
from wf.core.frametree import FrameTree

from .collision import CollisionModel
from .fk import UrdfFk
from .ik import solve_ik

_FULL_CIRCLE = 2.0 * np.pi
_THETA_TOL = 1e-9


def _axis_rotation(axis: int, theta: float) -> np.ndarray:
    """3x3 rotation of ``theta`` rad about axis ``0=x``/``1=y``/``2=z``."""
    rpy = [0.0, 0.0, 0.0]
    rpy[axis] = theta
    return rpy_to_matrix(rpy)


def _sample_thetas(free: Freedom, max_candidates: int) -> list[float]:
    """Discrete sweep values for ``free`` (always includes 0 when in range).

    A full-circle rotation samples ``[min, max)`` (excludes the duplicate
    endpoint); any other range is inclusive of both ends. Raises ``ValueError``
    when the resolution would exceed ``max_candidates`` (a client error: the
    step is too fine for the range).
    """
    lo, hi, step = free.min, free.max, free.step
    span = hi - lo
    full_circle = free.is_rotation and abs(span - _FULL_CIRCLE) < 1e-6
    n = int(round(span / step))
    count = n if full_circle else n + 1
    if count > max_candidates:
        raise ValueError(
            f"free dof {free.dof!r} needs {count} candidates "
            f"(> max_goal_candidates={max_candidates}); coarsen step or narrow range"
        )
    thetas = [lo + step * i for i in range(count)]
    # Snap a near-max sample onto max for a closed range (float drift guard).
    if not full_circle and thetas and abs(thetas[-1] - hi) > _THETA_TOL:
        thetas.append(hi)
    if lo - _THETA_TOL <= 0.0 <= hi + _THETA_TOL and not any(
        abs(t) < _THETA_TOL for t in thetas
    ):
        thetas.append(0.0)
    return thetas


def expand_freedom(
    pose: Pose, free: Freedom, *, max_candidates: int = 256
) -> list[Pose]:
    """Candidate poses over the free DOF, all in ``pose.frame`` coordinates.

    The nominal ``pose`` is the sweep centre (theta=0) and is always present
    when 0 is in range, so a loose goal never loses its unswept solution. Each
    candidate is a fully-defined :class:`Pose` ready for the normal
    resolve/IK path.
    """
    R = quaternion_to_rotation_matrix(pose.quat)
    p = np.asarray(pose.xyz, dtype=np.float64)
    axis = free.axis
    out: list[Pose] = []
    for theta in _sample_thetas(free, max_candidates):
        if free.is_rotation:
            dR = _axis_rotation(axis, theta)
            R_c = dR @ R if free.frame == "reference" else R @ dR
            p_c = p
        else:
            delta = np.zeros(3, dtype=np.float64)
            delta[axis] = theta
            p_c = p + (delta if free.frame == "reference" else R @ delta)
            R_c = R
        out.append(
            Pose(
                frame=pose.frame,
                xyz=[float(v) for v in p_c],
                quat=rotation_matrix_to_quaternion(R_c),
            )
        )
    return out


def candidate_qs(
    poses: list[Pose],
    *,
    fk: UrdfFk,
    q_seed: list[float],
    jmin: list[float],
    jmax: list[float],
    margin: float,
    tree: FrameTree,
    base_frame: str,
    tcp_T: np.ndarray,
    collision: CollisionModel,
    scene: list,
    ik_max_iters: int = 100,
) -> list[list[float]]:
    """Reachable, collision-free joint goals for ``poses`` (order = preference).

    Mirrors ``resolve_goal``'s pose->flange->IK path per candidate, drops IK
    failures and finals that collide, and sorts survivors by joint distance
    from ``q_seed`` (a cheap proxy that front-loads the likely-fastest options
    for the driver's duration-sorted planning).

    Every candidate is seeded from the same ``q_seed`` (the pre-goal config), so
    each solve lands on the branch consistent with the start rather than drifting
    across branches. ``ik_max_iters`` caps each solve: a reachable pose converges
    well within it from this seed, while an unreachable sample bails sooner —
    bounding the cost of a sweep where many samples are out of reach.
    """
    if not poses:
        return []
    tcp_T_inv = invert_transform(tcp_T)
    T_base_frame = tree.resolve(poses[0].frame, base_frame)
    survivors: list[list[float]] = []
    for pose in poses:
        T_base_tcp = T_base_frame @ make_transform(
            quaternion_to_rotation_matrix(pose.quat), pose.xyz
        )
        T_base_flange = T_base_tcp @ tcp_T_inv
        q = solve_ik(
            fk, T_base_flange, q_seed, jmin, jmax, margin=margin,
            max_iters=ik_max_iters,
        )
        if q is None:
            continue
        if collision.check_collision(q, scene, tree, base_frame)["hit"]:
            continue
        survivors.append(q)
    seed = np.asarray(q_seed, dtype=np.float64)
    survivors.sort(key=lambda q: float(np.sum((np.asarray(q) - seed) ** 2)))
    return survivors
