"""Frame math tests: quat<->matrix roundtrip, rpy against hand-computed."""

import math

import numpy as np
import pytest

from wf.core.frames import (
    invert_transform,
    make_transform,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_quaternion,
    rotation_matrix_to_rotvec,
    rpy_to_matrix,
)


@pytest.mark.parametrize(
    "quat",
    [
        [0.0, 0.0, 0.0, 1.0],
        [0.5, 0.5, 0.5, 0.5],
        [0.0, 0.7071067811865476, 0.0, 0.7071067811865476],
        [-0.5005, 0.4996, 0.4976, 0.5023],  # real hand-eye quat (not exactly unit)
    ],
)
def test_quat_matrix_roundtrip(quat):
    R = quaternion_to_rotation_matrix(quat)
    out = rotation_matrix_to_quaternion(R)
    q_in = np.asarray(quat) / np.linalg.norm(quat)
    q_out = np.asarray(out)
    # q and -q encode the same rotation.
    assert min(np.linalg.norm(q_out - q_in), np.linalg.norm(q_out + q_in)) < 1e-9


def test_quaternion_wrong_length_raises():
    with pytest.raises(ValueError):
        quaternion_to_rotation_matrix([0.0, 0.0, 1.0])


def test_rpy_90deg_about_x():
    R = rpy_to_matrix([math.pi / 2, 0.0, 0.0])
    # x stays, y -> z, z -> -y
    np.testing.assert_allclose(R @ [1, 0, 0], [1, 0, 0], atol=1e-12)
    np.testing.assert_allclose(R @ [0, 1, 0], [0, 0, 1], atol=1e-12)
    np.testing.assert_allclose(R @ [0, 0, 1], [0, -1, 0], atol=1e-12)


def test_rpy_90deg_about_z():
    R = rpy_to_matrix([0.0, 0.0, math.pi / 2])
    # x -> y, y -> -x
    np.testing.assert_allclose(R @ [1, 0, 0], [0, 1, 0], atol=1e-12)
    np.testing.assert_allclose(R @ [0, 1, 0], [-1, 0, 0], atol=1e-12)


def test_rpy_extrinsic_xyz_composition():
    # Extrinsic XYZ: R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
    roll, pitch, yaw = 0.3, -0.5, 1.1
    expected = (
        rpy_to_matrix([0, 0, yaw])
        @ rpy_to_matrix([0, pitch, 0])
        @ rpy_to_matrix([roll, 0, 0])
    )
    np.testing.assert_allclose(rpy_to_matrix([roll, pitch, yaw]), expected, atol=1e-12)


def test_invert_transform():
    R = rpy_to_matrix([0.2, 0.4, -0.7])
    T = make_transform(R, [1.0, -2.0, 0.5])
    np.testing.assert_allclose(invert_transform(T) @ T, np.eye(4), atol=1e-12)


def test_rotvec_identity_is_zero():
    np.testing.assert_allclose(rotation_matrix_to_rotvec(np.eye(3)), [0, 0, 0], atol=0)


def test_rotvec_90deg_about_z():
    R = rpy_to_matrix([0.0, 0.0, math.pi / 2])
    np.testing.assert_allclose(
        rotation_matrix_to_rotvec(R), [0.0, 0.0, math.pi / 2], atol=1e-9
    )


def test_rotvec_180deg_about_x():
    R = rpy_to_matrix([math.pi, 0.0, 0.0])
    rv = rotation_matrix_to_rotvec(R)
    assert abs(np.linalg.norm(rv) - math.pi) < 1e-9
    np.testing.assert_allclose(rv / np.linalg.norm(rv), [1.0, 0.0, 0.0], atol=1e-9)
