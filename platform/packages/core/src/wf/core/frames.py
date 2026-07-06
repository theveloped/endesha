"""Minimal frame math (numpy only).

The full time-aware frame resolver is a later roadmap phase; this module
carries only the conversion primitives lifted from the proven reference
implementation (Shepperd's method etc.). Quaternions are ``[qx, qy, qz, qw]``
(Hamilton, scalar last); transforms are 4x4 homogeneous matrices.
"""

from __future__ import annotations

import math

import numpy as np


def quaternion_to_rotation_matrix(q) -> np.ndarray:
    """Convert a quaternion ``[qx, qy, qz, qw]`` to a 3x3 rotation matrix."""
    q = np.asarray(q, dtype=np.float64)
    if q.shape != (4,):
        raise ValueError(f"expected quaternion of length 4, got shape {q.shape}")
    q = q / np.linalg.norm(q)
    qx, qy, qz, qw = q
    return np.array(
        [
            [1 - 2 * (qy**2 + qz**2), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
            [2 * (qx * qy + qz * qw), 1 - 2 * (qx**2 + qz**2), 2 * (qy * qz - qx * qw)],
            [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx**2 + qy**2)],
        ],
        dtype=np.float64,
    )


def rotation_matrix_to_quaternion(R) -> list[float]:
    """Convert a 3x3 rotation matrix to ``[qx, qy, qz, qw]`` (Shepperd's method)."""
    R = np.asarray(R, dtype=np.float64)
    trace = np.trace(R)

    if trace > 0:
        s = 0.5 / np.sqrt(trace + 1.0)
        qw = 0.25 / s
        qx = (R[2, 1] - R[1, 2]) * s
        qy = (R[0, 2] - R[2, 0]) * s
        qz = (R[1, 0] - R[0, 1]) * s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        qw = (R[2, 1] - R[1, 2]) / s
        qx = 0.25 * s
        qy = (R[0, 1] + R[1, 0]) / s
        qz = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        qw = (R[0, 2] - R[2, 0]) / s
        qx = (R[0, 1] + R[1, 0]) / s
        qy = 0.25 * s
        qz = (R[1, 2] + R[2, 1]) / s
    else:
        s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        qw = (R[1, 0] - R[0, 1]) / s
        qx = (R[0, 2] + R[2, 0]) / s
        qy = (R[1, 2] + R[2, 1]) / s
        qz = 0.25 * s

    return [float(qx), float(qy), float(qz), float(qw)]


def rotation_matrix_to_rotvec(R) -> np.ndarray:
    """Convert a 3x3 rotation matrix to an axis-angle vector (rad).

    Implemented via :func:`rotation_matrix_to_quaternion`:
    ``angle = 2*atan2(||v||, w)``, ``axis = v/||v||``. Returns zeros for
    ``||v|| < 1e-12`` (robust at 0 and pi).
    """
    qx, qy, qz, qw = rotation_matrix_to_quaternion(R)
    v = np.array([qx, qy, qz], dtype=np.float64)
    v_norm = float(np.linalg.norm(v))
    if v_norm < 1e-12:
        return np.zeros(3, dtype=np.float64)
    angle = 2.0 * math.atan2(v_norm, qw)
    return (angle / v_norm) * v


def make_transform(R, t) -> np.ndarray:
    """Create a 4x4 homogeneous transform from a 3x3 rotation and translation."""
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = np.asarray(R, dtype=np.float64)
    T[:3, 3] = np.asarray(t, dtype=np.float64).flatten()
    return T


def invert_transform(T) -> np.ndarray:
    """Invert a 4x4 homogeneous transform: T^-1 = [R^T, -R^T t]."""
    T = np.asarray(T, dtype=np.float64)
    R = T[:3, :3]
    t = T[:3, 3]
    T_inv = np.eye(4, dtype=np.float64)
    T_inv[:3, :3] = R.T
    T_inv[:3, 3] = -R.T @ t
    return T_inv


def transform_to_xyz_quat(T) -> tuple[list[float], list[float]]:
    """Decompose a 4x4 homogeneous transform into ``(xyz, [qx,qy,qz,qw])``.

    Inverse of ``make_transform(quaternion_to_rotation_matrix(quat), xyz)``.
    Translation in metres; quaternion Hamilton scalar-last.
    """
    T = np.asarray(T, dtype=np.float64)
    xyz = [float(v) for v in T[:3, 3]]
    quat = rotation_matrix_to_quaternion(T[:3, :3])
    return xyz, quat


def slerp(q0, q1, s: float) -> list[float]:
    """Spherical linear interpolation between quaternions ``[qx,qy,qz,qw]``.

    Returns the unit quaternion ``s`` of the way (``s in [0,1]``) from ``q0`` to
    ``q1`` along the shortest geodesic (the nearer of ``q1``/``-q1`` is used, so
    ``q`` and ``-q`` — the same rotation — never take the long way round). Falls
    back to normalised linear interpolation for nearly-parallel inputs.
    """
    a = np.asarray(q0, dtype=np.float64)
    b = np.asarray(q1, dtype=np.float64)
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    dot = float(np.dot(a, b))
    if dot < 0.0:  # shortest path: q and -q are the same rotation
        b = -b
        dot = -dot
    if dot > 0.9995:  # nearly parallel — lerp + renormalise
        out = a + s * (b - a)
        return [float(v) for v in out / np.linalg.norm(out)]
    theta0 = math.acos(dot)
    theta = theta0 * s
    sin0 = math.sin(theta0)
    w0 = math.sin(theta0 - theta) / sin0
    w1 = math.sin(theta) / sin0
    out = w0 * a + w1 * b
    return [float(v) for v in out / np.linalg.norm(out)]


def rpy_to_matrix(rpy) -> np.ndarray:
    """Convert roll-pitch-yaw (extrinsic XYZ) to a 3x3 rotation matrix.

    Equivalent to ``scipy.spatial.transform.Rotation.from_euler("xyz", rpy)``:
    ``R = Rz(yaw) @ Ry(pitch) @ Rx(roll)``.
    """
    roll, pitch, yaw = (float(v) for v in rpy)
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ],
        dtype=np.float64,
    )


def rpy_deg_to_matrix(rpy_deg) -> np.ndarray:
    """``rpy_to_matrix`` for roll-pitch-yaw given in DEGREES."""
    return rpy_to_matrix([math.radians(float(a)) for a in rpy_deg])
