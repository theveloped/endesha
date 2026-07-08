"""Integration test: run the demo_pick control-flow GRAPH over the in-process
sim realm (no mocks), driving a real ArmCore(SimArmBackend) over the bus.

Stands up the config service + sim arm on one peer session and the task_runner
(loaded with the demo_pick graph doc) on a linked peer, seeds the two named
poses, issues ``cmd/start``, and asserts the graph walked every node, the arm
executed the moves, and the grip (tool DO) fired. Arm-only — no camera needed.
"""

from __future__ import annotations

import contextlib
import tempfile
import time
from pathlib import Path

import pytest

from wf.contracts.task import keys as task_keys
from wf.core.codec import decode, encode
from wf.core.testing import linked_sessions
from wf.services.config import keys as config_keys
from wf.hal.aubo_i10 import BUNDLED_URDF

REALM = "sim"
RID = "r1"
CID = "cam0"

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
GRAPH = Path(__file__).resolve().parents[1] / "graphs" / "flows" / "demo_pick.yaml"


def _query_ok(session, key, payload, timeout_s=5.0):
    for reply in session.get(key, payload=encode(payload), timeout=timeout_s):
        if reply.ok is not None:
            return decode(reply.ok.payload)
    return None


def _sim_params() -> dict:
    from wf.hal.arm_sim import config as simcfg

    params = {
        k: (list(v) if isinstance(v, list) else v)
        for k, v in simcfg._PARAM_DEFAULTS.items()
    }
    params["urdf"] = BUNDLED_URDF
    params["home_q"] = list(HOME_Q)
    params["ruckig_defaults"] = {k: list(v) for k, v in simcfg._RUCKIG_DEFAULTS.items()}
    params["cartesian_defaults"] = dict(simcfg._CARTESIAN_DEFAULTS)
    return params


def _seed_pose(session, name, q) -> None:
    reply = _query_ok(
        session,
        config_keys.cmd_set(),
        {"key": config_keys.pose(name), "value": {"q": [float(v) for v in q]}},
    )
    assert reply is not None and reply.get("ok"), reply


@contextlib.contextmanager
def _config_store():
    from wf.services.config.store import ConfigStore

    with tempfile.TemporaryDirectory() as d:
        yield ConfigStore(d)


def test_demo_pick_graph_runs_over_sim():
    from wf.hal.arm_core import ArmCore
    from wf.hal.arm_sim.backend import SimArmBackend
    from wf.services.config.service import ConfigService
    from wf.services.task_runner.service import TaskRunnerService
    from wf.services.task_runner.spec import load_flow

    graph = load_flow(GRAPH)
    assert graph.name == "demo_pick"

    approach = list(HOME_Q)
    approach[0] += 0.1
    grasp = list(HOME_Q)
    grasp[0] += 0.2

    with linked_sessions() as (sa, sb), _config_store() as store:
        cfg = ConfigService(sa, store)
        cfg.start()
        backend = SimArmBackend(HOME_Q)
        arm = ArmCore(sa, REALM, RID, _sim_params(), backend, driver_version="test")
        arm.start()
        try:
            _seed_pose(sa, "pick_approach", approach)
            _seed_pose(sa, "pick_grasp", grasp)

            svc = TaskRunnerService(sb, REALM, graph, rid=RID, cid=CID)
            svc.start()
            try:
                states: list[dict] = []
                results: list[dict] = []
                state_sub = sb.declare_subscriber(
                    task_keys.state(REALM, "demo_pick"),
                    lambda s: states.append(decode(s.payload)),
                )
                result_sub = sb.declare_subscriber(
                    task_keys.result(REALM, "demo_pick"),
                    lambda s: results.append(decode(s.payload)),
                )
                try:
                    reply = _query_ok(sb, task_keys.cmd_start(REALM, "demo_pick"), {})
                    assert reply == {"ok": True, "flow": "demo_pick"}

                    deadline = time.monotonic() + 30.0
                    while not results and time.monotonic() < deadline:
                        time.sleep(0.05)
                    assert results, "no result published within 30s"
                    res = results[-1]
                    assert res["ok"] is True, res

                    # every node was entered (start + the four steps)
                    seen = {
                        s.get("active") for s in states if s.get("active") is not None
                    }
                    assert {"approach", "grasp", "close", "retreat"} <= seen

                    # grip closed -> tool DO pin 0 high; arm retreated to approach
                    assert backend.sim.tool_do_bits & 1 == 1
                    assert backend.sim.q[0] == pytest.approx(approach[0], abs=1e-2)
                finally:
                    state_sub.undeclare()
                    result_sub.undeclare()
            finally:
                svc.shutdown()
        finally:
            arm.shutdown()
            cfg.shutdown()
