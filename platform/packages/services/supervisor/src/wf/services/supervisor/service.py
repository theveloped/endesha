"""The supervisor service: cell bring-up + sole flow interpreter (design §8, §68).

From one cell file the supervisor brings up every always-on service the cell
needs (one HAL per resource + a node-local always-on vision runtime per distinct
detection pipeline), scans a flows directory, validates each flow spec, and
publishes a catalog of selectable flows with their RESOLVED role bindings.

The supervisor is the ONLY interpreter of flows: it owns the inventory and
resolves each flow's contract-typed roles to concrete resources. On
``flows/cmd/start`` it resolves roles -> ``--rid``/``--cid`` and spawns the
flow's ``task_runner`` (bringing it ONLINE); the operator runs it from the
Tasks page via the unchanged ``task/{flow}/cmd/start``. The flow's vision
detection is the always-on vision runtime, toggled by the running flow via the
existing ``vision/{pipeline}/cmd/enable`` — NOT a per-flow process.

Single-node this slice: the supervisor spawns all resources locally and is its
own master. The cell.yaml ``node:``/``master_node`` fields + the reserved
per-node key builders lay in the distributed seams (config-only later).

Run: ``python -m wf.services.supervisor --realm sim --cell cell.sim.yaml``.
"""

from __future__ import annotations

import argparse
import os
import signal
import tempfile
import threading
from pathlib import Path

import yaml
import zenoh

from wf.contracts.supervisor import keys as sup_keys
from wf.core.codec import encode
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import now_ns
from wf.services.task_runner.spec import load_spec

from .cell import load_cell, load_runtime, realize_cell, resolve_roles
from .procs import LAUNCH_EXTERNAL, ProcManager, provider_module

_log = get_logger("wf.services.supervisor.service")

_REAP_PERIOD_S = 1.0


