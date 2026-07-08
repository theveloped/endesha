"""Cartesian (straight-line) trajectory generation for ``movel`` (phase 2).

A ``movel`` drives the active TCP along a straight line (position lerp,
orientation slerp) from its current pose to a goal pose, true to Cartesian
velocity/acceleration/jerk limits. Rather than dense-sampling waypoints into
the joint planner, the move is decomposed into three cheap pieces:

1. a geometric path ``P(s)``, ``s in [0, 1]`` — ``pos = lerp``, ``rot = slerp``
   (straight by construction, exact);
2. a scalar time-law ``s(t)`` from a 1-DOF Ruckig run whose limits are the
   Cartesian limits mapped through the path length, additionally capped by the
   joint-speed limits along the path (slows the move near ill-conditioned
   configurations rather than demanding impossible joint speed);
3. a per-tick map ``q = IK(P(s(t)), seed=prev q)`` — warm-started, so each
   solve converges in a couple of iterations.

The output is a list of joint samples + ``wp_sample_idx``, identical in shape to
:func:`wf.world_model.trajectory.generate_ruckig_trajectory`, so the backend
plays it back unchanged.

Singularity guard: the smallest singular value of the flange Jacobian
(:func:`manipulability`) is checked along the path; below a floor the move is
rejected rather than letting the TCP silently deviate. A branch flip (a joint
jump beyond a tolerance between adjacent stations) is likewise rejected — a
``movel`` never crosses IK branches.
"""

from __future__ import annotations

import numpy as np

from wf.core.frames import (
    invert_transform,
    make_transform,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_rotvec,
    slerp,
    transform_to_xyz_quat,
)

from .fk import UrdfFk
from .ik import manipulability, numeric_jacobian, solve_ik
from .trajectory import generate_ruckig_trajectory

_EPS = 1e-6

# Cartesian limit keys expected in ``cart_limits`` (SI: m/s.., rad/s..).
CART_LIMIT_KEYS = (
    "vmax_lin", "amax_lin", "jmax_lin", "vmax_ang", "amax_ang", "jmax_ang",
)


class CartesianTrajectoryError(Exception):
    """A ``movel`` could not be realised (unreachable, singular, branch flip)."""


def _s_limit(v_lin: float, v_ang: float, length: float, angle: float) -> float:
    """Max ``s``-rate so neither the linear nor angular limit is exceeded."""
    lim = float("inf")
    if length > _EPS:
        lim = min(lim, v_lin / length)
    if angle > _EPS:
        lim = min(lim, v_ang / angle)
    return lim


