"""End-to-end task_runner tests against the in-process sim realm (no mocks).

The full-stack inspection test stands up config + arm_sim + camera2d_sim + the
``demo_detect`` DetectorPipeline + the task_runner over two linked peer sessions
and runs the ``demo_inspect`` statechart to completion, asserting the aggregated
result, the parallel-region overlap, and the pipeline result/overlay output.

The camera renderer requires the OSMesa backend (Linux/Docker only); the
full-stack test skips cleanly where it is absent. The unknown-pose rejection
test needs no renderer and runs everywhere.
"""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest

from wf.contracts.task import keys as task_keys
from wf.contracts.vision import keys as vision_keys
from wf.core.codec import decode, encode
from wf.core.testing import linked_sessions
from wf.services.config import keys as config_keys

REALM = "sim"
RID = "r1"
CID = "cam0"
# Joint config whose eye-in-hand camera looks down at a nearby board; verified
# in the sim container to render a decodable DataMatrix. The board is placed at
# this pose's camera/z=0 intersection (see _compute_board_xyz).
INSPECT_Q = [0.0, 0.6, 1.6727272727272728, -0.6981, 1.6384615384615384, 0.0]
# Three distinct above poses for the demo flow. They differ in the base joint so
# the arm visibly swings between them (real moves), while keeping the wrist-down
# config. The board sits under ``belt_above`` (j0 == INSPECT_Q's), so a frame
# grabbed there decodes; the other two are off-board.
ABOVE_QS = {
    "belt_above": INSPECT_Q,
    "left_above": [0.4, *INSPECT_Q[1:]],
    "right_above": [-0.4, *INSPECT_Q[1:]],
}


def _wait_until(predicate, timeout_s, message):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        val = predicate()
        if val:
            return val
        time.sleep(0.05)
    raise AssertionError(message)


def _set_config(session, key, value, timeout_s=5.0):
    replies = session.get(
        config_keys.cmd_set(),
        payload=encode({"key": key, "value": value}),
        timeout=timeout_s,
    )
    for reply in replies:
        if reply.ok is not None:
            out = decode(reply.ok.payload)
            assert out.get("ok"), f"config set failed for {key}: {out}"
            return
    raise AssertionError(f"no reply from config set for {key}")


def _query_ok(session, key, payload, timeout_s=5.0):
    replies = session.get(key, payload=encode(payload), timeout=timeout_s)
    for reply in replies:
        if reply.ok is not None:
            return decode(reply.ok.payload)
    return None


# ── unknown-pose rejection (no renderer needed) ────────────────────────────


def test_unknown_pose_rejected_without_motion():
    from wf.services.config.service import ConfigService
    from wf.services.config.store import ConfigStore
    from wf.services.task_runner.service import TaskRunnerService
    from wf.services.task_runner.spec import validate_spec

    with linked_sessions() as (sa, sb), _tmp_config(sa) as store:
        cfg = ConfigService(sa, store)
        cfg.start()
        try:
            spec = validate_spec(
                {
                    "name": "bad_flow_test",
                    "poses": ["does_not_exist"],
                    "vision": {"format": "DataMatrix", "pipeline": "x_detect"},
                    "conveyor": {"timeout_s": 0.5},
                }
            )
            svc = TaskRunnerService(sb, REALM, spec, rid=RID, cid=CID)
            svc.start()
            try:
                reply = _query_ok(
                    sb, task_keys.cmd_start(REALM, "bad_flow_test"), {}
                )
                assert reply == {
                    "ok": False,
                    "error": "unknown_pose:does_not_exist",
                }
            finally:
                svc.shutdown()
        finally:
            cfg.shutdown()


# ── full-stack inspection (renderer-gated) ─────────────────────────────────


def _compute_board_xyz(q):
    """Where the eye-in-hand camera optical axis hits z=0 for joint config ``q``.

    Lets the test place the DataMatrix board exactly under the camera's view at
    the seeded pose, so a grabbed frame contains a decodable symbol.
    """
    from wf.core.frames import make_transform, quaternion_to_rotation_matrix
    from wf.hal.aubo_i10 import BUNDLED_URDF
    from wf.hal.arm_sim.sim import SimArm
    from wf.world_model.fk import UrdfFk

    arm = SimArm(UrdfFk(BUNDLED_URDF), q)
    flange = arm.flange_pose(RID)
    T_wf = make_transform(
        quaternion_to_rotation_matrix(flange.quat), flange.xyz
    )
    # mount: optical 0.05 m beyond flange +Z, rpy 0 (camera2d_sim defaults).
    T_fo = make_transform(np.eye(3), [0.0, 0.0, 0.05])
    T_wo = T_wf @ T_fo
    origin = T_wo[:3, 3]
    z_axis = T_wo[:3, 2]  # optical +Z (view direction)
    if abs(z_axis[2]) < 1e-6:
        pytest.skip("camera not looking toward the z=0 plane at this pose")
    t = -origin[2] / z_axis[2]
    hit = origin + t * z_axis
    return [float(hit[0]), float(hit[1]), 0.0]


