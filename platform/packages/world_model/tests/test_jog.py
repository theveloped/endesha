"""Frame-aligned hold-to-jog math: this is where jog correctness is proven.

Config-free and deterministic — no zenoh/tree. ``ref_R`` (reference-frame axes
in base) and ``tcp_T`` (active T_flange<-tcp) are passed directly, exactly as
the driver supplies them.
"""

from __future__ import annotations

import numpy as np
import pytest

from wf.core.frames import rpy_to_matrix
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.fk import UrdfFk
from wf.world_model.jog import jog_joint_velocity

# Well-conditioned (non-singular) seed, shared with the IK suite.
HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
DT = 0.01


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


def _flange_origin(fk, q):
    return fk.get_ee_transform(q)[:3, 3]


def _tcp_origin(fk, q, tcp_T):
    T = fk.get_ee_transform(q)
    return T[:3, 3] + T[:3, :3] @ tcp_T[:3, 3]


def test_joint_passthrough(fk):
    vel = [0.1, -0.2, 0.05, 0.0, 0.3, -0.15]
    qd = jog_joint_velocity(
        fk, HOME_Q, mode="joint", velocity=vel, ref_R=np.eye(3),
        tcp_T=np.eye(4), jog_vmax=0.5,
    )
    assert qd == pytest.approx(vel)


def test_joint_clamp(fk):
    qd = jog_joint_velocity(
        fk, HOME_Q, mode="joint", velocity=[9.0, -9.0, 0.0, 0.0, 0.0, 0.0],
        ref_R=np.eye(3), tcp_T=np.eye(4), jog_vmax=0.5,
    )
    assert qd[0] == pytest.approx(0.5)
    assert qd[1] == pytest.approx(-0.5)


def test_cartesian_frame_aligned_translation(fk):
    """+X in a frame yawed 90° about base Z must move the TCP along base +Y."""
    ref_R = rpy_to_matrix([0.0, 0.0, np.pi / 2])
    qd = jog_joint_velocity(
        fk, HOME_Q, mode="cartesian", velocity=[0.05, 0.0, 0.0, 0.0, 0.0, 0.0],
        ref_R=ref_R, tcp_T=np.eye(4), jog_vmax=5.0, damping=0.05,
    )
    q1 = [h + v * DT for h, v in zip(HOME_Q, qd)]
    delta = _tcp_origin(fk, q1, np.eye(4)) - _tcp_origin(fk, HOME_Q, np.eye(4))
    unit = delta / np.linalg.norm(delta)
    # base +Y dominant; X/Z cross-axis bleed (DLS damping) small.
    assert unit[1] > 0.97
    assert abs(unit[0]) < 0.15
    assert abs(unit[2]) < 0.15


def test_cartesian_rotation_about_tcp(fk):
    """Pure wz with a z-offset TCP keeps the TCP origin put while the flange
    moves — rotation is about the TCP, not the flange."""
    tcp_T = np.eye(4)
    tcp_T[2, 3] = 0.12  # tool0-style z offset
    qd = jog_joint_velocity(
        fk, HOME_Q, mode="cartesian", velocity=[0.0, 0.0, 0.0, 0.0, 0.0, 0.3],
        ref_R=np.eye(3), tcp_T=tcp_T, jog_vmax=5.0, damping=0.05,
    )
    q1 = [h + v * DT for h, v in zip(HOME_Q, qd)]

    tcp_delta = np.linalg.norm(_tcp_origin(fk, q1, tcp_T) - _tcp_origin(fk, HOME_Q, tcp_T))
    flange_delta = np.linalg.norm(_flange_origin(fk, q1) - _flange_origin(fk, HOME_Q))

    assert flange_delta > 2e-4, "flange origin must move under rotate-about-TCP"
    assert tcp_delta < 0.2 * flange_delta, "TCP origin must stay ~fixed"


def test_cartesian_clamp(fk):
    """A large commanded twist clamps every joint to jog_vmax."""
    qd = jog_joint_velocity(
        fk, HOME_Q, mode="cartesian", velocity=[10.0, 10.0, 10.0, 5.0, 5.0, 5.0],
        ref_R=np.eye(3), tcp_T=np.eye(4), jog_vmax=0.5, damping=0.05,
    )
    assert all(abs(v) <= 0.5 + 1e-12 for v in qd)
    assert max(abs(v) for v in qd) == pytest.approx(0.5)


def test_bad_mode_rejected(fk):
    with pytest.raises(ValueError):
        jog_joint_velocity(
            fk, HOME_Q, mode="bogus", velocity=[0.0] * 6, ref_R=np.eye(3),
            tcp_T=np.eye(4), jog_vmax=0.5,
        )
