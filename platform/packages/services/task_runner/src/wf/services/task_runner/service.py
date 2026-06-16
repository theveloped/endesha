"""The task_runner service: runs a YAML statechart over the bus (design: task_runner).

``cmd/start`` instantiates the flow and drives it on a worker thread (serial:
a second start while a run is active is rejected ``busy``). A snapshot listener
publishes ``state`` on every transition; the terminal aggregate/failed publishes
``result``. ``cmd/abort`` flags the leaves and cancels in-flight motion. A
background timer renews the control lease while a run is active.

Run: ``python -m wf.services.task_runner --realm sim --flow <file.yaml>``.
"""

from __future__ import annotations

import argparse
import os
import threading

import zenoh

from wf.contracts.task import keys as task_keys
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import now_ns

from .leaves import Leaves
from .flow import build_flow_class
from .spec import load_spec
from wf.services.config import keys as config_keys

_log = get_logger("wf.services.task_runner.service")

_LEASE_RENEW_S = 10.0


class _Snapshot:
    """Listener published on every transition: builds the ``state`` dict.

    Holds a back-ref to the live flow (set by the service after construction)
    and a ``publish`` callback. ``after_transition`` records history and emits a
    snapshot; ``on_enter_state`` emits on entry (covers the initial state).
    """

    def __init__(self, flow_name: str, publish) -> None:
        self.flow_name = flow_name
        self._publish = publish
        self.sm = None
        self._history: list[dict] = []

    def _emit(self) -> None:
        sm = self.sm
        if sm is None:
            return
        self._publish(
            {
                "t": now_ns(),
                "flow": self.flow_name,
                "configuration": [s.id for s in sm.configuration],
                "terminated": bool(sm.is_terminated),
                "history": list(self._history),
                "context": {
                    "by_pose": sm.context.get("by_pose", []),
                    "conveyor": sm.context.get("conveyor"),
                    "summary": sm.context.get("summary"),
                },
            }
        )

    def after_transition(self, event, source, target) -> None:
        self._history.append(
            {
                "event": str(event),
                "source": getattr(source, "id", None),
                "target": getattr(target, "id", None),
                "t": now_ns(),
            }
        )
        self._emit()

    def on_enter_state(self, target) -> None:
        self._emit()


