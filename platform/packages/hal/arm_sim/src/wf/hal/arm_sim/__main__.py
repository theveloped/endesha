"""The `arm_sim` driver process (roadmap §10 item 6).

Simulates THIS cell's arm (Aubo i10) by wiring :class:`SimArmBackend` into the
shared :class:`~wf.hal.arm_core.ArmCore`. Reuses the aubo package's bundled URDF
(FK) via a normal dependency. Crash-only: no state to restore; on restart
everything is re-declared (liveliness re-asserts).

Mirror mode (``--mirror <realm>``): the backend subscribes that realm's
``arm/{rid}/state/joints``, shadows ``q``/``qd``, and republishes under this
namespace with fresh ``t = now_ns()`` — replayed payloads carry old data-time;
reusing it would trip the UI's 3 s staleness rule. While mirroring,
``execute_path`` goals are rejected with reason ``"mirroring"``; ``set_do``
still works (sim-local DO bits).
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os

from wf.core.session import declare_alive, open_session
from wf.hal.arm_core import ArmCore
from wf.hal.aubo_i10 import BUNDLED_URDF

from .backend import SimArmBackend
from .config import load_resource


def _driver_version() -> str:
    try:
        return importlib.metadata.version("wf-hal-arm-sim")
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="arm_sim", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument("--resource", default="r1", help="resource id (default r1)")
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    parser.add_argument(
        "--mirror",
        default=None,
        metavar="REALM",
        help="shadow this realm's state/joints (e.g. 'live', 'replay/demo'); "
        "execute_path goals are rejected while mirroring",
    )
    args = parser.parse_args(argv)

    params = load_resource(args.cell, args.resource)
    params["urdf"] = params.get("urdf") or BUNDLED_URDF
    backend = SimArmBackend(params["home_q"], mirror_realm=args.mirror)

    session = open_session(args.zenoh_config)
    token = declare_alive(session, args.realm, "arm", args.resource)
    core = ArmCore(
        session,
        args.realm,
        args.resource,
        params,
        backend,
        driver_version=_driver_version(),
    )
    try:
        core.start()
        core.run_forever()
    finally:
        del token
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
