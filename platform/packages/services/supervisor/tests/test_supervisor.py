"""End-to-end supervisor test: real subprocess bring-up over a shared bus.

The supervisor spawns HAL + vision + task_runner CHILD processes; they each
open their own zenoh session, so the test bus must be reachable by name. We
listen on a fixed TCP endpoint and hand the children a zenoh config that
connects to it (the in-process test session listens; children connect).

Skipped: camera2d_sim was retired, so this e2e can no longer stand up a live
sim camera in-process — the sim camera is now the external headless-browser HAL.
"""

from __future__ import annotations

import json
import socket
import tempfile
import time
from pathlib import Path

import pytest

from wf.contracts.supervisor import keys as sup_keys
from wf.contracts.task import keys as task_keys
from wf.contracts.vision import keys as vision_keys
from wf.core.codec import decode, encode

REALM = "sim"
_REPO = Path(__file__).resolve().parents[4]  # platform/
_CELL = _REPO / "deploy" / "cell.sim.yaml"
_FLOWS = _REPO / "packages" / "services" / "task_runner" / "flows"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until(predicate, timeout_s, message):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        val = predicate()
        if val:
            return val
        time.sleep(0.1)
    raise AssertionError(message)


def _query(session, key, payload, timeout_s=10.0):
    for reply in session.get(key, payload=encode(payload), timeout=timeout_s):
        if reply.ok is not None:
            return decode(reply.ok.payload)
    return None


def _catalog_entry(session, name):
    cat = _query(session, sup_keys.flows_catalog(REALM), {})
    if cat is None:
        return None
    for f in cat["flows"]:
        if f["name"] == name:
            return f
    return None


