"""``python -m wf.services.host_api --deploy deploy --port 8080 --with-config
[--activate <cell> [--runtime <overlay>]] [--zenoh-config ...]``

Starts the config store (``--with-config``), restores the last active cell
(``<deploy>/host.yaml``) or activates ``--activate``, then serves the API.
Ctrl-C stops the supervisor tree and the config service too.
"""

from __future__ import annotations

import argparse
import os

import uvicorn

from wf.core.log import get_logger

from .app import create_app
from .manager import SupervisorManager

_log = get_logger("wf.services.host_api")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="host_api", description=__doc__)
    parser.add_argument("--deploy", default="deploy", help="deploy root holding cell.yaml / <cell>/cell.yaml")
    parser.add_argument("--host", default=os.environ.get("WF_HOST_API_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("WF_HOST_API_PORT", "8080")))
    parser.add_argument("--realm", default=os.environ.get("WF_REALM", "cell"))
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path handed to the supervisor/config")
    parser.add_argument("--with-config", action="store_true", help="also run the config store service")
    parser.add_argument("--config-dir", default=None, help="config store dir (default <deploy>/config)")
    parser.add_argument("--activate", default=os.environ.get("WF_CELL"), help="cell id to activate at start (default: last active)")
    parser.add_argument("--runtime", default=os.environ.get("WF_RUNTIME"), help="overlay id for --activate")
    parser.add_argument("--no-restore", action="store_true", help="do not restore the last active cell")
    args = parser.parse_args(argv)

    manager = SupervisorManager(
        args.deploy, realm=args.realm, zenoh_config=args.zenoh_config,
        with_config=args.with_config, config_dir=args.config_dir,
    )
    manager.start_config()
    choice = None
    if args.activate:
        choice = {"cell": args.activate, "runtime": args.runtime}
    elif not args.no_restore:
        choice = manager.restore()
    if choice is None and manager.cell("default") is not None:
        choice = {"cell": "default", "runtime": None}  # first boot: the default cell, its default overlay
    if choice is not None:
        try:
            manager.activate(choice["cell"], choice.get("runtime"))
        except (KeyError, ValueError) as exc:
            _log.error("could not activate %s: %s", choice, exc)
    else:
        _log.info("no cell activated; pick one via POST /cells/<id>/activate")

    app = create_app(manager)
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    finally:
        manager.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
