"""Live in-sim demo of the task_runner statechart (run inside the wf-sim container).

Brings up config + arm_sim + camera2d_sim + the demo_detect DetectorPipeline +
the task_runner over two linked peer sessions, seeds the three inspect poses and
the DataMatrix board, then runs `demo_inspect` and STREAMS every `state`
snapshot, the vision `result` topic, and the final `result` to stdout so you can
watch both parallel regions advance and the codes aggregate.

    docker run --rm \
      -v "$PWD/packages:/platform/packages" -v "$PWD/scripts:/platform/scripts" \
      wf-sim bash -c "source /activate.sh && python scripts/demo_task_runner_sim.py"
"""

from __future__ import annotations

import tempfile
import textwrap
import time

import numpy as np

from wf.contracts.task import keys as task_keys
from wf.contracts.vision import keys as vision_keys
from wf.core.codec import decode, encode
from wf.core.frames import make_transform, quaternion_to_rotation_matrix
from wf.core.testing import linked_sessions
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.hal.arm_sim.__main__ import SimArmDriver
from wf.hal.arm_sim.config import load_resource as load_arm
from wf.hal.arm_sim.sim import SimArm
from wf.hal.camera2d_sim.__main__ import SimCameraDriver
from wf.hal.camera2d_sim.config import load_resource as load_cam
from wf.services.config import keys as config_keys
from wf.services.config.service import ConfigService
from wf.services.config.store import ConfigStore
from wf.services.task_runner.service import TaskRunnerService
from wf.services.task_runner.spec import load_spec
from wf.services.vision.service import DetectorPipeline
from wf.world_model.fk import UrdfFk

REALM, RID, CID = "sim", "r1", "cam0"
INSPECT_Q = [0.0, 0.6, 1.6727272727272728, -0.6981, 1.6384615384615384, 0.0]
FLOW = "packages/services/task_runner/flows/demo_inspect.yaml"


def _board_xyz(q):
    arm = SimArm(UrdfFk(BUNDLED_URDF), q)
    fl = arm.flange_pose(RID)
    T_wo = make_transform(quaternion_to_rotation_matrix(fl.quat), fl.xyz) @ make_transform(
        np.eye(3), [0.0, 0.0, 0.05]
    )
    o, z = T_wo[:3, 3], T_wo[:3, 2]
    hit = o + (-o[2] / z[2]) * z
    return [float(hit[0]), float(hit[1]), 0.0]


def _set(session, key, value):
    for r in session.get(
        config_keys.cmd_set(), payload=encode({"key": key, "value": value}), timeout=5.0
    ):
        if r.ok is not None:
            assert decode(r.ok.payload).get("ok"), f"set {key} failed"
            return


def _cell():
    fd = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
    fd.write(
        textwrap.dedent(
            """
            cell_type: demo@0.1
            platform: 0.1.0
            resources:
              r1: {contract: arm, hal: arm_sim, params: {}}
              cam0:
                contract: camera2d
                hal: camera2d_sim
                params:
                  mount: flange
                  mount_arm: r1
                  render: {width: 800, height: 800, fx: 900.0, fy: 900.0, background_gray: 90, mount_xyz: [0,0,0.05], mount_rpy_deg: [0,0,0]}
                  grab_defaults: {encoding: jpeg, quality: 90, scale: 1.0}
            """
        )
    )
    fd.close()
    return fd.name


def main() -> None:
    spec = load_spec(FLOW)
    cell = _cell()
    board = _board_xyz(INSPECT_Q)
    print(f"board placed at {board}")

    with linked_sessions() as (sa, sb), tempfile.TemporaryDirectory() as d:
        cfg = ConfigService(sa, ConfigStore(d))
        cfg.start()
        for name in ("inspect_a", "inspect_b", "inspect_c"):
            _set(sa, config_keys.pose(name), {"q": list(INSPECT_Q)})
        _set(
            sa,
            config_keys.scene("datamatrix_part"),
            {
                "frame": "world",
                "pose": {"xyz": board, "quat": [0, 0, 0, 1]},
                "geometry": {"type": "mesh", "uri": "asset://wf/datamatrix_part.glb"},
            },
        )
        arm = SimArmDriver(sa, REALM, RID, load_arm(cell, RID), None)
        arm.start()
        cam = SimCameraDriver(sa, REALM, CID, load_cam(cell, CID))
        cam.start()
        det = DetectorPipeline(
            sb, REALM, "demo_detect",
            input_topic=f"{REALM}/camera2d/{CID}/image", fmt="DataMatrix",
        )
        det.start()
        svc = TaskRunnerService(sb, REALM, spec, rid=RID, cid=CID)
        svc.start()

        sb.declare_subscriber(
            task_keys.state(REALM, spec["name"]),
            lambda s: print("  state:", decode(s.payload)["configuration"],
                            "codes=", (decode(s.payload)["context"]["summary"] or {}).get("codes")),
        )
        sb.declare_subscriber(
            vision_keys.result(REALM, "demo_detect"),
            lambda s: print("  vision result:", [d["text"] for d in decode(s.payload)["detections"]]),
        )
        done = []
        sb.declare_subscriber(
            task_keys.result(REALM, spec["name"]),
            lambda s: done.append(decode(s.payload)),
        )

        time.sleep(0.5)
        print("starting demo_inspect ...")
        for r in sb.get(task_keys.cmd_start(REALM, spec["name"]), payload=encode({}), timeout=5.0):
            if r.ok is not None:
                print("start ack:", decode(r.ok.payload))

        for _ in range(600):
            if done:
                break
            time.sleep(0.1)
        print("\nFINAL RESULT:", done[0] if done else "<timeout>")

        svc.shutdown(); det.shutdown(); cam.shutdown(); arm.shutdown(); cfg.shutdown()


if __name__ == "__main__":
    main()
