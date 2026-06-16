"""Ruckig trajectory tests — pure compute, no hardware."""

import math

from wf.world_model.trajectory import (
    JOINT_LIMIT_MARGIN,
    generate_ruckig_trajectory,
    validate_trajectory,
)

DT = 0.005
VMAX = [1.5] * 6
AMAX = [3.0] * 6
JMAX = [20.0] * 6

START = [0.0] * 6
HOME = [0.0, math.radians(-30), math.radians(120), math.radians(-40), math.radians(90), 0.0]


def test_trajectory_endpoints_and_velocity():
    traj, _ = generate_ruckig_trajectory(
        [START, HOME], DT, vmax=VMAX, amax=AMAX, jmax=JMAX
    )
    assert len(traj) > 10
    for j in range(6):
        assert abs(traj[0][j] - START[j]) < 1e-3
        assert abs(traj[-1][j] - HOME[j]) < 1e-3
    # Per-sample finite-difference velocity stays within vmax + eps.
    eps = 0.05
    for a, b in zip(traj, traj[1:]):
        for j in range(6):
            assert abs(b[j] - a[j]) / DT <= VMAX[j] + eps


def test_validate_flags_limit_violation():
    traj, _ = generate_ruckig_trajectory(
        [START, HOME], DT, vmax=VMAX, amax=AMAX, jmax=JMAX
    )
    jmin = [-2.95] * 6
    jmax_lim = [2.95] * 6
    assert validate_trajectory(traj, jmin, jmax_lim) is None

    # Push one sample past a limit.
    bad = [list(q) for q in traj]
    bad[len(bad) // 2][2] = 2.95 + JOINT_LIMIT_MARGIN
    violation = validate_trajectory(bad, jmin, jmax_lim)
    assert violation is not None
    assert "foreArm_joint" in violation


def test_wp_sample_idx_monotonic_and_complete():
    mid = [0.1] * 6
    traj, wp_idx = generate_ruckig_trajectory(
        [START, mid, HOME], DT, vmax=VMAX, amax=AMAX, jmax=JMAX
    )
    assert len(wp_idx) == 2  # one entry per waypoint after the first
    assert all(b > a for a, b in zip(wp_idx, wp_idx[1:]))
    assert wp_idx[-1] == len(traj)
    # The recorded boundary sample is at the intermediate waypoint.
    boundary = traj[wp_idx[0] - 1]
    for j in range(6):
        assert abs(boundary[j] - mid[j]) < 1e-3