class TaskRunnerService:
    def __init__(
        self,
        session: zenoh.Session,
        realm: str,
        spec: dict,
        *,
        rid: str = "r1",
        cid: str = "cam0",
        client_id: str | None = None,
    ) -> None:
        self.session = session
        self.realm = realm
        self.spec = spec
        self.name = spec["name"]
        self.rid = rid
        self.cid = cid
        self.client_id = client_id or f"task_runner:{self.name}"
        self.pipeline = spec["vision"]["pipeline"]

        self._flow_cls = build_flow_class(spec)
        self._state_pub = session.declare_publisher(
            task_keys.state(realm, self.name),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._result_pub = session.declare_publisher(
            task_keys.result(realm, self.name),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._queryables: list = []
        self._alive_token = None
        self._stop_event = threading.Event()

        # run state
        self._run_lock = threading.Lock()
        self._active = False
        self._leaves: Leaves | None = None
        self._worker: threading.Thread | None = None
        self._lease_timer: threading.Timer | None = None

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._queryables = [
            self.session.declare_queryable(
                task_keys.cmd_start(self.realm, self.name), self._on_start
            ),
            self.session.declare_queryable(
                task_keys.cmd_abort(self.realm, self.name), self._on_abort
            ),
        ]
        self._alive_token = declare_alive(self.session, self.realm, "task", self.name)
        _log.info("task_runner up: realm=%s flow=%s", self.realm, self.name)

    def run_forever(self) -> None:
        try:
            self._stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._stop_event.set()
        self._cancel_lease_timer()
        if self._leaves is not None:
            self._leaves.close()
        _log.info("task_runner stopped")

    # ── queryables ───────────────────────────────────────────────────────

    def _on_start(self, query: zenoh.Query) -> None:
        k = str(query.key_expr)
        with self._run_lock:
            if self._active:
                query.reply(k, encode({"ok": False, "error": "busy"}))
                return
            missing = self._missing_pose()
            if missing is not None:
                query.reply(k, encode({"ok": False, "error": f"unknown_pose:{missing}"}))
                return
            self._active = True
        query.reply(k, encode({"ok": True, "flow": self.name}))
        self._worker = threading.Thread(
            target=self._run, name=f"task-{self.name}", daemon=True
        )
        self._worker.start()

    def _on_abort(self, query: zenoh.Query) -> None:
        k = str(query.key_expr)
        leaves = self._leaves
        if leaves is not None:
            leaves.abort()
            leaves.cancel_motion()
        query.reply(k, encode({"ok": True}))

    # ── run ──────────────────────────────────────────────────────────────

    def _missing_pose(self) -> str | None:
        """First spec pose with no ``config/poses/{name}`` entry, or None."""
        for pose in self.spec["poses"]:
            reply = self._query(config_keys.pose(pose), {})
            if reply is None or "q" not in reply:
                return pose
        return None

    def _run(self) -> None:
        leaves = Leaves(
            self.session,
            self.realm,
            rid=self.rid,
            cid=self.cid,
            pipeline=self.pipeline,
            client_id=self.client_id,
        )
        self._leaves = leaves
        snapshot = _Snapshot(self.name, self._publish_state)
        try:
            leaves.acquire_lease()
            self._start_lease_timer()
            sm = self._flow_cls(leaves)
            snapshot.sm = sm
            sm.add_listener(snapshot)
            snapshot._emit()  # initial configuration snapshot
            sm.pump()
            self._publish_result(
                {
                    "t": now_ns(),
                    "flow": self.name,
                    "ok": bool(getattr(sm, "ok", False)),
                    "error": sm.error,
                    "summary": sm.context.get("summary"),
                }
            )
        except Exception as exc:  # noqa: BLE001 — a run failure must not crash the service
            _log.exception("run failed")
            self._publish_result(
                {
                    "t": now_ns(),
                    "flow": self.name,
                    "ok": False,
                    "error": repr(exc),
                    "summary": None,
                }
            )
        finally:
            self._cancel_lease_timer()
            leaves.release_lease()
            leaves.close()
            self._leaves = None
            with self._run_lock:
                self._active = False

    # ── lease renewal ────────────────────────────────────────────────────

    def _start_lease_timer(self) -> None:
        def renew() -> None:
            leaves = self._leaves
            if leaves is None or self._stop_event.is_set():
                return
            try:
                leaves.acquire_lease()
            except Exception:
                _log.warning("lease renewal failed", exc_info=True)
            self._start_lease_timer()

        self._lease_timer = threading.Timer(_LEASE_RENEW_S, renew)
        self._lease_timer.daemon = True
        self._lease_timer.start()

    def _cancel_lease_timer(self) -> None:
        if self._lease_timer is not None:
            self._lease_timer.cancel()
            self._lease_timer = None

    # ── publish ──────────────────────────────────────────────────────────

    def _publish_state(self, state: dict) -> None:
        try:
            self._state_pub.put(encode(state))
        except Exception:
            _log.debug("state publish failed", exc_info=True)

    def _publish_result(self, result: dict) -> None:
        try:
            self._result_pub.put(encode(result))
        except Exception:
            _log.debug("result publish failed", exc_info=True)

    def _query(self, key: str, payload: dict, *, timeout_s: float = 5.0):
        replies = self.session.get(key, payload=encode(payload), timeout=timeout_s)
        for reply in replies:
            sample = reply.ok
            if sample is not None:
                return decode(sample.payload)
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="wf.services.task_runner", description=__doc__)
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "sim"),
        help="realm (default env WF_REALM or 'sim')",
    )
    parser.add_argument("--flow", required=True, help="path to a flow YAML file")
    parser.add_argument("--rid", default="r1", help="arm resource id (default r1)")
    parser.add_argument("--cid", default="cam0", help="camera resource id (default cam0)")
    parser.add_argument("--client-id", default=None, help="control lease client id")
    parser.add_argument(
        "--start",
        action="store_true",
        help="auto-issue cmd/start once the service is up",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    spec = load_spec(args.flow)
    session = open_session(args.zenoh_config)
    service = TaskRunnerService(
        session,
        args.realm,
        spec,
        rid=args.rid,
        cid=args.cid,
        client_id=args.client_id,
    )
    try:
        service.start()
        if args.start:
            session.get(
                task_keys.cmd_start(args.realm, spec["name"]),
                payload=encode({}),
                timeout=5.0,
            )
        service.run_forever()
    finally:
        if service._alive_token is not None:
            del service._alive_token
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
