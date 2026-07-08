"""Eye-in-hand pose stamping for Camera2dCore (no GenTL/camera needed).

Exercises ``Camera2dCore._camera_pose`` math: world<-optical =
T_world_flange @ T_flange_optical, decomposed to {frame, xyz, quat}. The core
only needs a session stub (it declares two publishers at construction); the
backend is unused by the pose path.
"""

from __future__ import annotations

import numpy as np

from wf.core.frames import (
    make_transform,
    quaternion_to_rotation_matrix,
    rpy_deg_to_matrix,
)
from wf.hal.camera2d_core import Camera2dCore


class _FakePub:
    def put(self, *a, **k):
        pass


class _FakeSession:
    def declare_publisher(self, *a, **k):
        return _FakePub()


def _core(mount_xyz=(0.0, 0.0, 0.05), mount_rpy_deg=(0.0, 0.0, 0.0)) -> Camera2dCore:
    params = {
        "mount_arm": "r1",
        "mount_xyz": list(mount_xyz),
        "mount_rpy_deg": list(mount_rpy_deg),
    }
    return Camera2dCore(_FakeSession(), "cell", "cam0", params, backend=None)


def test_pose_none_before_flange():
    assert _core()._camera_pose() is None


def test_pose_identity_flange_is_mount_offset():
    c = _core(mount_xyz=(0.0, 0.0, 0.05))
    c._flange_xyz = [0.0, 0.0, 0.0]
    c._flange_quat = [0.0, 0.0, 0.0, 1.0]
    pose = c._camera_pose()
    assert pose["frame"] == "world"
    assert np.allclose(pose["xyz"], [0.0, 0.0, 0.05])
    assert np.allclose(pose["quat"], [0.0, 0.0, 0.0, 1.0])


def test_pose_composes_flange_and_mount():
    c = _core(mount_xyz=(0.1, 0.0, 0.0))
    c._flange_xyz = [1.0, 2.0, 3.0]
    c._flange_quat = [0.0, 0.0, 0.0, 1.0]
    assert np.allclose(c._camera_pose()["xyz"], [1.1, 2.0, 3.0])


def test_pose_matches_explicit_matrix_product():
    c = _core(mount_xyz=(0.02, -0.01, 0.05), mount_rpy_deg=(10.0, 0.0, 90.0))
    flange_xyz = [0.3, -0.2, 0.6]
    flange_quat = [0.0, 0.0, 0.3826834, 0.9238795]  # 45deg about Z
    c._flange_xyz = flange_xyz
    c._flange_quat = flange_quat
    pose = c._camera_pose()
    t_wf = make_transform(quaternion_to_rotation_matrix(flange_quat), flange_xyz)
    t_fo = make_transform(rpy_deg_to_matrix([10.0, 0.0, 90.0]), [0.02, -0.01, 0.05])
    expected = (t_wf @ t_fo)[:3, 3]
    assert np.allclose(pose["xyz"], expected)
