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

Run: ``python -m wf.services.supervisor --cell deploy/cell.yaml
--runtime deploy/runtime/sim.yaml``.
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
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import now_ns
from wf.services.task_runner.graph import Graph, is_graph_doc, validate_graph
from wf.services.task_runner.spec import load_flow

from .cell import (
    devices_inventory,
    load_cell,
    load_runtime,
    realize_cell,
    resolve_roles,
)
from .procs import LAUNCH_EXTERNAL, ProcManager, provider_module

_log = get_logger("wf.services.supervisor.service")

_REAP_PERIOD_S = 1.0


def _describe_flow(obj: dict | Graph) -> dict:
    """Normalize a loaded flow (legacy spec dict OR node :class:`Graph`) into a
    uniform catalog descriptor the supervisor consumes regardless of format::

        {"name", "roles", "kind": "spec"|"graph",
         "vision_pipelines": [(pipeline, format), ...]}

    ``roles`` keeps the ``{role: {"contract": ...}}`` shape ``resolve_roles``
    expects. A graph's vision pipelines come from its ``vision.start`` nodes (an
    arm-only graph has none)."""
    if isinstance(obj, Graph):
        pipelines: list[tuple[str, str]] = []
        for node in obj.nodes.values():
            if node.type == "vision.start":
                pipeline = node.params.get("pipeline") or f"{obj.name}_detect"
                fmt = node.params.get("format")
                fmt = fmt if isinstance(fmt, str) else "Any"
                if (pipeline, fmt) not in pipelines:
                    pipelines.append((pipeline, fmt))
        return {
            "name": obj.name,
            "roles": dict(obj.roles),
            "kind": "graph",
            "vision_pipelines": pipelines,
        }
    return {
        "name": obj["name"],
        "roles": dict(obj["roles"]),
        "kind": "spec",
        "vision_pipelines": [(obj["vision"]["pipeline"], obj["vision"]["format"])],
    }


