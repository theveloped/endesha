"""Long-running sim cell for the browser click-through of the Tasks page.

Brings up config + arm_sim + camera2d_sim + the demo_detect DetectorPipeline +
the task_runner over ONE zenoh session connected to an external router (so the
host browser, via the remote-api bridge, shares the bus). Seeds the three
inspect poses + the DataMatrix board, then idles — the task_runner waits for a
`cmd/start` from the UI. Ctrl-C / SIGTERM tears everything down.

    # inside the wf-sim container, peered to a router the browser bridge shares:
    python scripts/live_sim_cell.py --connect tcp/host.docker.internal:7447
"""

from __future__ import annotations

import argparse
import signal
import tempfile
import textwrap
import threading
import time

import numpy as np
import zenoh

from wf.core.codec import decode, encode
from wf.core.frames import make_transform, quaternion_to_rotation_matrix
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.hal.arm_core import ArmCore
from wf.hal.arm_sim.backend import SimArmBackend
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

REALM, RID, CID = "cell", "r1", "cam0"
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", default=None, help="router endpoint, e.g. tcp/host.docker.internal:7447")
    ap.add_argument("--listen", default=None, help="listen endpoint instead of connecting")
    args = ap.parse_args()

    zcfg = zenoh.Config()
    zcfg.insert_json5("mode", '"peer"')
    zcfg.insert_json5("scouting/multicast/enabled", "false")
    if args.connect:
        zcfg.insert_json5("connect/endpoints", f'["{args.connect}"]')
    if args.listen:
        zcfg.insert_json5("listen/endpoints", f'["{args.listen}"]')
    session = zenoh.open(zcfg)

    spec = load_spec(FLOW)
    cell = _cell()
    board = _board_xyz(INSPECT_Q)

    cfg = ConfigService(session, ConfigStore(tempfile.mkdtemp()))
    cfg.start()
    for name in ("inspect_a", "inspect_b", "inspect_c"):
        _set(session, config_keys.pose(name), {"q": list(INSPECT_Q)})
    _set(
        session,
        config_keys.scene("datamatrix_part"),
        {
            "frame": "world",
            "pose": {"xyz": board, "quat": [0, 0, 0, 1]},
            "geometry": {"type": "mesh", "uri": "asset://wf/datamatrix_part.glb"},
        },
    )
    arm_params = load_arm(cell, RID)
    arm_params["urdf"] = arm_params.get("urdf") or BUNDLED_URDF
    arm = ArmCore(session, REALM, RID, arm_params, SimArmBackend(arm_params["home_q"]))
    arm.start()
    cam = SimCameraDriver(session, REALM, CID, load_cam(cell, CID))
    cam.start()
    det = DetectorPipeline(
        session, REALM, "demo_detect",
        input_topic=f"{REALM}/camera2d/{CID}/image", fmt="DataMatrix",
    )
    det.start()
    svc = TaskRunnerService(session, REALM, spec, rid=RID, cid=CID)
    svc.start()

    print(f"live sim cell up (board at {board}); task_runner '{spec['name']}' waiting for cmd/start")
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    try:
        while not stop.wait(1.0):
            pass
    finally:
        svc.shutdown(); det.shutdown(); cam.shutdown(); arm.shutdown(); cfg.shutdown()
        session.close()


if __name__ == "__main__":
    main()
