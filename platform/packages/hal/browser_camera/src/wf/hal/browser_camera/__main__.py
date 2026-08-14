"""Run the browser-produced camera2d provider."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import yaml

from wf.core.session import declare_alive, open_session
from wf.hal.camera2d_core import Camera2dCore

from .backend import BrowserCameraBackend


def _load_params(cell_path: str, resource_id: str) -> dict:
    cell = yaml.safe_load(Path(cell_path).read_text(encoding="utf-8")) or {}
    params = dict(cell["resources"][resource_id].get("params") or {})
    params.setdefault("mount_arm", "r1")
    params.setdefault("mount_xyz", [0.0, 0.0, 0.05])
    params.setdefault("mount_rpy_deg", [0.0, 0.0, 0.0])
    params.setdefault(
        "stream_defaults",
        {"rate_hz": 15.0, "scale": 0.25, "roi": None, "encoding": "jpeg", "quality": 75},
    )
    params.setdefault(
        "grab_defaults",
        {"scale": 1.0, "roi": None, "encoding": "jpeg", "quality": 90},
    )
    return params


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--resource", default="cam0")
    parser.add_argument("--realm", default=os.environ.get("WF_REALM", "cell"))
    parser.add_argument("--zenoh-config", default=None)
    args = parser.parse_args(argv)

    params = _load_params(args.cell, args.resource)
    session = open_session(args.zenoh_config)
    token = declare_alive(session, args.realm, "camera2d", args.resource)
    backend = BrowserCameraBackend(session, args.realm, args.resource, params)
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
