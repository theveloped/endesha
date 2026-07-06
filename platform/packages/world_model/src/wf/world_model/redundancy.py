"""Path-loose redundancy resolution for ``movel`` + a free DOF (phase 3).

A ``movel`` whose goal leaves one DOF free turns the 6-DoF arm into a
functionally redundant one along a 5-DoF task path: at every station of the
straight-line path the free DOF may take any value, and choosing it well keeps
the arm dexterous — away from singularities and joint limits — where a fixed
orientation would stall.

The free value ``theta(s)`` is resolved by a lattice + dynamic program, subject
to a hard constraint: the whole path must stay **within the current IK branch**.
No branch flips, no singularity crossings. If no on-branch, singularity-free
corridor connects the start config to the goal, the move is rejected (a
:class:`RedundancyError`) rather than silently flipping or deviating.

Method (this is phase-1's sampler run at every station, plus a graph search):

1. Discretise the path into ``M`` stations. At each, the 5 constrained DOF are
   the nominal lerp/slerp interpolation; the free DOF is swept into ``K`` values
   via :func:`wf.world_model.goal_sampling.expand_freedom`.
2. Each ``(station, theta)`` node is solved by warm IK seeded along its
   theta-track (so IK stays on one branch), then pruned if it fails IK, drops
   below the manipulability floor, or collides.
3. A 1-D DP connects adjacent stations with edges feasible only within the
   branch tolerance; the cost trades joint motion against proximity to
   singularity. The globally optimal on-branch ``theta(s)`` is recovered as a
   joint path ``q(s)``.

The returned ``q(s)`` knots (starting at ``q_start``) are time-parameterised by
the caller (Ruckig through the joint waypoints, blended) into servo samples.
"""

from __future__ import annotations

import math

import numpy as np

from wf.contracts.arm.messages import Freedom, Pose
from wf.core.frames import (
    invert_transform,
    make_transform,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_rotvec,
    slerp,
    transform_to_xyz_quat,
)
from wf.core.frametree import FrameTree

from .collision import CollisionModel
from .fk import UrdfFk
from .goal_sampling import expand_freedom
from .ik import manipulability, solve_ik

_EPS = 1e-6


class RedundancyError(Exception):
    """No on-branch, singularity-free ``theta(s)`` corridor exists."""


def _joint_jump(a: list[float], b: list[float]) -> float:
    return max(abs(x - y) for x, y in zip(a, b))


def resolve_redundant_path(
    T0_tcp: np.ndarray,
    T1_tcp: np.ndarray,
    free: Freedom,
    *,
    fk: UrdfFk,
    q_start: list[float],
    jmin: list[float],
    jmax: list[float],
    tcp_T: np.ndarray,
    collision: CollisionModel,
    scene: list,
    tree: FrameTree,
    base_frame: str,
    manip_floor: float,
    branch_tol: float,
    margin: float = 0.0,
    step_m: float = 0.02,
    step_rad: float = 0.1,
    max_stations: int = 60,
    max_candidates: int = 256,
    sing_weight: float = 0.05,
) -> list[list[float]]:
    """Resolve ``theta(s)`` for a straight ``T0_tcp``->``T1_tcp`` TCP path.

    Returns the joint knots ``q(s)`` (first knot is ``q_start``), all on the
    starting IK branch and clear of singularities/collisions. Raises
    :class:`RedundancyError` when no such corridor exists.
    """
    p0, q0 = transform_to_xyz_quat(T0_tcp)
    p1, q1 = transform_to_xyz_quat(T1_tcp)
    p0 = np.asarray(p0, dtype=np.float64)
    p1 = np.asarray(p1, dtype=np.float64)
    length = float(np.linalg.norm(p1 - p0))
    R0 = quaternion_to_rotation_matrix(q0)
    R1 = quaternion_to_rotation_matrix(q1)
    angle = float(np.linalg.norm(rotation_matrix_to_rotvec(R1 @ R0.T)))
    if length < _EPS and angle < _EPS:
        return [list(q_start)]

    n_lin = length / step_m if step_m > 0 else 0.0
    n_ang = angle / step_rad if step_rad > 0 else 0.0
    stations = max(2, int(math.ceil(max(n_lin, n_ang))))
    stations = min(stations, max_stations)

    tcp_T_inv = invert_transform(tcp_T)

    def nominal_pose(s: float) -> Pose:
        pos = p0 + s * (p1 - p0)
        return Pose(frame=base_frame, xyz=[float(v) for v in pos],
                    quat=slerp(q0, q1, s))

    def flange_of(pose: Pose) -> np.ndarray:
        T_tcp = make_transform(quaternion_to_rotation_matrix(pose.quat), pose.xyz)
        return T_tcp @ tcp_T_inv

    # Deterministic theta-track count K (same sweep values at every station).
    k_tracks = len(expand_freedom(nominal_pose(1.0), free, max_candidates=max_candidates))

    # Layer 0 is the fixed start config (single node); its theta is implicit.
    layers: list[list[dict | None]] = [
        [{"q": list(q_start), "cost": 0.0, "prev": None}]
    ]
    track_seed = [list(q_start) for _ in range(k_tracks)]

    for k in range(1, stations + 1):
        s = k / stations
        poses = expand_freedom(nominal_pose(s), free, max_candidates=max_candidates)
        prev = layers[-1]
        layer: list[dict | None] = []
        for j, pose in enumerate(poses):
            q = solve_ik(fk, flange_of(pose), track_seed[j], jmin, jmax,
                         margin=margin)
            if q is None:
                layer.append(None)
                continue
            T_cur = fk.get_ee_transform(q)
            m = manipulability(fk, q, T_current=T_cur)
            if m < manip_floor:
                layer.append(None)
                continue
            if collision.check_collision(q, scene, tree, base_frame)["hit"]:
                layer.append(None)
                continue
            track_seed[j] = q
            # Best on-branch predecessor.
            best_cost = float("inf")
            best_prev = None
            for pi, pnode in enumerate(prev):
                if pnode is None or _joint_jump(pnode["q"], q) > branch_tol:
                    continue
                step = float(np.linalg.norm(np.asarray(q) - np.asarray(pnode["q"])))
                c = pnode["cost"] + step + sing_weight / m
                if c < best_cost:
                    best_cost = c
                    best_prev = pi
            if best_prev is None:
                layer.append(None)  # reachable pose, but not from this branch
            else:
                layer.append({"q": q, "cost": best_cost, "prev": best_prev})
        if all(n is None for n in layer):
            raise RedundancyError(
                f"no on-branch, singularity-free corridor at s={s:.2f}"
            )
        layers.append(layer)

    # Best goal node, then backtrack the theta(s) corridor.
    final = layers[-1]
    best_i = min(
        (i for i, n in enumerate(final) if n is not None),
        key=lambda i: final[i]["cost"],
        default=None,
    )
    if best_i is None:
        raise RedundancyError("no feasible redundant path to the goal")

    knots: list[list[float]] = []
    k = len(layers) - 1
    idx: int | None = best_i
    while idx is not None:
        node = layers[k][idx]
        knots.append(list(node["q"]))
        idx = node["prev"]
        k -= 1
    knots.reverse()
    return knots
