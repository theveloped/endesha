"""The ``ecoclean`` washer provider process: ``python -m wf.hal.ecoclean --cell
<realized> --resource washer0 --realm cell``. The realized resource's ``kind``
picks the backend: ``ecoclean`` (live, OPC-UA) or ``ecoclean_sim``."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import yaml

from wf.core.session import open_session

from .core import WasherCore
from .live import make_live_backend
from .sim import EcocleanSimBackend

KINDS = {"ecoclean": make_live_backend, "ecoclean_sim": EcocleanSimBackend}


def load_resource(cell_yaml_path: str, resource_id: str) -> tuple[str, dict]:
    path = Path(cell_yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"cell file not found: {cell_yaml_path}")
    cell = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    resources = cell.get("resources") or {}
    if resource_id not in resources:
        raise KeyError(f"resource {resource_id!r} not found in {cell_yaml_path}")
    res = resources[resource_id]
    return str(res.get("kind", "ecoclean_sim")), dict(res.get("params") or {})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ecoclean", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to (realized) cell.yaml")
    parser.add_argument("--resource", default="washer0", help="resource id (default washer0)")
    parser.add_argument("--realm", default=os.environ.get("WF_REALM", "cell"))
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    parser.add_argument("--kind", default=None, help="override the backend kind (ecoclean | ecoclean_sim)")
    args = parser.parse_args(argv)

    kind, params = load_resource(args.cell, args.resource)
    kind = args.kind or kind
    if kind not in KINDS:
        raise SystemExit(f"unknown ecoclean kind {kind!r}; expected one of {sorted(KINDS)}")
    session = open_session(args.zenoh_config)
    core = WasherCore(session, args.realm, args.resource, params, KINDS[kind](params))
    try:
        core.start()
        core.run_forever()
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
