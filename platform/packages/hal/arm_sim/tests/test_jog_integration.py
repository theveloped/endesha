"""Sim-arm jog integration: ``_apply_jog`` armed/disarmed/watchdog/clamp.

Drives the integration logic without a zenoh session: the driver is built via
``object.__new__`` with only the attributes ``_apply_jog`` touches. The
frame-alignment math itself is proven in ``world_model/tests/test_jog.py``;
here we cover the tick-loop branches (arming gate, watchdog freeze, lease loss,
joint-limit clamp).
"""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest

from wf.contracts.arm.messages import JogCommand
from wf.core.frametree import FrameTree
from wf.core.lease import ControlLease
from wf.hal.arm_sim.__main__ import SimArmDriver
from wf.hal.arm_sim.sim import SimArm
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.fk import UrdfFk

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
DT = 0.005


class _FakeActionServer:
    active_goal_id = None


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


def _driver(fk, *, client="c1") -> SimArmDriver:
    d = object.__new__(SimArmDriver)
    d.rid = "r1"
    d.sim = SimArm(fk, HOME_Q)
    d.mirror_realm = None
    d.action_server = _FakeActionServer()
    d._lock = threading.Lock()
    d._tcp_lock = threading.Lock()
    d._active_tcp = ("flange", np.eye(4))
    limits = fk.get_joint_limits()
    ordered = [limits[name] for name in fk.JOINT_ORDER]
    d._jmin = [lo for lo, _ in ordered]
    d._jmax = [hi for _, hi in ordered]
    d._jog_vmax = 0.5
    d._jog_damping = 0.05
    d._lease = ControlLease(ttl_s=30.0)
    d._lease.acquire(client, "tester")
    d._jog_tree = FrameTree({})  # empty -> base resolves to identity
    d._jog_cmd = None
    d._jog_deadline = 0.0
    d._jog_active = False
    return d


def _arm(d, cmd, *, watchdog_s=0.25):
    d._jog_cmd = cmd
    d._jog_deadline = time.monotonic() + watchdog_s


def test_joint_jog_advances_q(fk):
    d = _driver(fk)
    _arm(d, JogCommand(client_id="c1", mode="joint",
                       frame="base", velocity=[0.2, 0, 0, 0, 0, 0], t=0))
    q0 = list(d.sim.q)
    d._apply_jog(DT)
    assert d._jog_active
    assert d.sim.q[0] == pytest.approx(q0[0] + 0.2 * DT)
    assert d.sim.qd[0] == pytest.approx(0.2)


def test_watchdog_freezes_after_expiry(fk):
    d = _driver(fk)
    _arm(d, JogCommand(client_id="c1", mode="joint",
                       frame="base", velocity=[0.2, 0, 0, 0, 0, 0], t=0))
    d._apply_jog(DT)
    assert d._jog_active
    q_after = list(d.sim.q)

    d._jog_deadline = time.monotonic() - 1.0  # watchdog lapsed
    d._apply_jog(DT)
    assert not d._jog_active
    assert d.sim.qd == [0.0] * 6, "expired watchdog must freeze velocity"
    assert d.sim.q == q_after, "frozen arm holds its last pose"


def test_lease_loss_disarms(fk):
    d = _driver(fk)
    _arm(d, JogCommand(client_id="c1", mode="joint",
                       frame="base", velocity=[0.2, 0, 0, 0, 0, 0], t=0))
    d._apply_jog(DT)
    assert d._jog_active
    d._lease.release("c1")  # holder gone
    d._apply_jog(DT)
    assert not d._jog_active
    assert d.sim.qd == [0.0] * 6


def test_goal_active_blocks_jog(fk):
    d = _driver(fk)
    d.action_server.active_goal_id = "g1"
    _arm(d, JogCommand(client_id="c1", mode="joint",
                       frame="base", velocity=[0.5, 0, 0, 0, 0, 0], t=0))
    q0 = list(d.sim.q)
    d._apply_jog(DT)
    assert not d._jog_active
    assert d.sim.q == q0


def test_joint_limit_clamp(fk):
    d = _driver(fk)
    d.sim.set_q([d._jmax[0] - 1e-4] + HOME_Q[1:])  # joint 0 at its max
    _arm(d, JogCommand(client_id="c1", mode="joint",
                       frame="base", velocity=[0.5, 0, 0, 0, 0, 0], t=0))
    d._apply_jog(DT)
    assert d.sim.q[0] == pytest.approx(d._jmax[0])
    assert d.sim.q[0] <= d._jmax[0] + 1e-12
