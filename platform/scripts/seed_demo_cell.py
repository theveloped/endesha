"""One-shot demo seeder for the sim cell (extracted from live_sim_cell.py).

Seeds the three inspect poses (all = INSPECT_Q) and the DataMatrix board scene
object at the FK-derived board position, then exits. Keeps the supervisor
demo-agnostic: a real cell uses taught poses, so the supervisor never seeds.

    # peered to the router the stack shares:
    python scripts/seed_demo_cell.py --connect tcp/zenoh-router:7447
"""

from __future__ import annotations

import argparse

import numpy as np
import zenoh

from wf.core.codec import decode, encode
from wf.core.frames import make_transform, quaternion_to_rotation_matrix
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.hal.arm_sim.sim import SimArm
from wf.services.config import keys as config_keys
from wf.world_model.fk import UrdfFk

REALM, RID, CID = "sim", "r1", "cam0"
INSPECT_Q = [0.0, 0.6, 1.6727272727272728, -0.6981, 1.6384615384615384, 0.0]


def _board_xyz(q):
    """Where the eye-in-hand camera optical axis hits z=0 for joint config q."""
    arm = SimArm(UrdfFk(BUNDLED_URDF), q)
    fl = arm.flange_pose(RID)
    T_wo = make_transform(
        quaternion_to_rotation_matrix(fl.quat), fl.xyz
    ) @ make_transform(np.eye(3), [0.0, 0.0, 0.05])
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
    raise AssertionError(f"no reply from config set for {key}")


def seed(session) -> None:
    board = _board_xyz(INSPECT_Q)
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
    print(f"seeded inspect poses + datamatrix_part board at {board}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="seed_demo_cell", description=__doc__)
    ap.add_argument(
        "--connect", default=None, help="router endpoint, e.g. tcp/zenoh-router:7447"
    )
    ap.add_argument("--listen", default=None, help="listen endpoint instead")
    args = ap.parse_args(argv)

    zcfg = zenoh.Config()
    zcfg.insert_json5("mode", '"peer"')
    zcfg.insert_json5("scouting/multicast/enabled", "false")
    if args.connect:
        zcfg.insert_json5("connect/endpoints", f'["{args.connect}"]')
    if args.listen:
        zcfg.insert_json5("listen/endpoints", f'["{args.listen}"]')
    session = zenoh.open(zcfg)
    try:
        seed(session)
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
