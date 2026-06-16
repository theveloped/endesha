"""FK port golden-value tests (values computed from the reference impl)."""

import math

import numpy as np

from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.fk import UrdfFk

HOME = [0.0, math.radians(-30), math.radians(120), math.radians(-40), math.radians(90), 0.0]


def test_fk_zeros_golden():
    fk = UrdfFk(BUNDLED_URDF)
    T = fk.get_ee_transform([0.0] * 6)
    np.testing.assert_allclose(T[:3, 3], [0.0, -0.2953, 1.5132], atol=1e-4)


def test_fk_home_golden():
    fk = UrdfFk(BUNDLED_URDF)
    T = fk.get_ee_transform(HOME)
    np.testing.assert_allclose(T[:3, 3], [0.51338, -0.20130, 0.11885], atol=1e-3)
    np.testing.assert_allclose(T[:3, 0], [0.0, 1.0, 0.0], atol=1e-3)


def test_fk_rejects_wrong_dof():
    fk = UrdfFk(BUNDLED_URDF)
    try:
        fk.get_ee_transform([0.0] * 5)
    except ValueError:
        return
    raise AssertionError("expected ValueError for 5 joint angles")
