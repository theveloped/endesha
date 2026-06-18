"""Sim-arm jog integration over the ArmCore seam: armed / watchdog / lease /
goal-gate / joint-limit clamp.

Drives the jog path without a zenoh session: an ``ArmCore`` and a
``SimArmBackend`` are built via ``object.__new__`` with only the attributes the
jog path touches. The gate (lease/goal/watchdog) lives in ``ArmCore.jog_step``;
the integrate + clamp lives in ``SimArmBackend.apply_jog_velocity``. The
frame-alignment math itself is proven in ``world_model/tests/test_jog.py``.
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
from wf.hal.arm_core import ArmCore
from wf.hal.arm_sim.backend import SimArmBackend
from wf.hal.arm_sim.sim import SimArm
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.fk import UrdfFk
from wf.world_model.validate import TCP_FLANGE

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
DT = 0.005


class _FakeActionServer:
    active_goal_id = None


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


def _core(fk, *, client="c1") -> ArmCore:
    """An ArmCore + SimArmBackend wired with only what the jog path reads."""
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
    core._jog_tree = FrameTree({})  # empty -> base resolves to identity
    core._jog_active = False
    limits = fk.get_joint_limits()
    ordered = [limits[name] for name in fk.JOINT_ORDER]
    core.jmin = [lo for lo, _ in ordered]
    core.jmax = [hi for _, hi in ordered]
    core.servo_dt = DT

    backend = object.__new__(SimArmBackend)
    backend.sim = SimArm(fk, HOME_Q)
    backend.lock = threading.Lock()
    backend.core = core
    backend.mirror_realm = None
    core.backend = backend
    return core


def _arm(core, cmd, *, watchdog_s=0.25):
    core._jog_cmd = cmd
    core._jog_deadline = time.monotonic() + watchdog_s


def _tick(core):
    """One backend jog step: compute via core, apply via backend."""
    qd = core.jog_step()
    if qd is not None:
        if any(qd):
            core.backend.apply_jog_velocity(qd)
        else:
            core.backend.halt_jog()
    return qd


def test_joint_jog_advances_q(fk):
    core = _core(fk)
    sim = core.backend.sim
    _arm(core, JogCommand(client_id="c1", mode="joint",
                          frame="base", velocity=[0.2, 0, 0, 0, 0, 0], t=0))
    q0 = list(sim.q)
    _tick(core)
    assert core._jog_active
    assert sim.q[0] == pytest.approx(q0[0] + 0.2 * DT)
    assert sim.qd[0] == pytest.approx(0.2)


def test_watchdog_freezes_after_expiry(fk):
    core = _core(fk)
    sim = core.backend.sim
    _arm(core, JogCommand(client_id="c1", mode="joint",
                          frame="base", velocity=[0.2, 0, 0, 0, 0, 0], t=0))
    _tick(core)
    assert core._jog_active
    q_after = list(sim.q)

    core._jog_deadline = time.monotonic() - 1.0  # watchdog lapsed
    _tick(core)
    assert not core._jog_active
    assert sim.qd == [0.0] * 6, "expired watchdog must freeze velocity"
    assert sim.q == q_after, "frozen arm holds its last pose"


def test_lease_loss_disarms(fk):
    core = _core(fk)
    sim = core.backend.sim
    _arm(core, JogCommand(client_id="c1", mode="joint",
                          frame="base", velocity=[0.2, 0, 0, 0, 0, 0], t=0))
    _tick(core)
    assert core._jog_active
    core._lease.release("c1")  # holder gone
    _tick(core)
    assert not core._jog_active
    assert sim.qd == [0.0] * 6


def test_goal_active_blocks_jog(fk):
    core = _core(fk)
    sim = core.backend.sim
    core.action_server.active_goal_id = "g1"
    _arm(core, JogCommand(client_id="c1", mode="joint",
                          frame="base", velocity=[0.5, 0, 0, 0, 0, 0], t=0))
    q0 = list(sim.q)
    _tick(core)
    assert not core._jog_active
    assert sim.q == q0


def test_joint_limit_clamp(fk):
    core = _core(fk)
    sim = core.backend.sim
    sim.set_q([core.jmax[0] - 1e-4] + HOME_Q[1:])  # joint 0 at its max
    _arm(core, JogCommand(client_id="c1", mode="joint",
                          frame="base", velocity=[0.5, 0, 0, 0, 0, 0], t=0))
    _tick(core)
    assert sim.q[0] == pytest.approx(core.jmax[0])
    assert sim.q[0] <= core.jmax[0] + 1e-12