class SupervisorService:
    def __init__(
        self,
        session: zenoh.Session,
        realm: str,
        cell: dict,
        active_sources: dict,
        *,
        flows_dir: str,
        graphs_dir: str | None = None,
        config_dir: str = "deploy/config",
        with_config: bool = False,
        zenoh_config: str | None = None,
        node: str = "main",
    ) -> None:
        self.session = session
        self.realm = realm
        # The full (multi-source) cell + a mutable active-source map: the service
        # realizes the concrete inventory itself and rewrites the child-params
        # file on a runtime source switch.
        self.cell = cell
        self.active_sources = dict(active_sources)
        self.realized = realize_cell(cell, self.active_sources)
        self.cell_path = _write_realized_cell(self.realized)
        self.flows_dir = Path(flows_dir)
        self.graphs_dir = Path(graphs_dir) if graphs_dir else None
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

        # Scan the flow directories: a valid flow (legacy spec OR node graph)
        # lands in _catalog as a normalized descriptor; a malformed file lands in
        # _errors under its file stem (reported, never a crash).
        self._catalog: dict[str, dict] = {}
        self._flow_files: dict[str, str] = {}
        self._errors: dict[str, str] = {}
        scan_dirs = [self.flows_dir]
        if self.graphs_dir is not None:
            scan_dirs.append(self.graphs_dir)
        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            for path in sorted(scan_dir.glob("*.yaml")):
                stem = path.stem
                try:
                    desc = _describe_flow(load_flow(path))
                except Exception as exc:  # noqa: BLE001
                    self._errors[stem] = str(exc)
                    _log.warning("flow %s invalid: %s", stem, exc)
                    continue
                self._catalog[desc["name"]] = desc
                self._flow_files[desc["name"]] = str(path.resolve())

        self._catalog_pub = session.declare_publisher(
            sup_keys.flows_catalog(realm),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._descriptor_pub = session.declare_publisher(
            sup_keys.supervisor_descriptor(realm, node),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._devices_pub = session.declare_publisher(
            sup_keys.supervisor_devices(realm, node),
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
                sup_keys.flows_doc(self.realm), self._on_doc_query
            ),
            self.session.declare_queryable(
                sup_keys.flows_cmd_save(self.realm), self._on_cmd_save
            ),
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
                self._on_set_source,
            ),
        ]
        self._alive_token = declare_alive(
            self.session, self.realm, "supervisor", self.node
        )
        self._publish_catalog()
        self._publish_descriptor()
        self._publish_devices()
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
        try:
            os.unlink(self.cell_path)
        except OSError:
            pass
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
        for rid in self.realized["resources"]:
            try:
                self._spawn_provider(rid)
            except RuntimeError as exc:
                # A provider that can't start (e.g. a live device with no
                # hardware attached) must NOT kill the cell — log it, leave the
                # device down; it can be switched to sim/replay at runtime.
                _log.error("provider %s failed to start: %s; left down", rid, exc)

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

    def _spawn_provider(self, rid: str) -> None:
        """Spawn the realized provider child for ``rid`` (no-op for an
        off / external-launched source). Raises RuntimeError on spawn failure."""
        res = self.realized["resources"].get(rid)
        if res is None:
            return  # selected off -> no provider
        if res["launch"] == LAUNCH_EXTERNAL:
            _log.info(
                "resource %s served externally (kind=%s); not spawning",
                rid,
                res["kind"],
            )
            return
        module = provider_module(res["contract"], res["kind"])
        argv = [module, "--cell", self.cell_path, "--resource", rid, "--realm", self.realm]
        if self.zenoh_config:
            argv += ["--zenoh-config", self.zenoh_config]
        self._procs.spawn(f"hal:{rid}", argv)

    def _vision_runtimes(self) -> list[tuple[str, str, str]]:
        """Distinct ``(pipeline, format, cid)`` triples to spawn as always-on
        detectors. The camera is the one the flows using that pipeline resolve
        to (single-camera cell -> the one camera)."""
        seen: dict[str, tuple[str, str, str]] = {}
        for name, desc in self._catalog.items():
            try:
                roles = resolve_roles(self.cell, desc, name)
            except KeyError:
                continue
            cid = roles.get("cam")
            if cid is None:
                continue
            for pipeline, fmt in desc["vision_pipelines"]:
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
            desc = self._catalog[name]
            try:
                roles = resolve_roles(self.cell, desc, name)
            except KeyError as exc:
                return {"ok": False, "error": str(exc)}
            rid = roles.get("arm")
            if rid is None:
                return {"ok": False, "error": "unresolved_role:arm"}
            # A flow needn't use a camera (e.g. an arm-only pick graph); the
            # task_runner accepts a default cid it simply won't drive.
            cid = roles.get("cam", "cam0")
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

    # ── graph doc read / save (node editor) ──────────────────────────────

    def _on_doc_query(self, query: zenoh.Query) -> None:
        self._reply_dict(query, self._doc_reply(self._req_field(query, "name")))

    def _doc_reply(self, name: str | None) -> dict:
        if not name or name not in self._flow_files:
            return {"ok": False, "error": f"unknown_flow:{name or ''}"}
        try:
            raw = yaml.safe_load(
                Path(self._flow_files[name]).read_text(encoding="utf-8")
            )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "name": name,
            "kind": self._catalog[name]["kind"],
            "doc": raw,
        }

    def _on_cmd_save(self, query: zenoh.Query) -> None:
        req = self._req_payload(query)
        self._reply_dict(query, self._save_reply(req.get("name"), req.get("doc")))

    def _save_reply(self, name, doc) -> dict:
        """Validate + persist an authored graph doc as a repo file, then refresh
        the catalog. Only node graphs are editor-authored; legacy specs are not
        overwritable here."""
        if not isinstance(name, str) or not name:
            return {"ok": False, "error": "bad_save:name"}
        if not isinstance(doc, dict):
            return {"ok": False, "error": "bad_save:doc must be a mapping"}
        if self.graphs_dir is None:
            return {"ok": False, "error": "bad_save:no_graphs_dir"}
        doc = {**doc, "name": name}
        if not is_graph_doc(doc):
            return {"ok": False, "error": "bad_save:not_a_graph"}
        existing = self._flow_files.get(name)
        if existing is not None and self.graphs_dir not in Path(existing).parents:
            return {"ok": False, "error": f"exists_as_spec:{name}"}
        try:
            graph = validate_graph(doc)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        try:
            self.graphs_dir.mkdir(parents=True, exist_ok=True)
            path = self.graphs_dir / f"{name}.yaml"
            path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        with self._lock:
            self._catalog[name] = _describe_flow(graph)
            self._flow_files[name] = str(path.resolve())
            self._errors.pop(name, None)
        self._publish_catalog()
        return {"ok": True, "name": name}

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
            desc = self._catalog[name]
            error = None
            roles: dict[str, dict] = {}
            try:
                resolved = resolve_roles(self.cell, desc, name)
                for role, decl in desc["roles"].items():
                    roles[role] = {
                        "contract": decl["contract"],
                        "resource_id": resolved[role],
                    }
            except KeyError as exc:
                error = str(exc)
            pipelines = desc["vision_pipelines"]
            flows.append(
                {
                    "name": name,
                    "roles": roles,
                    "kind": desc["kind"],
                    "pipeline": pipelines[0][0] if pipelines else None,
                    "format": pipelines[0][1] if pipelines else None,
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

    # ── devices inventory + runtime source switching ─────────────────────

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
        req: dict = {}
        if query.payload is not None:
            try:
                decoded = decode(query.payload)
                if isinstance(decoded, dict):
                    req = decoded
            except Exception:  # noqa: BLE001
                req = {}
        self._reply_dict(
            query, self._set_source_reply(req.get("device_id"), req.get("source"))
        )

    def _set_source_reply(self, device_id, source) -> dict:
        """Cold-switch a device's source: stop the old provider, re-realize +
        rewrite the child-params file, start the new provider."""
        if not isinstance(device_id, str) or device_id not in self.cell["resources"]:
            return {"ok": False, "error": f"unknown_device:{device_id}"}
        if source != "off" and source not in self.cell["resources"][device_id]["sources"]:
            return {"ok": False, "error": f"no_source:{device_id}:{source}"}
        error = None
        with self._lock:
            self._procs.stop(f"hal:{device_id}")  # idempotent
            self.active_sources[device_id] = source
            self.realized = realize_cell(self.cell, self.active_sources)
            _dump_realized(self.realized, self.cell_path)
            try:
                self._spawn_provider(device_id)
            except RuntimeError as exc:
                error = str(exc)
        self._publish_devices()
        self._publish_descriptor()
        if error:
            return {"ok": False, "error": error, "device_id": device_id, "source": source}
        return {"ok": True, "device_id": device_id, "source": source}

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
    def _req_payload(query: zenoh.Query) -> dict:
        payload = query.payload
        if payload is None:
            return {}
        try:
            req = decode(payload)
        except Exception:  # noqa: BLE001
            return {}
        return req if isinstance(req, dict) else {}

    @classmethod
    def _req_field(cls, query: zenoh.Query, field: str) -> str | None:
        value = cls._req_payload(query).get(field)
        return value if isinstance(value, str) else None

    @staticmethod
    def _reply_dict(query: zenoh.Query, value: dict) -> None:
        query.reply(str(query.key_expr), encode(value))

    def _publish(self, pub: zenoh.Publisher, value: dict) -> None:
        try:
            pub.put(encode(value))
        except Exception:  # noqa: BLE001
            _log.debug("publish failed", exc_info=True)


def _dump_realized(realized: dict, path: str) -> None:
    """Write the realized inventory to ``path`` (overwriting). The realized
    resources carry ``{contract, kind, launch, node, params}`` so each HAL's
    existing ``load_resource(cell, rid)`` reads its merged params unchanged."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(realized, f, sort_keys=False)


def _write_realized_cell(realized: dict) -> str:
    """Create a temp realized cell file for child HAL spawning; the service
    rewrites it in place on a source switch and unlinks it on shutdown."""
    fd, path = tempfile.mkstemp(prefix="wf-realized-cell-", suffix=".yaml")
    os.close(fd)
    _dump_realized(realized, path)
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
        help="directory of legacy flow YAML specs",
    )
    parser.add_argument(
        "--graphs-dir",
        default="packages/services/task_runner/graphs/flows",
        help="directory of node-graph flow docs",
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

    # cell = design-time truth; the runtime overlay selects an initial source
    # mode per logical device. The service holds both, realizes the concrete
    # inventory, and cold-switches a device's source on cmd/set_source.
    cell = load_cell(args.cell)
    active = load_runtime(args.runtime)["active_sources"] if args.runtime else {}

    session = open_session(args.zenoh_config)
    service = SupervisorService(
        session,
        args.realm,
        cell,
        active,
        flows_dir=args.flows_dir,
        graphs_dir=args.graphs_dir,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
