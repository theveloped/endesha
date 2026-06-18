"""The `aubo_driver` process (design §5.1): real Aubo i10 via the shared core.

Wires :class:`AuboBackend` (the Aubo SDK / RTDE seam) into
:class:`~wf.hal.arm_core.ArmCore`, which serves the whole arm contract. The
backend holds two RPC connections (the SDK is not shared across concurrent
threads): ``sdk_cmd`` owned by the command worker, ``sdk_state`` by the state
poller + out-of-band ``cmd/stop``.

Crash-only: no state to restore; on restart everything is re-declared
(liveliness re-asserts).
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os

from wf.core.session import declare_alive, open_session
from wf.hal.arm_core import ArmCore

from . import BUNDLED_URDF
from .backend import AuboBackend
from .config import load_resource


def _driver_version() -> str:
    try:
        return importlib.metadata.version("wf-hal-aubo-i10")
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="aubo_driver", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument("--resource", default="r1", help="resource id (default r1)")
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    params = load_resource(args.cell, args.resource)
    params["urdf"] = params.get("urdf") or BUNDLED_URDF
    backend = AuboBackend(params)

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