def test_supervisor_end_to_end(tmp_path):
    pytest.skip(
        "camera2d_sim retired; sim camera is now the external headless-browser "
        "HAL — see deploy/Dockerfile.headless",
        allow_module_level=False,
    )

    import zenoh

    from wf.services.supervisor.cell import load_cell
    from wf.services.supervisor.service import SupervisorService
    from wf.services.config.service import ConfigService
    from wf.services.config.store import ConfigStore
    from wf.services.config import keys as config_keys
    from wf.core.frames import make_transform, quaternion_to_rotation_matrix
    from wf.hal.aubo_i10 import BUNDLED_URDF
    from wf.hal.arm_sim.sim import SimArm
    from wf.world_model.fk import UrdfFk
    import numpy as np

    inspect_q = [0.0, 0.6, 1.6727272727272728, -0.6981, 1.6384615384615384, 0.0]

    def _seed(sess):
        arm = SimArm(UrdfFk(BUNDLED_URDF), inspect_q)
        fl = arm.flange_pose("r1")
        T_wo = make_transform(
            quaternion_to_rotation_matrix(fl.quat), fl.xyz
        ) @ make_transform(np.eye(3), [0.0, 0.0, 0.05])
        o, z = T_wo[:3, 3], T_wo[:3, 2]
        board = (o + (-o[2] / z[2]) * z).tolist()
        board = [float(board[0]), float(board[1]), 0.0]
        # belt_above looks at the board; left/right swing j0 off-board so the
        # arm performs real moves between the demo poses.
        above_qs = {
            "belt_above": inspect_q,
            "left_above": [0.4, *inspect_q[1:]],
            "right_above": [-0.4, *inspect_q[1:]],
        }
        for name, q in above_qs.items():
            _query(sess, config_keys.cmd_set(), {"key": config_keys.pose(name), "value": {"q": list(q)}})
        _query(
            sess,
            config_keys.cmd_set(),
            {
                "key": config_keys.scene("datamatrix_part"),
                "value": {
                    "frame": "world",
                    "pose": {"xyz": board, "quat": [0, 0, 0, 1]},
                    "geometry": {"type": "mesh", "uri": "asset://wf/datamatrix_part.glb"},
                },
            },
        )

    port = _free_port()
    endpoint = f"tcp/127.0.0.1:{port}"

    # The test session listens; spawned children connect via this config file.
    listen_cfg = zenoh.Config()
    listen_cfg.insert_json5("mode", json.dumps("peer"))
    listen_cfg.insert_json5("scouting/multicast/enabled", "false")
    listen_cfg.insert_json5("listen/endpoints", json.dumps([endpoint]))
    session = zenoh.open(listen_cfg)

    child_cfg_path = tmp_path / "connect.json5"
    child_cfg_path.write_text(
        json.dumps(
            {
                "mode": "peer",
                "scouting": {"multicast": {"enabled": False}},
                "connect": {"endpoints": [endpoint]},
            }
        ),
        encoding="utf-8",
    )

    cleanup = []
    try:
        cfg = ConfigService(session, ConfigStore(str(tmp_path / "store")))
        cfg.start()
        cleanup.append(cfg.shutdown)
        _seed(session)  # poses + datamatrix board

        cell = load_cell(str(_CELL))
        sup = SupervisorService(
            session,
            REALM,
            cell,
            {},
            flows_dir=str(_FLOWS),
            with_config=False,
            zenoh_config=str(child_cfg_path),
        )
        sup.start()
        cleanup.append(sup.shutdown)

        # Catalog lists demo_inspect offline with resolved role bindings.
        entry = _wait_until(
            lambda: _catalog_entry(session, "demo_inspect"),
            10.0,
            "no demo_inspect in catalog",
        )
        assert entry["online"] is False
        assert entry["roles"]["arm"]["resource_id"] == "r1"
        assert entry["roles"]["cam"]["resource_id"] == "cam0"
        assert entry["error"] is None

        # Always-on vision runtime token appears (spawned with the cell).
        vision_live = {"v": False}
        vsub = session.liveliness().declare_subscriber(
            vision_keys.alive(REALM, "demo_detect"),
            handler=lambda s: vision_live.__setitem__(
                "v", s.kind == zenoh.SampleKind.PUT
            ),
            history=True,
        )
        cleanup.append(vsub.undeclare)
        _wait_until(
            lambda: vision_live["v"],
            30.0,
            "always-on vision runtime never came up",
        )

        # Bring the flow online -> task_runner spawns, token + online flip.
        reply = _query(session, sup_keys.flows_cmd_start(REALM), {"flow": "demo_inspect"})
        assert reply["ok"] is True, reply
        task_live = {"v": False}
        tsub = session.liveliness().declare_subscriber(
            task_keys.alive(REALM, "demo_inspect"),
            handler=lambda s: task_live.__setitem__(
                "v", s.kind == zenoh.SampleKind.PUT
            ),
            history=True,
        )
        cleanup.append(tsub.undeclare)
        _wait_until(
            lambda: task_live["v"],
            30.0,
            "task_runner token never appeared after start",
        )
        _wait_until(
            lambda: (_catalog_entry(session, "demo_inspect") or {}).get("online")
            is True,
            10.0,
            "catalog never flipped online",
        )

        # Drive the actual run through the supervisor-resolved task_runner.
        final_result = []
        fsub = session.declare_subscriber(
            task_keys.result(REALM, "demo_inspect"),
            lambda s: final_result.append(decode(s.payload)),
        )
        cleanup.append(fsub.undeclare)
        time.sleep(0.5)
        start = _query(session, task_keys.cmd_start(REALM, "demo_inspect"), {})
        assert start == {"ok": True, "flow": "demo_inspect"}, start
        res = _wait_until(
            lambda: final_result[0] if final_result else None,
            60.0,
            "no demo_inspect result published",
        )
        assert res["ok"] is True, res
        assert "WF-PART-0042" in res["summary"]["codes"]

        # Starting again -> already_online.
        again = _query(session, sup_keys.flows_cmd_start(REALM), {"flow": "demo_inspect"})
        assert again == {"ok": False, "error": "already_online"}, again

        # Stop -> task token gone, catalog offline, vision token still present.
        stop = _query(session, sup_keys.flows_cmd_stop(REALM), {"flow": "demo_inspect"})
        assert stop == {"ok": True}, stop
        _wait_until(
            lambda: (_catalog_entry(session, "demo_inspect") or {}).get("online")
            is False,
            15.0,
            "catalog never flipped offline after stop",
        )
        # vision runtime is cell-level, stays up
        assert vision_live["v"] is True

        # Unknown flow.
        nope = _query(session, sup_keys.flows_cmd_start(REALM), {"flow": "nope"})
        assert nope == {"ok": False, "error": "unknown_flow:nope"}, nope
    finally:
        for fn in reversed(cleanup):
            try:
                fn()
            except Exception:
                pass
        session.close()
