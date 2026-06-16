"""Numeric inverse kinematics on the URDF FK (damped least squares).

Own IK by decision: the vendor SDK's kinematics is never used. The solver
runs at goal-acceptance time only (not in the servo loop), so a numeric
Jacobian over :meth:`UrdfFk.get_ee_transform` (7 FK calls per iteration,
cheap numpy) is plenty fast.
"""

from __future__ import annotations

import numpy as np

from wf.core.frames import rotation_matrix_to_rotvec

from .fk import UrdfFk

_JACOBIAN_EPS = 1e-6


def _pose_error(T_target: np.ndarray, T_current: np.ndarray) -> np.ndarray:
    """6-vector ``[dp, drot]``: position delta + axis-angle of R_t @ R_c.T."""
    e = np.empty(6, dtype=np.float64)
    e[:3] = T_target[:3, 3] - T_current[:3, 3]
    e[3:] = rotation_matrix_to_rotvec(T_target[:3, :3] @ T_current[:3, :3].T)
    return e


def numeric_jacobian(
    fk: UrdfFk, q, *, T_current: np.ndarray | None = None
) -> np.ndarray:
    """6x6 numeric flange Jacobian at ``q`` (forward differences).

    Rows are ``[dp_flange; drotvec] / _JACOBIAN_EPS`` — the same body-velocity
    Jacobian the DLS step uses. ``T_current`` is the FK at ``q`` if already
    computed (saves one FK call); recomputed otherwise.
    """
    q = np.asarray(q, dtype=np.float64)
    if T_current is None:
        T_current = fk.get_ee_transform(q)
    J = np.empty((6, 6), dtype=np.float64)
    for j in range(6):
        q_pert = q.copy()
        q_pert[j] += _JACOBIAN_EPS
        T_pert = fk.get_ee_transform(q_pert)
        J[:3, j] = (T_pert[:3, 3] - T_current[:3, 3]) / _JACOBIAN_EPS
        J[3:, j] = (
            rotation_matrix_to_rotvec(T_pert[:3, :3] @ T_current[:3, :3].T)
            / _JACOBIAN_EPS
        )
    return J


def solve_ik(
    fk: UrdfFk,
    T_target: np.ndarray,
    q_seed: list[float],
    jmin: list[float],
    jmax: list[float],
    *,
    margin: float = 0.0,
    pos_tol: float = 1e-4,
    rot_tol: float = 1e-3,
    max_iters: int = 200,
    damping: float = 0.05,
    step_clamp: float = 0.2,
) -> list[float] | None:
    """Solve ``T_base<-flange == T_target`` for joint angles.

    Damped-least-squares iteration seeded from ``q_seed`` (the current or
    previous waypoint's q — seed continuity keeps solutions on the nearby
    branch). When the raw seed stalls (typically a joint pinned at a limit
    on the wrong wrist branch), two fixed ±0.4 rad perturbations of the
    seed are retried — 3 attempts total, deterministic. Returns the
    solution as 6 floats, or None when every attempt exhausts
    ``max_iters`` without convergence.
    """
    T_target = np.asarray(T_target, dtype=np.float64)
    seed = np.asarray(q_seed, dtype=np.float64)
    lo = np.asarray(jmin, dtype=np.float64) + margin
    hi = np.asarray(jmax, dtype=np.float64) - margin

    for offset in (0.0, 0.4, -0.4):
        q = _dls(
            fk,
            T_target,
            np.clip(seed + offset, lo, hi),
            lo,
            hi,
            pos_tol=pos_tol,
            rot_tol=rot_tol,
            max_iters=max_iters,
            damping=damping,
            step_clamp=step_clamp,
        )
        if q is not None:
            return q
    return None


def _dls(
    fk: UrdfFk,
    T_target: np.ndarray,
    q: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    *,
    pos_tol: float,
    rot_tol: float,
    max_iters: int,
    damping: float,
    step_clamp: float,
) -> list[float] | None:
    """One damped-least-squares descent from ``q``; None on non-convergence."""
    for _ in range(max_iters):
        T_current = fk.get_ee_transform(q)
        e = _pose_error(T_target, T_current)
        if np.linalg.norm(e[:3]) < pos_tol and np.linalg.norm(e[3:]) < rot_tol:
            return [float(v) for v in q]

        J = numeric_jacobian(fk, q, T_current=T_current)

        dq = J.T @ np.linalg.solve(J @ J.T + damping**2 * np.eye(6), e)
        dq = np.clip(dq, -step_clamp, step_clamp)
        q = np.clip(q + dq, lo, hi)

    return None
