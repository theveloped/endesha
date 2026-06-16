"""Ruckig trajectory generation + joint-limit validation.

Lifted verbatim from the proven reference implementation, including the
corner-blend velocity heuristic (non-obvious math — do not re-derive). One
extension: `generate_ruckig_trajectory` also returns `wp_sample_idx`, the
sample index at which each waypoint (after the first) is reached — used for
`current_wp` action feedback.
"""

from __future__ import annotations

import math

from ruckig import InputParameter, OutputParameter, Result, Ruckig

JOINT_LIMIT_MARGIN = 0.01  # rad (~0.6 deg) inward safety margin on joint limits

JOINT_NAMES = [
    "shoulder_joint",
    "upperArm_joint",
    "foreArm_joint",
    "wrist1_joint",
    "wrist2_joint",
    "wrist3_joint",
]


class TrajectoryError(Exception):
    pass


def joints_close(a, b, tol: float = 0.01) -> bool:
    if len(a) != len(b):
        return False
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def generate_ruckig_trajectory(
    waypoints,
    dt,
    dof=6,
    vmax=None,
    amax=None,
    jmax=None,
    corner_tolerance_mm=None,
) -> tuple[list[list[float]], list[int]]:
    """Generate a smooth joint trajectory through waypoints using Ruckig.

    Args:
        waypoints: list of joint positions (each a list of `dof` floats, rad)
        dt: servo cycle time (seconds)
        dof: degrees of freedom
        vmax: max velocity per joint (rad/s), default [1.5]*dof
        amax: max acceleration per joint (rad/s^2), default [3.0]*dof
        jmax: max jerk per joint (rad/s^3), default [20.0]*dof
        corner_tolerance_mm: if set, allow blending at intermediate waypoints
            with approximately this max Cartesian deviation (mm). Conversion
            to joint space uses a conservative 1 m effective lever arm. If
            None, stop (v=0) at each waypoint.

    Returns:
        (traj, wp_sample_idx) where wp_sample_idx[i] is the sample index at
        which waypoint i+1 is reached (monotonic, ends at len(traj)).
    """
    if vmax is None:
        vmax = [1.5] * dof
    if amax is None:
        amax = [3.0] * dof
    if jmax is None:
        jmax = [20.0] * dof

    otg = Ruckig(dof, dt)
    ip = InputParameter(dof)
    op = OutputParameter(dof)

    ip.max_velocity = vmax
    ip.max_acceleration = amax
    ip.max_jerk = jmax

    ip.current_position = list(waypoints[0])
    ip.current_velocity = [0.0] * dof
    ip.current_acceleration = [0.0] * dof

    # Convert corner tolerance from mm to joint-space (rad).
    # Approximation: 1 mm tip motion ~ 1e-3 rad for a ~1 m lever arm.
    blend = corner_tolerance_mm is not None and corner_tolerance_mm > 0
    ct_rad = corner_tolerance_mm / 1000.0 if blend else 0.0

    traj: list[list[float]] = []
    wp_sample_idx: list[int] = []
    n_wp = len(waypoints)

    for seg_idx in range(1, n_wp):
        target = waypoints[seg_idx]
        is_last = seg_idx == n_wp - 1

        ip.target_position = list(target)
        ip.target_acceleration = [0.0] * dof

        if is_last or not blend:
            # Stop at this waypoint
            ip.target_velocity = [0.0] * dof
        else:
            # Compute pass-through velocity for corner blending
            prev_wp = waypoints[seg_idx - 1]
            next_wp = waypoints[seg_idx + 1]

            # Outgoing direction: target -> next_wp
            out_vec = [next_wp[j] - target[j] for j in range(dof)]
            out_dist = math.sqrt(sum(d * d for d in out_vec))

            # Incoming direction: prev_wp -> target
            in_vec = [target[j] - prev_wp[j] for j in range(dof)]
            in_dist = math.sqrt(sum(d * d for d in in_vec))

            if out_dist < 1e-9 or in_dist < 1e-9:
                ip.target_velocity = [0.0] * dof
            else:
                out_dir = [d / out_dist for d in out_vec]
                in_dir = [d / in_dist for d in in_vec]

                # Angle between incoming and outgoing (0 = collinear, pi = reversal)
                cos_theta = sum(in_dir[j] * out_dir[j] for j in range(dof))
                cos_theta = max(-1.0, min(1.0, cos_theta))
                theta = math.acos(cos_theta)

                if theta > 2.094:
                    # Near-reversal (>120 deg) — no meaningful blend, just stop
                    speed = 0.0
                elif theta < 0.01:
                    # Nearly straight — pass through at max speed
                    speed = min(vmax)
                else:
                    # Deviation ~ v^2 * sin(theta/2) / (2 * a_eff)
                    # => v = sqrt(2 * a_eff * ct_rad / sin(theta/2))
                    sin_half = math.sin(theta / 2)
                    a_eff = min(amax)
                    speed = math.sqrt(2.0 * a_eff * ct_rad / max(sin_half, 0.01))

                # Cap by per-joint velocity limits
                for j in range(dof):
                    if abs(out_dir[j]) > 1e-9:
                        speed = min(speed, vmax[j] / abs(out_dir[j]))

                # Cap by what's kinematically reachable over the incoming
                # segment: v_max_reachable = sqrt(v_current^2 + 2*a*d).
                # Conservative: assume starting from 0 -> sqrt(2*a*d)
                a_eff = min(amax)
                speed = min(speed, math.sqrt(max(2.0 * a_eff * in_dist, 0.0)))
                # Also cap by what allows decelerating over the outgoing segment
                speed = min(speed, math.sqrt(max(2.0 * a_eff * out_dist, 0.0)))

                ip.target_velocity = [speed * out_dir[j] for j in range(dof)]

        res = otg.update(ip, op)
        if res not in (Result.Working, Result.Finished):
            # If blending velocity is infeasible, fall back to stopping
            if blend and not is_last:
                ip.target_velocity = [0.0] * dof
                res = otg.update(ip, op)
            if res not in (Result.Working, Result.Finished):
                raise TrajectoryError(
                    f"Ruckig planning failed at waypoint {seg_idx}: {res}"
                )

        while res == Result.Working:
            traj.append(list(op.new_position))
            ip.current_position = list(op.new_position)
            ip.current_velocity = list(op.new_velocity)
            ip.current_acceleration = list(op.new_acceleration)
            res = otg.update(ip, op)

        # Final point of this segment
        traj.append(list(op.new_position))
        ip.current_position = list(op.new_position)

        if is_last or not blend:
            ip.current_velocity = [0.0] * dof
            ip.current_acceleration = [0.0] * dof
        else:
            # Carry velocity/acceleration through to next segment
            ip.current_velocity = list(op.new_velocity)
            ip.current_acceleration = list(op.new_acceleration)

        wp_sample_idx.append(len(traj))

    return traj, wp_sample_idx


def validate_trajectory(traj, jmin, jmax, margin=JOINT_LIMIT_MARGIN) -> str | None:
    """Check all trajectory samples are within joint limits (with margin).

    Returns None on success, or an error message string on violation.
    """
    eff_min = [lo + margin for lo in jmin]
    eff_max = [hi - margin for hi in jmax]
    for i, q in enumerate(traj):
        for j in range(len(q)):
            if q[j] < eff_min[j] - 1e-6 or q[j] > eff_max[j] + 1e-6:
                return (
                    f"Trajectory sample {i}/{len(traj)} violates "
                    f"joint {j} ({JOINT_NAMES[j]}) limit: "
                    f"{math.degrees(q[j]):.2f} deg not in "
                    f"[{math.degrees(eff_min[j]):.1f}, "
                    f"{math.degrees(eff_max[j]):.1f}] deg. "
                    f"Reduce corner tolerance or adjust waypoints."
                )
    return None