def generate_cartesian_trajectory(
    T0_tcp: np.ndarray,
    T1_tcp: np.ndarray,
    dt: float,
    *,
    fk: UrdfFk,
    q_seed: list[float],
    jmin: list[float],
    jmax: list[float],
    tcp_T: np.ndarray,
    cart_limits: dict,
    vmax_joint: list[float],
    manip_floor: float,
    branch_tol: float,
    margin: float = 0.0,
    coarse_stations: int = 16,
) -> tuple[list[list[float]], list[int]]:
    """Straight-line TCP move from ``T0_tcp`` to ``T1_tcp`` (both base<-TCP).

    Returns ``(traj, wp_sample_idx)``; ``wp_sample_idx`` is ``[len(traj)]`` (a
    single goal waypoint). Raises :class:`CartesianTrajectoryError` when the
    path is unreachable, passes too near a singularity (``manip_floor``), or
    would require an IK branch flip (``branch_tol``).
    """
    p0, q0 = transform_to_xyz_quat(T0_tcp)
    p1, q1 = transform_to_xyz_quat(T1_tcp)
    p0 = np.asarray(p0, dtype=np.float64)
    p1 = np.asarray(p1, dtype=np.float64)
    length = float(np.linalg.norm(p1 - p0))

    R0 = quaternion_to_rotation_matrix(q0)
    R1 = quaternion_to_rotation_matrix(q1)
    rotvec = rotation_matrix_to_rotvec(R1 @ R0.T)  # dtheta/ds * axis (constant)
    angle = float(np.linalg.norm(rotvec))

    if length < _EPS and angle < _EPS:
        return [list(q_seed)], [1]

    tcp_T_inv = invert_transform(tcp_T)

    def flange_target(s: float) -> np.ndarray:
        pos = p0 + s * (p1 - p0)
        quat = slerp(q0, q1, s)
        T_tcp = make_transform(quaternion_to_rotation_matrix(quat), pos)
        return T_tcp @ tcp_T_inv

    # Task twist per unit s (flange approximation: exact angular, linear ignores
    # the small omega x r_tcp offset — a conservative cap, not a servo target).
    twist = np.concatenate([p1 - p0, rotvec])

    # ── coarse pass: feasibility + a conservative joint-speed s-rate cap ──────
    seed = list(q_seed)
    prev_qc: list[float] | None = None
    sdot_cap = float("inf")
    for k in range(coarse_stations + 1):
        s = k / coarse_stations
        qc = solve_ik(fk, flange_target(s), seed, jmin, jmax, margin=margin)
        if qc is None:
            raise CartesianTrajectoryError(f"unreachable at s={s:.3f}")
        T_cur = fk.get_ee_transform(qc)
        if manipulability(fk, qc, T_current=T_cur) < manip_floor:
            raise CartesianTrajectoryError(f"singularity in path at s={s:.3f}")
        if prev_qc is not None and _joint_jump(qc, prev_qc) > branch_tol:
            raise CartesianTrajectoryError(f"branch flip required at s={s:.3f}")
        dqds = np.linalg.lstsq(numeric_jacobian(fk, qc, T_current=T_cur), twist,
                               rcond=None)[0]
        for j in range(6):
            if abs(dqds[j]) > _EPS:
                sdot_cap = min(sdot_cap, vmax_joint[j] / abs(dqds[j]))
        prev_qc = qc
        seed = qc

    # ── s(t): 1-DOF Ruckig with Cartesian-mapped, joint-capped limits ─────────
    vmax_s = min(
        _s_limit(cart_limits["vmax_lin"], cart_limits["vmax_ang"], length, angle),
        sdot_cap,
    )
    amax_s = _s_limit(cart_limits["amax_lin"], cart_limits["amax_ang"], length, angle)
    jmax_s = _s_limit(cart_limits["jmax_lin"], cart_limits["jmax_ang"], length, angle)
    s_traj, _ = generate_ruckig_trajectory(
        [[0.0], [1.0]], dt, dof=1, vmax=[vmax_s], amax=[amax_s], jmax=[jmax_s]
    )

    # ── fine pass: per-tick warm IK along s(t) ────────────────────────────────
    seed = list(q_seed)
    prev_q: list[float] | None = None
    traj: list[list[float]] = []
    for row in s_traj:
        s = min(max(float(row[0]), 0.0), 1.0)
        q = solve_ik(fk, flange_target(s), seed, jmin, jmax, margin=margin)
        if q is None:
            raise CartesianTrajectoryError(f"unreachable at s={s:.3f}")
        T_cur = fk.get_ee_transform(q)
        if manipulability(fk, q, T_current=T_cur) < manip_floor:
            raise CartesianTrajectoryError(f"singularity in path at s={s:.3f}")
        if prev_q is not None and _joint_jump(q, prev_q) > branch_tol:
            raise CartesianTrajectoryError(f"branch flip required at s={s:.3f}")
        traj.append(q)
        seed = q
        prev_q = q
    return traj, [len(traj)]


def _joint_jump(a: list[float], b: list[float]) -> float:
    """Max per-joint absolute difference (rad) — a branch-flip detector."""
    return max(abs(x - y) for x, y in zip(a, b))
