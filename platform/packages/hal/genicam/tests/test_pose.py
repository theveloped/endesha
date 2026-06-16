"""Eye-in-hand pose stamping for the genicam driver (no GenTL/camera needed).

Exercises ``GenicamDriver._camera_pose`` math: world<-optical =
T_world_flange @ T_flange_optical, decomposed to {frame, xyz, quat}. The
driver only needs a session stub (it declares two publishers at construction).
"""

from __future__ import annotations

import numpy as np

from wf.core.frames import (
    make_transform,
    quaternion_to_rotation_matrix,
    rpy_deg_to_matrix,
)
from wf.hal.genicam.__main__ import GenicamDriver


class _FakePub:
    def put(self, *a, **k):
        pass


class _FakeSession:
    def declare_publisher(self, *a, **k):
        return _FakePub()


def _driver(mount_xyz=(0.0, 0.0, 0.05), mount_rpy_deg=(0.0, 0.0, 0.0)):
    params = {
        "mount_arm": "r1",
        "mount_xyz": list(mount_xyz),
        "mount_rpy_deg": list(mount_rpy_deg),
        "cti_path": "x",
        "serial": None,
    }
    return GenicamDriver(_FakeSession(), "live", "cam0", params)


def test_pose_none_before_flange():
    # No flange sample yet -> pose is None (the UI frustum simply hides).
    assert _driver()._camera_pose() is None


def test_pose_identity_flange_is_mount_offset():
    d = _driver(mount_xyz=(0.0, 0.0, 0.05))
    # Identity flange (at origin, no rotation): optical origin = mount offset.
    d._flange_xyz = [0.0, 0.0, 0.0]
    d._flange_quat = [0.0, 0.0, 0.0, 1.0]
    pose = d._camera_pose()
    assert pose["frame"] == "world"
    assert np.allclose(pose["xyz"], [0.0, 0.0, 0.05])
    assert np.allclose(pose["quat"], [0.0, 0.0, 0.0, 1.0])


def test_pose_composes_flange_and_mount():
    d = _driver(mount_xyz=(0.1, 0.0, 0.0))
    # Flange translated; identity rotation -> optical = flange + mount offset.
    d._flange_xyz = [1.0, 2.0, 3.0]
    d._flange_quat = [0.0, 0.0, 0.0, 1.0]
    pose = d._camera_pose()
    assert np.allclose(pose["xyz"], [1.1, 2.0, 3.0])


def test_pose_matches_explicit_matrix_product():
    d = _driver(mount_xyz=(0.02, -0.01, 0.05), mount_rpy_deg=(10.0, 0.0, 90.0))
    flange_xyz = [0.3, -0.2, 0.6]
    flange_quat = [0.0, 0.0, 0.3826834, 0.9238795]  # 45deg about Z
    d._flange_xyz = flange_xyz
    d._flange_quat = flange_quat
    pose = d._camera_pose()
    t_wf = make_transform(quaternion_to_rotation_matrix(flange_quat), flange_xyz)
    t_fo = make_transform(rpy_deg_to_matrix([10.0, 0.0, 90.0]), [0.02, -0.01, 0.05])
    expected = (t_wf @ t_fo)[:3, 3]
    assert np.allclose(pose["xyz"], expected)
