"""Cell supervisor: provider bring-up and runtime device source management.

The supervisor realizes the canonical cell plus a runtime overlay, starts one
provider per active resource, publishes the device inventory, and cold-switches
providers between live, simulated, replay, and off sources. It also hosts the
cell's single control-lease authority (``wf.contracts.control``). It
deliberately contains no task, flow, graph, or vision-pipeline orchestration.

Run: ``python -m wf.services.supervisor --cell deploy/cell.yaml
--runtime deploy/runtime/sim.yaml``.
"""

from __future__ import annotations

import argparse
import os
import signal
import tempfile
import threading

import yaml
import zenoh

from wf.contracts.control.authority import ControlAuthority
from wf.contracts.supervisor import keys as sup_keys
from wf.core.audit import QueryAudit
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import now_ns

from .cell import devices_inventory, load_cell, load_runtime, realize_cell
from .procs import LAUNCH_EXTERNAL, ProcManager, provider_module
from .telemetry import EventLog, LogHub

_log = get_logger("wf.services.supervisor.service")
_REAP_PERIOD_S = 1.0


class SupervisorService:
    def __init__(
        self,
        session: zenoh.Session,
        realm: str,
        cell: dict,
        active_sources: dict,
        *,
        config_dir: str = "deploy/config",
        with_config: bool = False,
        programs_dir: str | None = None,
        zenoh_config: str | None = None,
        node: str = "main",
    ) -> None:
        self.session = session
        self.realm = realm
        self.cell = cell
        self.active_sources = dict(active_sources)
        self.realized = realize_cell(cell, self.active_sources)
        self.cell_path = _write_realized_cell(self.realized)
        self.config_dir = config_dir
        self.with_config = with_config
        self.programs_dir = programs_dir
        self.zenoh_config = zenoh_config
        self.node = node

        self._logs = LogHub(session, realm, node)
        self._events = EventLog(session, realm, node)
        self._audit = QueryAudit(session, realm, "supervisor")
        self._procs = ProcManager(on_line=self._logs.line)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._reaper: threading.Thread | None = None
        self._alive_token = None
        self._started_at = now_ns()

        self._descriptor_pub = session.declare_publisher(
            sup_keys.supervisor_descriptor(realm, node),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._devices_pub = session.declare_publisher(
            sup_keys.supervisor_devices(realm, node),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._queryables: list = []
        self._control = ControlAuthority(
            session, realm, ttl_s=cell.get("control", {}).get("lease_ttl_s", 30.0)
        )

    def start(self) -> None:
        # Authority first: providers check the lease as soon as they come up.
        self._control.start()
        self._spawn_always_on()
        self._queryables = [
            self.session.declare_queryable(
                sup_keys.supervisor_descriptor(self.realm, self.node),
                self._on_descriptor_query,
            ),
            self.session.declare_queryable(
                sup_keys.supervisor_devices(self.realm, self.node),
                self._on_devices_query,
            ),
            self.session.declare_queryable(
                sup_keys.supervisor_cmd_set_source(self.realm, self.node),
                self._audit.wrap(self._on_set_source),
            ),
            self.session.declare_queryable(
                sup_keys.supervisor_log_glob(self.realm, self.node),
                self._logs.on_log_query,
            ),
            self.session.declare_queryable(
                sup_keys.supervisor_events(self.realm, self.node),
                self._events.on_events_query,
            ),
        ]
        self._alive_token = declare_alive(
            self.session, self.realm, "supervisor", self.node
        )
        self._publish_descriptor()
        self._publish_devices()
        self._start_reaper()
        self._events.emit("supervisor_started", cell=self.cell.get("name") or self.realm)
        _log.info("supervisor up: realm=%s node=%s", self.realm, self.node)

    def run_forever(self) -> None:
        signal.signal(signal.SIGTERM, lambda *_: self._stop_event.set())
        signal.signal(signal.SIGINT, lambda *_: self._stop_event.set())
        if hasattr(signal, "SIGBREAK"):  # Windows: the host API stops us with Ctrl-Break
            signal.signal(signal.SIGBREAK, lambda *_: self._stop_event.set())
        try:
            self._stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        if self._stop_event.is_set() and self._reaper is None:
            return
        self._stop_event.set()
        if self._reaper is not None:
            self._reaper.join(timeout=2.0)
            self._reaper = None
        self._procs.stop_all()
        for queryable in self._queryables:
            queryable.undeclare()
        self._queryables = []
        self._control.close()
        if self._alive_token is not None:
            del self._alive_token
            self._alive_token = None
        try:
            os.unlink(self.cell_path)
        except OSError:
            pass
        _log.info("supervisor stopped")

    def _spawn_always_on(self) -> None:
        if self.with_config:
            argv = ["wf.services.config", "--dir", self.config_dir, "--realm", self.realm]
            if self.zenoh_config:
                argv += ["--zenoh-config", self.zenoh_config]
            self._procs.spawn("config", argv)
            self._events.emit("service_started", "config")
        if self.programs_dir:
            argv = ["wf.services.program_runner", "--programs", self.programs_dir,
                    "--realm", self.realm, "--node", self.node]
            if self.zenoh_config:
                argv += ["--zenoh-config", self.zenoh_config]
            self._procs.spawn("program_runner", argv)
            self._events.emit("service_started", "program_runner")

        for resource_id in self.realized["resources"]:
            try:
                self._spawn_provider(resource_id)
            except RuntimeError as exc:
                self._events.emit("spawn_failed", f"hal:{resource_id}", error=str(exc))
                _log.error(
                    "provider %s failed to start: %s; left down",
                    resource_id,
                    exc,
                )

    def _spawn_provider(self, resource_id: str) -> None:
        """Spawn one realized provider; external and off sources are no-ops."""
        resource = self.realized["resources"].get(resource_id)
        if resource is None:
            return
        if resource["launch"] == LAUNCH_EXTERNAL:
            _log.info(
                "resource %s served externally (kind=%s); not spawning",
                resource_id,
                resource["kind"],
            )
            return
        module = provider_module(resource["contract"], resource["kind"])
        argv = [
            module,
            "--cell",
            self.cell_path,
            "--resource",
            resource_id,
            "--realm",
            self.realm,
        ]
        if self.zenoh_config:
            argv += ["--zenoh-config", self.zenoh_config]
        self._procs.spawn(f"hal:{resource_id}", argv)
        self._events.emit("service_started", f"hal:{resource_id}", provider=resource["kind"])

    def _descriptor_payload(self) -> dict:
        always_on = [
            {"kind": name, "instance_id": name, "alive": True}
            for name in self._procs.names()
        ]
        return {
            "t": now_ns(),
            "node": self.node,
            # Cell identity for multi-cell UIs: the realm is the id, ``name`` is
            # the display name (cell.yaml ``name:``, default the realm).
            "realm": self.realm,
            "cell_name": self.cell.get("name") or self.realm,
            "cell_type": self.cell.get("cell_type"),
            "is_master": True,
            "owns_resources": sorted(self.cell["resources"]),
            "always_on": always_on,
            "started_at": self._started_at,
        }

    def _publish_descriptor(self) -> None:
        self._publish(self._descriptor_pub, self._descriptor_payload())

    def _on_descriptor_query(self, query: zenoh.Query) -> None:
        self._reply_dict(query, self._descriptor_payload())

    def _devices_payload(self) -> dict:
        return {
            "t": now_ns(),
            "node": self.node,
            "devices": devices_inventory(self.cell, self.active_sources),
        }

    def _publish_devices(self) -> None:
        self._publish(self._devices_pub, self._devices_payload())

    def _on_devices_query(self, query: zenoh.Query) -> None:
        self._reply_dict(query, self._devices_payload())

    def _on_set_source(self, query: zenoh.Query) -> None:
        request: dict = {}
        if query.payload is not None:
            try:
                decoded = decode(query.payload)
                if isinstance(decoded, dict):
                    request = decoded
            except Exception:  # noqa: BLE001
                pass
        self._reply_dict(
            query,
            self._set_source_reply(request.get("device_id"), request.get("source")),
        )

    def _set_source_reply(self, device_id, source) -> dict:
        """Cold-switch a device and restart its selected provider."""
        if not isinstance(device_id, str) or device_id not in self.cell["resources"]:
            for host, res in self.cell["resources"].items():
                if device_id in (res.get("provides") or {}):
                    return {"ok": False, "error": f"provided_by:{host}"}
            return {"ok": False, "error": f"unknown_device:{device_id}"}
        sources = self.cell["resources"].get(device_id, {}).get("sources", {})
        if source != "off" and source not in sources:
            return {"ok": False, "error": f"no_source:{device_id}:{source}"}

        error = None
        with self._lock:
            if self._procs.stop(f"hal:{device_id}"):
                self._events.emit("service_stopped", f"hal:{device_id}")
            self.active_sources[device_id] = source
            self.realized = realize_cell(self.cell, self.active_sources)
            _dump_realized(self.realized, self.cell_path)
            try:
                self._spawn_provider(device_id)
            except RuntimeError as exc:
                error = str(exc)
                self._events.emit("spawn_failed", f"hal:{device_id}", error=error)

        self._events.emit("source_switched", f"hal:{device_id}", device_id=device_id, source=source, ok=error is None)
        self._publish_devices()
        self._publish_descriptor()
        if error:
            return {
                "ok": False,
                "error": error,
                "device_id": device_id,
                "source": source,
            }
        return {"ok": True, "device_id": device_id, "source": source}

    def _start_reaper(self) -> None:
        self._reaper = threading.Thread(
            target=self._reap_loop,
            name="supervisor-reaper",
            daemon=True,
        )
        self._reaper.start()

    def _reap_loop(self) -> None:
        while not self._stop_event.wait(_REAP_PERIOD_S):
            dead = self._procs.reap_dead()
            if dead:
                for name, rc in dead:
                    self._events.emit("service_exited", name, exit_code=rc)
                self._publish_descriptor()

    @staticmethod
    def _reply_dict(query: zenoh.Query, value: dict) -> None:
        query.reply(str(query.key_expr), encode(value))

    @staticmethod
    def _publish(pub: zenoh.Publisher, value: dict) -> None:
        try:
            pub.put(encode(value))
        except Exception:  # noqa: BLE001
            _log.debug("publish failed", exc_info=True)


def _dump_realized(realized: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as file:
        yaml.safe_dump(realized, file, sort_keys=False)


def _write_realized_cell(realized: dict) -> str:
    fd, path = tempfile.mkstemp(prefix="wf-realized-cell-", suffix=".yaml")
    os.close(fd)
    _dump_realized(realized, path)
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="wf.services.supervisor",
        description=__doc__,
    )
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument(
        "--runtime",
        default=None,
        help="runtime overlay selecting active device sources",
    )
    parser.add_argument(
        "--config-dir",
        default="deploy/config",
        help="config store directory (only used with --with-config)",
    )
    parser.add_argument(
        "--with-config",
        action="store_true",
        help="spawn the config service as an always-on child",
    )
    parser.add_argument(
        "--programs",
        default=None,
        metavar="DIR",
        help="spawn the program runner over this directory of program modules",
    )
    parser.add_argument(
        "--node",
        default="main",
        help="node id (default main)",
    )
    parser.add_argument(
        "--zenoh-config",
        default=None,
        help="zenoh config path",
    )
    args = parser.parse_args(argv)

    cell = load_cell(args.cell)
    active = load_runtime(args.runtime)["active_sources"] if args.runtime else {}

    session = open_session(args.zenoh_config)
    service = SupervisorService(
        session,
        args.realm,
        cell,
        active,
        config_dir=args.config_dir,
        with_config=args.with_config,
        programs_dir=args.programs,
        zenoh_config=args.zenoh_config,
        node=args.node,
    )
    try:
        service.start()
        service.run_forever()
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
