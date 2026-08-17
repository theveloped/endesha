"""The ``sim_tags`` provider process: ``python -m wf.hal.sim_tags --cell <realized>
--resource plc0 --realm cell``."""

from __future__ import annotations

import argparse
import os

from wf.core.session import open_session
from wf.hal.tags_core import TagsCore, load_tags_resource

from .backend import SimTagsBackend


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sim_tags", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to (realized) cell.yaml")
    parser.add_argument("--resource", default="plc0", help="resource id (default plc0)")
    parser.add_argument("--realm", default=os.environ.get("WF_REALM", "cell"))
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    params = load_tags_resource(args.cell, args.resource)
    session = open_session(args.zenoh_config)
    core = TagsCore(session, args.realm, args.resource, params, SimTagsBackend(params))
    try:
        core.start()
        core.run_forever()
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
