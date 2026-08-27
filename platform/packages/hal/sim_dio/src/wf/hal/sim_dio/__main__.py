"""The ``sim_dio`` provider process: ``python -m wf.hal.sim_dio --cell <realized>
--resource io0 --realm cell``."""

from __future__ import annotations

import argparse
import os

from wf.core.session import open_session
from wf.hal.dio_core import DioCore, load_dio_resource

from .backend import SimDioBackend


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sim_dio", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to (realized) cell.yaml")
    parser.add_argument("--resource", default="io0", help="resource id (default io0)")
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    params = load_dio_resource(args.cell, args.resource)
    session = open_session(args.zenoh_config)
    core = DioCore(session, args.realm, args.resource, params, SimDioBackend(params))
    try:
        core.start()
        core.run_forever()
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
