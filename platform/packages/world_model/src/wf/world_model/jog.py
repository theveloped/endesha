"""Hold-to-jog velocity math (frame + TCP aware). Pure numpy.

Maps an operator jog command to a 6-vector joint velocity. The controlled
point is the active TCP origin; cartesian translations/rotations are expressed
in the axes of a caller-resolved reference frame (``ref_R``, the frame's axes
in the arm base). A pure rotation jog turns the TCP about its OWN origin.

No tree/config/zenoh deps — the driver resolves ``ref_R`` and supplies the
active ``tcp_T`` (``T_flange<-tcp``).
"""

from __future__ import annotations

import numpy as np

from .fk import UrdfFk
from .ik import numeric_jacobian


def jog_joint_velocity(
    fk: UrdfFk,
    q,
    *,
    mode: str,
    velocity,
    ref_R: np.ndarray,
    tcp_T: np.ndarray,
    jog_vmax: float,
    damping: float = 0.05,
) -> list[float]:
    """Joint velocity (rad/s) for one jog command.

    ``mode="joint"``: ``velocity`` is the per-joint target (passthrough).
    ``mode="cartesian"``: ``velocity`` is ``[vx, vy, vz, wx, wy, wz]`` in
    ``ref_R``'s axes; the controlled point is the TCP origin and rotation is
    about it. Every component is clamped to ``|qd_i| <= jog_vmax``.
    """
    velocity = np.asarray(velocity, dtype=np.float64)
    if mode == "joint":
        qd = velocity
    elif mode == "cartesian":
        ref_R = np.asarray(ref_R, dtype=np.float64)
        tcp_T = np.asarray(tcp_T, dtype=np.float64)
        v_base = ref_R @ velocity[:3]
        w_base = ref_R @ velocity[3:]
        T = fk.get_ee_transform(q)
        R_flange = T[:3, :3]
        # flange-origin -> TCP-origin vector, in base axes
        r = R_flange @ tcp_T[:3, 3]
        # hold the TCP origin fixed under a pure w -> rotate about the TCP
        v_flange = v_base - np.cross(w_base, r)
        twist = np.concatenate([v_flange, w_base])
        J = numeric_jacobian(fk, q, T_current=T)
        qd = J.T @ np.linalg.solve(J @ J.T + damping**2 * np.eye(6), twist)
    else:
        raise ValueError(f"mode must be 'joint' or 'cartesian', got {mode!r}")

    qd = np.clip(qd, -jog_vmax, jog_vmax)
    return [float(v) for v in qd]
