"""ArmCore.jog_step gate, isolated from any backend's motion application.

A minimal fake backend supplies a fixed ``latest_q`` and a toggleable
``motion_block_reason``; the test asserts the qd / freeze-sentinel / idle
contract of ``jog_step`` across the arming gates. The frame-alignment math is
proven in ``world_model/tests/test_jog.py``.
"""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest

from wf.contracts.arm import keys
from wf.contracts.arm.messages import JogCommand
from wf.core.frametree import FrameTree
from wf.core.lease import ControlLease
from wf.hal.arm_core import ArmBackend, ArmCore
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.fk import UrdfFk
from wf.world_model.validate import TCP_FLANGE

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]


class _FakeActionServer:
    active_goal_id = None


class _FakeBackend(ArmBackend):
    def __init__(self, q):
        self._q = list(q)
        self.block: str | None = None

    def start(self, core):  # pragma: no cover - unused
        pass

    def shutdown(self):  # pragma: no cover - unused
        pass

    def latest_q(self):
        return list(self._q)

    def motion_block_reason(self, *, for_goal):
        return self.block

    def apply_jog_velocity(self, qd):  # pragma: no cover - unused
        pass

    def halt_jog(self):  # pragma: no cover - unused
        pass

    def run_path(self, *a):  # pragma: no cover - unused
        pass

    def set_do(self, *a):  # pragma: no cover - unused
        pass


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


def _core(fk, *, client="c1") -> ArmCore:
    core = object.__new__(ArmCore)
    core.rid = "r1"
    core.base_frame = keys.base_frame("r1")
    core.fk = fk
    core._jog_lock = threading.Lock()
    core._tcp_lock = threading.Lock()
    core._active_tcp = (TCP_FLANGE, np.eye(4))
    core._jog_vmax = 0.5
    core._jog_damping = 0.05
    core._lease = ControlLease(30.0)
    core._lease.acquire(client, "tester")
    core.action_server = _FakeActionServer()
    core._jog_cmd = None
    core._jog_deadline = 0.0
    core._jog_tree = FrameTree({})
    core._jog_active = False
    core.backend = _FakeBackend(HOME_Q)
    return core


def _arm(core, *, vel, watchdog_s=0.25):
    core._jog_cmd = JogCommand(
        client_id="c1", mode="joint", frame="base", velocity=vel, t=0
    )
    core._jog_deadline = time.monotonic() + watchdog_s


def test_idle_returns_none(fk):
    core = _core(fk)
    assert core.jog_step() is None


def test_armed_returns_qd(fk):
    core = _core(fk)
    _arm(core, vel=[0.2, 0, 0, 0, 0, 0])
    qd = core.jog_step()
    assert qd is not None and any(qd)
    assert core._jog_active


def test_watchdog_freezes_once_then_idle(fk):
    core = _core(fk)
    _arm(core, vel=[0.2, 0, 0, 0, 0, 0])
    core.jog_step()  # active
    core._jog_deadline = time.monotonic() - 1.0
    assert core.jog_step() == [0.0] * 6  # freeze sentinel on the transition
    assert not core._jog_active
    assert core.jog_step() is None  # idle thereafter


def test_block_reason_disarms(fk):
    core = _core(fk)
    _arm(core, vel=[0.2, 0, 0, 0, 0, 0])
    core.jog_step()  # active
    core.backend.block = "mirroring"
    assert core.jog_step() == [0.0] * 6
    assert not core._jog_active


def test_goal_active_returns_none(fk):
    core = _core(fk)
    core.action_server.active_goal_id = "g1"
    _arm(core, vel=[0.5, 0, 0, 0, 0, 0])
    assert core.jog_step() is None
    assert not core._jog_active