def test_demo_inspect_end_to_end():
    pytest.importorskip("pyrender")
    try:
        import pyrender  # noqa: F401
    except BaseException as exc:  # noqa: BLE001
        pytest.skip(f"pyrender backend unavailable: {exc!r}")

    from wf.hal.arm_sim.__main__ import SimArmDriver
    from wf.hal.arm_sim.config import load_resource as load_arm
    from wf.hal.camera2d_sim.__main__ import SimCameraDriver
    from wf.hal.camera2d_sim.config import load_resource as load_cam
    from wf.services.config.service import ConfigService
    from wf.services.config.store import ConfigStore
    from wf.services.task_runner.service import TaskRunnerService
    from wf.services.task_runner.spec import validate_spec
    from wf.services.vision.service import DetectorPipeline

    cell = _write_test_cell()
    board_xyz = _compute_board_xyz(INSPECT_Q)

    with linked_sessions() as (sa, sb), _tmp_config(sa) as store:
        cfg = ConfigService(sa, store)
        cfg.start()
        cleanup = [cfg.shutdown]
        try:
            # Seed the demo poses; only belt_above looks at the board, the
            # other two swing the arm off-board (real moves between poses).
            for name, q in ABOVE_QS.items():
                _set_config(sa, config_keys.pose(name), {"q": list(q)})
            _set_config(
                sa,
                config_keys.scene("datamatrix_part"),
                {
                    "frame": "world",
                    "pose": {"xyz": board_xyz, "quat": [0, 0, 0, 1]},
                    "geometry": {"type": "mesh", "uri": "asset://wf/datamatrix_part.glb"},
                },
            )

            try:
                arm = SimArmDriver(sa, REALM, RID, load_arm(cell, RID), None)
            except Exception as exc:  # noqa: BLE001
                pytest.skip(f"arm_sim unavailable: {exc!r}")
            arm.start()
            cleanup.append(arm.shutdown)

            try:
                cam = SimCameraDriver(sa, REALM, CID, load_cam(cell, CID))
            except RuntimeError as exc:
                pytest.skip(f"camera render backend unavailable: {exc}")
            cam.start()
            cleanup.append(cam.shutdown)

            detector = DetectorPipeline(
                sb,
                REALM,
                "demo_detect",
                input_topic=f"{REALM}/camera2d/{CID}/image",
                fmt="DataMatrix",
            )
            detector.start()
            cleanup.append(detector.shutdown)

            # record overlay frames + results the pipeline publishes
            overlays = []
            results = []
            osub = sb.declare_subscriber(
                vision_keys.image(REALM, "demo_detect"),
                lambda s: overlays.append(bytes(s.payload)),
            )
            rsub = sb.declare_subscriber(
                vision_keys.result(REALM, "demo_detect"),
                lambda s: results.append(decode(s.payload)),
            )
            cleanup.append(osub.undeclare)
            cleanup.append(rsub.undeclare)

            spec = validate_spec(
                {
                    "name": "demo_inspect",
                    "poses": ["belt_above", "left_above", "right_above"],
                    "vision": {
                        "format": "DataMatrix",
                        "min_count": 1,
                        "pipeline": "demo_detect",
                    },
                    "conveyor": {"do_pin": 0, "di_pin": 0, "timeout_s": 2.0},
                }
            )
            svc = TaskRunnerService(sb, REALM, spec, rid=RID, cid=CID)
            svc.start()
            cleanup.append(svc.shutdown)

            # record state snapshots to prove parallel-region overlap
            states = []
            ssub = sb.declare_subscriber(
                task_keys.state(REALM, "demo_inspect"),
                lambda s: states.append(decode(s.payload)),
            )
            cleanup.append(ssub.undeclare)

            final_result = []
            fsub = sb.declare_subscriber(
                task_keys.result(REALM, "demo_inspect"),
                lambda s: final_result.append(decode(s.payload)),
            )
            cleanup.append(fsub.undeclare)

            time.sleep(0.5)  # let routes settle
            start = _query_ok(sb, task_keys.cmd_start(REALM, "demo_inspect"), {})
            assert start == {"ok": True, "flow": "demo_inspect"}

            _wait_until(
                lambda: final_result[0] if final_result else None,
                60.0,
                "no demo_inspect result published",
            )
            res = final_result[0]
            assert res["ok"] is True, res
            assert "WF-PART-0042" in res["summary"]["codes"]
            assert res["summary"]["conveyor"]["tripped_by"] == "timeout"

            # both regions active simultaneously in at least one snapshot
            both = any(
                any(cid in ("inspecting", "inspected") for cid in s["configuration"])
                and any(cid in ("running", "stopped") for cid in s["configuration"])
                for s in states
            )
            assert both, f"no snapshot showed both regions active: {[s['configuration'] for s in states]}"

            # pipeline emitted detections + overlay frames
            assert any(r["detections"] for r in results), "no non-empty detection result"
            assert overlays, "no overlay frames published"
        finally:
            for fn in reversed(cleanup):
                try:
                    fn()
                except Exception:
                    pass


# ── helpers ────────────────────────────────────────────────────────────────


import contextlib
import tempfile


@contextlib.contextmanager
def _tmp_config(session):
    from wf.services.config.store import ConfigStore

    with tempfile.TemporaryDirectory() as d:
        yield ConfigStore(d)


def _write_test_cell() -> str:
    """A cell.yaml giving arm r1 + camera cam0 with a render block for the sim."""
    import tempfile
    import textwrap

    fd = tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    fd.write(
        textwrap.dedent(
            """
            cell_type: test-cell@0.1
            platform: 0.1.0
            resources:
              r1:
                contract: arm
                hal: arm_sim
                params: {}
              cam0:
                contract: camera2d
                hal: camera2d_sim
                params:
                  mount: flange
                  mount_arm: r1
                  render:
                    width: 800
                    height: 800
                    fx: 900.0
                    fy: 900.0
                    background_gray: 90
                    mount_xyz: [0.0, 0.0, 0.05]
                    mount_rpy_deg: [0.0, 0.0, 0.0]
                  stream_defaults: {rate_hz: 15.0, scale: 1.0, encoding: jpeg, quality: 90}
                  grab_defaults: {encoding: jpeg, quality: 90, scale: 1.0}
            """
        )
    )
    fd.close()
    return fd.name
