"""The `genicam_driver` process (design §5.5, camera2d contract).

Wires :class:`GenicamBackend` (the Harvester/GenTL camera seam) into the shared
:class:`~wf.hal.camera2d_core.Camera2dCore`, which serves the whole camera2d
contract. Deliberate divergence from the aubo driver's crash-only startup: a
missing or powered-off camera must NOT kill the cell stack, so the backend's
connect runs in a retry loop and failures surface in ``CameraStatus.error``.

No default continuous stream: the camera idles; full-res frames are fetched via
``cmd/grab`` (SingleFrame), a parameterized stream is switched on/off via
``cmd/stream_start``/``cmd/stream_stop`` (Continuous). Grab is REJECTED while
streaming. Every frame — stream or grab — goes out on the one ``image`` topic
(payload = bytes, attachment = CBOR FrameHeader, one shared ``seq`` counter).
"""

from __future__ import annotations

import argparse
import os

from wf.core.session import declare_alive, open_session
from wf.hal.camera2d_core import Camera2dCore

from .backend import GenicamBackend
from .config import load_resource


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="genicam_driver", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument("--resource", default="cam0", help="resource id (default cam0)")
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    params = load_resource(args.cell, args.resource)
    backend = GenicamBackend(params)

    session = open_session(args.zenoh_config)
    token = declare_alive(session, args.realm, "camera2d", args.resource)
    core = Camera2dCore(session, args.realm, args.resource, params, backend)
    try:
        core.start()
        core.run_forever()
    finally:
        del token
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