class SupervisorService:
    def __init__(
        self,
        session: zenoh.Session,
        realm: str,
        cell: dict,
        *,
        cell_path: str,
        flows_dir: str,
        config_dir: str = "deploy/config",
        with_config: bool = False,
        zenoh_config: str | None = None,
        node: str = "main",
    ) -> None:
        self.session = session
        self.realm = realm
        self.cell = cell
        self.cell_path = str(Path(cell_path).resolve())
        self.flows_dir = Path(flows_dir)
        self.config_dir = config_dir
        self.with_config = with_config
        self.zenoh_config = zenoh_config
        self.node = node

        self._procs = ProcManager()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._reaper: threading.Thread | None = None
        self._alive_token = None
        self._started_at = now_ns()

        # Scan the flows directory: a valid spec lands in _catalog; a malformed
        # file lands in _errors under its file stem (reported, never a crash).
        self._catalog: dict[str, dict] = {}
        self._flow_files: dict[str, str] = {}
        self._errors: dict[str, str] = {}
        for path in sorted(self.flows_dir.glob("*.yaml")):
            stem = path.stem
            try:
                spec = load_spec(path)
            except Exception as exc:  # noqa: BLE001
                self._errors[stem] = str(exc)
                _log.warning("flow %s invalid: %s", stem, exc)
                continue
            self._catalog[spec["name"]] = spec
            self._flow_files[spec["name"]] = str(path.resolve())

        self._catalog_pub = session.declare_publisher(
            sup_keys.flows_catalog(realm),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._descriptor_pub = session.declare_publisher(
            sup_keys.supervisor_descriptor(realm, node),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._status_pubs: dict[str, zenoh.Publisher] = {}
        self._queryables: list = []

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._spawn_always_on()
        self._queryables = [
            self.session.declare_queryable(
                sup_keys.flows_cmd_start(self.realm), self._on_cmd_start
            ),
            self.session.declare_queryable(
                sup_keys.flows_cmd_stop(self.realm), self._on_cmd_stop
            ),
            self.session.declare_queryable(
                sup_keys.flows_catalog(self.realm), self._on_catalog_query
            ),
            self.session.declare_queryable(
                sup_keys.supervisor_descriptor(self.realm, self.node),
                self._on_descriptor_query,
            ),
        ]
        self._alive_token = declare_alive(
            self.session, self.realm, "supervisor", self.node
        )
        self._publish_catalog()
        self._publish_descriptor()
        self._start_reaper()
        _log.info(
            "supervisor up: realm=%s node=%s flows=%s errors=%s",
            self.realm,
            self.node,
            sorted(self._catalog),
            sorted(self._errors),
        )

    def run_forever(self) -> None:
        signal.signal(signal.SIGTERM, lambda *_: self._stop_event.set())
        signal.signal(signal.SIGINT, lambda *_: self._stop_event.set())
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
        for q in self._queryables:
            q.undeclare()
        self._queryables = []
        if self._alive_token is not None:
            del self._alive_token
            self._alive_token = None
        _log.info("supervisor stopped")

    # ── always-on bring-up ───────────────────────────────────────────────

    def _spawn_always_on(self) -> None:
        cfg = self.zenoh_config
        if self.with_config:
            argv = ["wf.services.config", "--dir", self.config_dir]
            if cfg:
                argv += ["--zenoh-config", cfg]
            self._procs.spawn("config", argv)

        # One provider per resource (single node -> all of them). An
        # external-launched provider (e.g. the headless-browser camera2d that
        # renders the twin scene and serves the contract over the bridge) is
        # served outside the supervisor's control; the supervisor still carries
        # it in the inventory (role resolution, vision binding) but spawns no
        # Python child for it.
        for rid, res in self.cell["resources"].items():
            if res["launch"] == LAUNCH_EXTERNAL:
                _log.info(
                    "resource %s served externally (kind=%s); not spawning",
                    rid,
                    res["kind"],
                )
                continue
            module = provider_module(res["contract"], res["kind"])
            argv = [
                module,
                "--cell",
                self.cell_path,
                "--resource",
                rid,
                "--realm",
                self.realm,
            ]
            if cfg:
                argv += ["--zenoh-config", cfg]
            self._procs.spawn(f"hal:{rid}", argv)

        # Always-on vision runtime: one process per distinct (pipeline, format)
        # found across the catalog, bound to the camera resource the flows
        # using it resolve to. The flow's task_runner toggles it via cmd/enable.
        for pipeline, fmt, cid in self._vision_runtimes():
            argv = [
                "wf.services.vision",
                "--realm",
                self.realm,
                "--pipeline",
                pipeline,
                "--input",
                f"camera2d/{cid}",
                "--op",
                "detect",
                "--detect-format",
                fmt,
            ]
            if cfg:
                argv += ["--zenoh-config", cfg]
            self._procs.spawn(f"vision:{pipeline}", argv)

    def _vision_runtimes(self) -> list[tuple[str, str, str]]:
        """Distinct ``(pipeline, format, cid)`` triples to spawn as always-on
        detectors. The camera is the one the flows using that pipeline resolve
        to (single-camera cell -> the one camera)."""
        seen: dict[str, tuple[str, str, str]] = {}
        for name, spec in self._catalog.items():
            pipeline = spec["vision"]["pipeline"]
            fmt = spec["vision"]["format"]
            try:
                roles = resolve_roles(self.cell, spec, name)
            except KeyError:
                continue
            cid = roles.get("cam")
            if cid is None:
                continue
            seen.setdefault(pipeline, (pipeline, fmt, cid))
        return list(seen.values())

    # ── flow orchestration ───────────────────────────────────────────────

    def _on_cmd_start(self, query: zenoh.Query) -> None:
        self._reply_dict(query, self._start_flow_reply(self._req_flow(query)))

    def _on_cmd_stop(self, query: zenoh.Query) -> None:
        self._reply_dict(query, self._stop_flow_reply(self._req_flow(query)))

    def _start_flow_reply(self, name: str | None) -> dict:
        if not name:
            return {"ok": False, "error": "unknown_flow:"}
        if name not in self._catalog:
            if name in self._errors:
                return {"ok": False, "error": self._errors[name]}
            return {"ok": False, "error": f"unknown_flow:{name}"}
        with self._lock:
            if self._procs.alive(f"task:{name}"):
                return {"ok": False, "error": "already_online"}
            spec = self._catalog[name]
            try:
                roles = resolve_roles(self.cell, spec, name)
            except KeyError as exc:
                return {"ok": False, "error": str(exc)}
            try:
                rid = roles["arm"]
                cid = roles["cam"]
            except KeyError as exc:
                return {"ok": False, "error": f"unresolved_role:{exc.args[0]}"}
            self._publish_status(name, "spawning", [])
            cfg = self.zenoh_config
            argv = [
                "wf.services.task_runner",
                "--realm",
                self.realm,
                "--flow",
                self._flow_files[name],
                "--rid",
                rid,
                "--cid",
                cid,
            ]
            if cfg:
                argv += ["--zenoh-config", cfg]
            try:
                self._procs.spawn(f"task:{name}", argv)
            except RuntimeError as exc:
                self._publish_status(name, "stopped", [])
                return {"ok": False, "error": str(exc)}
        self._publish_status(name, "running", [{"kind": "task_runner", "alive": True}])
        self._publish_catalog()
        self._publish_descriptor()
        return {
            "ok": True,
            "flow": name,
            "services": [{"kind": "task_runner", "instance_id": f"task:{name}"}],
        }

    def _stop_flow_reply(self, name: str | None) -> dict:
        if not name or name not in self._catalog:
            return {"ok": False, "error": "not_online"}
        with self._lock:
            stopped = self._procs.stop(f"task:{name}")
        if not stopped:
            return {"ok": False, "error": "not_online"}
        self._publish_status(name, "stopped", [])
        self._publish_catalog()
        self._publish_descriptor()
        return {"ok": True}

    # ── catalog / descriptor / status ────────────────────────────────────

    def _catalog_payload(self) -> dict:
        flows = []
        for name in sorted(set(self._catalog) | set(self._errors)):
            if name in self._errors:
                flows.append(
                    {
                        "name": name,
                        "roles": {},
                        "pipeline": None,
                        "format": None,
                        "online": False,
                        "error": self._errors[name],
                    }
                )
                continue
            spec = self._catalog[name]
            error = None
            roles: dict[str, dict] = {}
            try:
                resolved = resolve_roles(self.cell, spec, name)
                for role, decl in spec["roles"].items():
                    roles[role] = {
                        "contract": decl["contract"],
                        "resource_id": resolved[role],
                    }
            except KeyError as exc:
                error = str(exc)
            flows.append(
                {
                    "name": name,
                    "roles": roles,
                    "pipeline": spec["vision"]["pipeline"],
                    "format": spec["vision"]["format"],
                    "online": self._procs.alive(f"task:{name}"),
                    "error": error,
                }
            )
        return {"t": now_ns(), "realm": self.realm, "flows": flows}

    def _descriptor_payload(self) -> dict:
        always_on = []
        for name in self._procs.names():
            if name.startswith("task:"):
                continue
            always_on.append({"kind": name, "instance_id": name, "alive": True})
        return {
            "t": now_ns(),
            "node": self.node,
            "is_master": True,
            "owns_resources": sorted(self.cell["resources"]),
            "always_on": always_on,
            "started_at": self._started_at,
        }

    def _publish_catalog(self) -> None:
        self._publish(self._catalog_pub, self._catalog_payload())

    def _publish_descriptor(self) -> None:
        self._publish(self._descriptor_pub, self._descriptor_payload())

    def _publish_status(self, flow: str, phase: str, services: list) -> None:
        pub = self._status_pubs.get(flow)
        if pub is None:
            pub = self.session.declare_publisher(
                sup_keys.flow_status(self.realm, flow),
                congestion_control=zenoh.CongestionControl.DROP,
            )
            self._status_pubs[flow] = pub
        self._publish(
            pub,
            {"t": now_ns(), "flow": flow, "phase": phase, "services": services},
        )

    def _on_catalog_query(self, query: zenoh.Query) -> None:
        self._reply_dict(query, self._catalog_payload())

    def _on_descriptor_query(self, query: zenoh.Query) -> None:
        self._reply_dict(query, self._descriptor_payload())

    # ── reaper ───────────────────────────────────────────────────────────

    def _start_reaper(self) -> None:
        self._reaper = threading.Thread(
            target=self._reap_loop, name="supervisor-reaper", daemon=True
        )
        self._reaper.start()

    def _reap_loop(self) -> None:
        while not self._stop_event.wait(_REAP_PERIOD_S):
            dead = self._procs.reap_dead()
            if dead:
                self._publish_catalog()
                self._publish_descriptor()

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _req_flow(query: zenoh.Query) -> str | None:
        from wf.core.codec import decode

        payload = query.payload
        if payload is None:
            return None
        try:
            req = decode(payload)
        except Exception:  # noqa: BLE001
            return None
        if isinstance(req, dict):
            flow = req.get("flow")
            return flow if isinstance(flow, str) else None
        return None

    @staticmethod
    def _reply_dict(query: zenoh.Query, value: dict) -> None:
        query.reply(str(query.key_expr), encode(value))

    def _publish(self, pub: zenoh.Publisher, value: dict) -> None:
        try:
            pub.put(encode(value))
        except Exception:  # noqa: BLE001
            _log.debug("publish failed", exc_info=True)


def _write_realized_cell(realized: dict) -> str:
    """Dump the realized inventory to a temp cell file for child HAL spawning.

    The realized resources are the legacy ``{contract, hal, node, params}``
    shape, so each HAL's existing ``load_resource(cell, rid)`` reads its merged
    params with no change. Caller unlinks the file on shutdown.
    """
    fd, path = tempfile.mkstemp(prefix="wf-realized-cell-", suffix=".yaml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        yaml.safe_dump(realized, f, sort_keys=False)
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="wf.services.supervisor", description=__doc__)
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument(
        "--runtime",
        default=None,
        help="path to a runtime overlay (active_sources) selecting source modes",
    )
    parser.add_argument(
        "--flows-dir",
        default="packages/services/task_runner/flows",
        help="directory of flow YAML specs",
    )
    parser.add_argument(
        "--config-dir",
        default="deploy/config",
        help="config store dir (only used with --with-config)",
    )
    parser.add_argument(
        "--with-config",
        action="store_true",
        help="spawn the config service as an always-on child",
    )
    parser.add_argument("--node", default="main", help="node id (default main)")
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    # cell = design-time truth; the runtime overlay selects a source mode per
    # logical device. realize_cell collapses the two into the concrete inventory
    # (one provider per resource). Children are spawned against a realized cell
    # file so their existing per-resource loaders read merged params unchanged.
    cell = load_cell(args.cell)
    active = load_runtime(args.runtime)["active_sources"] if args.runtime else {}
    realized = realize_cell(cell, active)
    realized_path = _write_realized_cell(realized)

    session = open_session(args.zenoh_config)
    service = SupervisorService(
        session,
        args.realm,
        realized,
        cell_path=realized_path,
        flows_dir=args.flows_dir,
        config_dir=args.config_dir,
        with_config=args.with_config,
        zenoh_config=args.zenoh_config,
        node=args.node,
    )
    try:
        service.start()
        service.run_forever()
    finally:
        session.close()
        try:
            os.unlink(realized_path)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
