"""The program runner: ONE PackML unit hosting ONE program (RFC §3.4-3.7).

Threads
- **driver**: the only thread that touches the unit machine and the program's
  StateChart. Everything else (queryables, triggers, action threads) enqueues
  work for it (:meth:`_call`).
- **actions**: one thread per running program state action (``run_<state>``),
  each under an :class:`ActionContext`; cancelled when the state is left or
  the unit leaves Execute (Hold/Suspend/Stop/Abort). The next action starts
  only after the previous ones joined (bounded).
- **lease renewer**: renews the cell control lease every 10 s while the unit
  is not Idle/Stopped/Aborted/Complete.
- **state tick**: 1 Hz keepalive publish of ``program/state``.

Unit-state work (all on the driver thread, ``sc`` sent when done)::

    starting    acquire lease, bind roles, construct program (enters initial)
    execute     (re)start actions of the program's active states
    holding /   cancel actions, program.on_hold(); on Execute re-entry the
    suspending  interrupted state's action re-runs from the top (RFC §9.2)
    completing  program reached a final state
    stopping    cancel actions, stop arms, program.on_stop()
    aborting    cancel actions, stop arms, program.on_abort(reason)
    resetting   discard the program instance (the loaded spec stays)
    complete/stopped/aborted/idle   lease released

Program events come from ``self.emit`` (action threads), declarative
``triggers`` (dio channel edges, per-state timers), and ``program/cmd/event``
(HMI/bus). They are dispatched only while the unit executes.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import os
import queue
import re
import threading
import time
import uuid
from pathlib import Path

import zenoh

from wf.contracts.arm import keys as arm_keys
from wf.contracts.arm.messages import ArmStatus
from wf.contracts.control import keys as control_keys
from wf.core.envelope import request as envelope_request
from wf.contracts.program import keys
from wf.contracts.program.keys import UNIT_COMMANDS
from wf.contracts.program.messages import (
    Ack,
    Catalog,
    CatalogEntry,
    EventRequest,
    LoadRequest,
    LogLine,
    ProgramState,
    SaveReply,
    SaveRequest,
    SourceReply,
    TransitionEvent,
)
from wf.contracts.supervisor import keys as sup_keys
from wf.core.audit import QueryAudit
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.core.session import open_session
from wf.core.time import now_ns
from wf.program import ActionCancelled, ActionContext, Machine, Program, ProgramError

from .discovery import Discovered, discover
from .unit import EXECUTING_STATES, LEASE_FREE_STATES, UnitMachine

_log = get_logger("wf.services.program_runner")

_LEASE_RENEW_S = 10.0
_STATE_TICK_S = 1.0
_ACTION_JOIN_S = 3.0
_DRIVER_CALL_TIMEOUT_S = 10.0
_LOG_KEEP = 300
_FILE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.py$")


class _Loaded:
    """The loaded program spec (survives reset; discarded by unload/load)."""

    __slots__ = ("name", "cls", "bindings", "params")

    def __init__(self, name: str, cls: type[Program], bindings: dict, params: dict):
        self.name = name
        self.cls = cls
        self.bindings = bindings
        self.params = params


class _Action:
    __slots__ = ("state_id", "ctx", "thread")

    def __init__(self, state_id: str, ctx: ActionContext, thread: threading.Thread):
        self.state_id = state_id
        self.ctx = ctx
        self.thread = thread


class ProgramRunner:
    def __init__(
        self,
        session: zenoh.Session,
        realm: str,
        programs_dir: str,
        *,
        node: str = "main",
        devices: list[dict] | None = None,
    ) -> None:
        self.session = session
        self.realm = realm
        self._audit = QueryAudit(session, realm, "program_runner")
        self.programs_dir = programs_dir
        self.node = node

        self._catalog: list[Discovered] = []
        self._devices: list[dict] = list(devices or [])
        self._devices_given = devices is not None

        self._loaded: _Loaded | None = None
        self._program: Program | None = None
        self._machine: Machine | None = None
        self._roles = None
        self._client_id: str | None = None
        self._reason: str | None = None
        self._cycle = 0

        self._actions: dict[str, _Action] = {}
        self._timers: dict[tuple[str, str], threading.Timer] = {}
        self._trigger_unsubs: list = []
        self._status_subs: list = []
        self._estop_latched = False

        self._q: queue.Queue = queue.Queue()
        self._driver_thread: threading.Thread | None = None
        self._driver_ident: int | None = None
        self._stop = threading.Event()
        self._lease_thread: threading.Thread | None = None
        self._tick_thread: threading.Thread | None = None

        self._log_lines: collections.deque = collections.deque(maxlen=_LOG_KEEP)
        self._pub_log = session.declare_publisher(
            keys.log(realm), congestion_control=zenoh.CongestionControl.DROP
        )
        self._pub_state = session.declare_publisher(keys.state(realm))
        self._pub_catalog = session.declare_publisher(keys.catalog(realm))
        self._pub_transitions = session.declare_publisher(
            keys.transitions(realm), congestion_control=zenoh.CongestionControl.DROP
        )
        self._queryables: list = []
        self._devices_sub = None
        self._alive_token = None

        # Last: constructing the unit enters Idle and fires our listeners.
        self.unit = UnitMachine(listeners=[self])

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._driver_thread = threading.Thread(target=self._driver_loop, name="program-driver", daemon=True)
        self._driver_thread.start()
        self._rescan()
        if not self._devices_given:
            self._devices_sub = self.session.declare_subscriber(
                sup_keys.supervisor_devices(self.realm, self.node), self._on_devices
            )
            self._fetch_devices()
        self._queryables = [
            self.session.declare_queryable(keys.catalog(self.realm), self._on_catalog_query),
            self.session.declare_queryable(keys.cmd_load(self.realm), self._audit.wrap(self._on_load)),
            self.session.declare_queryable(keys.state(self.realm), self._on_state_query),
            self.session.declare_queryable(keys.cmd_event(self.realm), self._audit.wrap(self._on_event)),
            self.session.declare_queryable(keys.cmd_source(self.realm), self._on_source),
            self.session.declare_queryable(keys.cmd_save(self.realm), self._audit.wrap(self._on_save)),
            self.session.declare_queryable(keys.cmd_delete(self.realm), self._audit.wrap(self._on_delete)),
            self.session.declare_queryable(keys.log(self.realm), self._on_log_query),
        ] + [
            self.session.declare_queryable(keys.cmd(self.realm, c), self._audit.wrap(self._make_cmd_handler(c)))
            for c in UNIT_COMMANDS
        ]
        self._alive_token = self.session.liveliness().declare_token(keys.alive(self.realm))
        self._lease_thread = threading.Thread(target=self._lease_loop, name="program-lease", daemon=True)
        self._lease_thread.start()
        self._tick_thread = threading.Thread(target=self._tick_loop, name="program-state-tick", daemon=True)
        self._tick_thread.start()
        self._publish_state()
        _log.info("program runner up: realm=%s programs=%s (%d found)", self.realm, self.programs_dir, len(self._catalog))

    def run_forever(self) -> None:
        try:
            while not self._stop.wait(1.0):
                pass
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        if self._stop.is_set():
            return
        try:
            self._call(lambda: self._teardown_program("runner_shutdown"), timeout=5.0)
        except Exception:
            _log.debug("teardown on shutdown failed", exc_info=True)
        self._release_lease()
        self._stop.set()
        self._q.put(None)
        for t in (self._driver_thread, self._lease_thread, self._tick_thread):
            if t is not None:
                t.join(timeout=2.0)
        for q in self._queryables:
            try:
                q.undeclare()
            except Exception:
                pass
        self._queryables = []
        for sub in (self._devices_sub,):
            if sub is not None:
                try:
                    sub.undeclare()
                except Exception:
                    pass
        if self._alive_token is not None:
            try:
                self._alive_token.undeclare()
            except Exception:
                pass
            self._alive_token = None
        _log.info("program runner stopped")

    # ── driver thread ────────────────────────────────────────────────────

    def _driver_loop(self) -> None:
        self._driver_ident = threading.get_ident()
        while True:
            item = self._q.get()
            if item is None:
                return
            fn, future = item
            try:
                result = fn()
                if future is not None:
                    future.set_result(result)
            except Exception as exc:  # noqa: BLE001
                if future is not None:
                    future.set_exception(exc)
                else:
                    _log.exception("driver task failed")

    def _post(self, fn) -> None:
        """Fire-and-forget on the driver thread."""
        self._q.put((fn, None))

    def _call(self, fn, timeout: float = _DRIVER_CALL_TIMEOUT_S):
        """Run ``fn`` on the driver thread and return its result."""
        if threading.get_ident() == self._driver_ident:
            return fn()
        future: concurrent.futures.Future = concurrent.futures.Future()
        self._q.put((fn, future))
        return future.result(timeout=timeout)

    # ── catalog / devices ────────────────────────────────────────────────

    def _rescan(self) -> None:
        self._catalog = discover(self.programs_dir)
        self._publish_catalog()

    def _catalog_msg(self) -> Catalog:
        return Catalog(t=now_ns(), programs=[d.entry for d in self._catalog])

    def _publish_catalog(self) -> None:
        try:
            self._pub_catalog.put(encode(self._catalog_msg().to_wire()))
        except Exception:
            _log.debug("catalog publish failed", exc_info=True)

    def _on_catalog_query(self, query) -> None:
        query.reply(str(query.key_expr), encode(self._catalog_msg().to_wire()))

    def _fetch_devices(self) -> None:
        try:
            for reply in self.session.get(sup_keys.supervisor_devices(self.realm, self.node), timeout=3.0):
                if reply.ok is not None:
                    payload = decode(reply.ok.payload)
                    self._devices = list(payload.get("devices") or [])
                    return
        except Exception:
            _log.debug("devices query failed", exc_info=True)
        if not self._devices:
            _log.warning("no device inventory yet (supervisor down?); load will retry")

    def _on_devices(self, sample) -> None:
        try:
            payload = decode(sample.payload)
        except Exception:
            return
        self._devices = list(payload.get("devices") or [])

    # ── state publishing ─────────────────────────────────────────────────

    def _waiting_for(self, program: Program | None) -> list[dict]:
        """What would move the program on from its active states (debug aid)."""
        if program is None:
            return []
        active = set(program.active_state_ids)
        out: list[dict] = []
        try:
            accepted: dict[str, str] = {}
            for st in program.configuration:
                for tr in st.transitions:
                    for ev in tr.events:
                        eid = getattr(ev, "id", str(ev))
                        accepted.setdefault(eid, getattr(tr.target, "id", str(tr.target)))
            for trig in program.triggers:
                if trig.kind == "channel" and trig.event in accepted:
                    out.append({"kind": "channel", "event": trig.event, "target": accepted[trig.event], **trig.params})
                elif trig.kind == "timer" and trig.params.get("state") in active:
                    out.append({"kind": "timer", "event": trig.event, "target": accepted.get(trig.event, ""), **trig.params})
            covered = {w["event"] for w in out}
            for eid, target in sorted(accepted.items()):
                if eid not in covered:
                    out.append({"kind": "event", "event": eid, "target": target})
        except Exception:  # noqa: BLE001 - never let a debug aid break state publishing
            _log.debug("waiting_for failed", exc_info=True)
        return out

    def _state_msg(self) -> ProgramState:
        program = self._program
        loaded = self._loaded
        return ProgramState(
            t=now_ns(),
            unit=self.unit.state_id,
            program=None if loaded is None else loaded.name,
            program_states=[] if program is None else program.active_state_ids,
            actions=sorted(self._actions),
            reason=self._reason,
            params={} if loaded is None else dict(loaded.params),
            bindings={} if loaded is None else dict(loaded.bindings),
            client_id=self._client_id,
            cycle=self._cycle,
            waiting_for=self._waiting_for(program) if self.unit.state_id in EXECUTING_STATES else [],
        )

    # ── program log ──────────────────────────────────────────────────────

    def _emit_log(self, level: str, message: str, source: str | None = None) -> None:
        line = LogLine(
            t=now_ns(),
            level=level,
            source=source or (self._loaded.name if self._loaded is not None else "runner"),
            message=message,
        )
        self._log_lines.append(line)
        try:
            self._pub_log.put(encode(line.to_wire()))
        except Exception:
            _log.debug("log publish failed", exc_info=True)

    def _on_log_query(self, query) -> None:
        query.reply(str(query.key_expr), encode({"lines": [ln.to_wire() for ln in self._log_lines]}))

    # ── program sources (editor) ─────────────────────────────────────────

    def _resolve_file(self, name_or_file: str) -> Path | None:
        """A program's file by catalog name, or a bare ``x.py`` file name."""
        root = Path(self.programs_dir)
        for d in self._catalog:
            if d.entry.name == name_or_file and d.entry.path:
                return Path(d.entry.path)
        if _FILE_RE.match(name_or_file):
            return root / name_or_file
        return None

    def _on_source(self, query) -> None:
        try:
            req = decode(query.payload) if query.payload is not None else {}
            name = str(req.get("name") or req.get("file") or "")
            path = self._resolve_file(name)
            if path is None or not path.is_file():
                reply = SourceReply(ok=False, name=name, error=f"unknown_program:{name}")
            else:
                entry = next((d.entry for d in self._catalog if d.entry.path == str(path)), None)
                reply = SourceReply(ok=True, name=entry.name if entry else path.stem, path=str(path),
                                    text=path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            reply = SourceReply(ok=False, error=f"source_failed:{exc!r}")
        query.reply(str(query.key_expr), encode(reply.to_wire()))

    def _on_save(self, query) -> None:
        try:
            req = SaveRequest.from_wire(decode(query.payload))
        except Exception as exc:
            query.reply(str(query.key_expr), encode(SaveReply(ok=False, error=f"bad_request:{exc!r}").to_wire()))
            return
        try:
            reply = self._call(lambda: self._save(req))
        except Exception as exc:  # noqa: BLE001
            reply = SaveReply(ok=False, error=f"save_failed:{exc!r}")
        query.reply(str(query.key_expr), encode(reply.to_wire()))

    def _save(self, req: SaveRequest) -> SaveReply:
        if not _FILE_RE.match(req.file):
            return SaveReply(ok=False, error="bad_file:expected a bare module name like my_program.py")
        root = Path(self.programs_dir)
        root.mkdir(parents=True, exist_ok=True)
        path = root / req.file
        tmp = path.with_suffix(".py.tmp")
        tmp.write_text(req.text, encoding="utf-8")
        os.replace(tmp, path)
        self._rescan()
        entry = next((d.entry for d in self._catalog if d.entry.path == str(path)), None)
        if entry is None:
            entry = CatalogEntry(name=path.stem, path=str(path), error="not discovered after save")
        self._emit_log("info" if entry.error is None else "warning",
                       f"saved {req.file}" + ("" if entry.error is None else f" (import error: {entry.error.splitlines()[-1]})"),
                       source="runner")
        return SaveReply(ok=True, entry=entry)

    def _on_delete(self, query) -> None:
        try:
            req = decode(query.payload) if query.payload is not None else {}
            name = str(req.get("name") or req.get("file") or "")
            err = self._call(lambda: self._delete(name))
        except Exception as exc:  # noqa: BLE001
            err = f"delete_failed:{exc!r}"
        query.reply(str(query.key_expr), encode(Ack(ok=err is None, error=err).to_wire()))

    def _delete(self, name: str) -> str | None:
        if self._loaded is not None and self._loaded.name == name and self.unit.state_id not in ("idle", "stopped"):
            return f"invalid_in_state:{self.unit.state_id}"
        path = self._resolve_file(name)
        if path is None or not path.is_file():
            return f"unknown_program:{name}"
        path.unlink()
        if self._loaded is not None and self._loaded.name == name:
            self._teardown_program("deleted")
            self._loaded = None
        self._rescan()
        self._emit_log("info", f"deleted {path.name}", source="runner")
        self._publish_state()
        return None

    def _publish_state(self) -> None:
        try:
            self._pub_state.put(encode(self._state_msg().to_wire()))
        except Exception:
            _log.debug("state publish failed", exc_info=True)

    def _on_state_query(self, query) -> None:
        query.reply(str(query.key_expr), encode(self._state_msg().to_wire()))

    def _tick_loop(self) -> None:
        while not self._stop.wait(_STATE_TICK_S):
            self._publish_state()

    def _publish_transition(self, scope: str, source, target, event, detail=None) -> None:
        try:
            self._pub_transitions.put(
                encode(TransitionEvent(t=now_ns(), scope=scope, source=source, target=target,
                                       event=event, detail=detail).to_wire())
            )
        except Exception:
            _log.debug("transition publish failed", exc_info=True)

    # ── queryables (zenoh threads -> driver) ─────────────────────────────

    def _reply(self, query, ack: Ack) -> None:
        query.reply(str(query.key_expr), encode(ack.to_wire()))

    def _on_load(self, query) -> None:
        try:
            req = LoadRequest.from_wire(decode(query.payload))
        except Exception as exc:
            self._reply(query, Ack(ok=False, error=f"bad_request:{exc!r}"))
            return
        try:
            err = self._call(lambda: self._load(req))
        except Exception as exc:  # noqa: BLE001
            err = f"load_failed:{exc!r}"
        self._reply(query, Ack(ok=err is None, error=err))

    def _make_cmd_handler(self, command: str):
        def handler(query) -> None:
            data: dict = {}
            try:
                if query.payload is not None:
                    decoded = decode(query.payload)
                    if isinstance(decoded, dict):
                        data = decoded
            except Exception:
                pass
            try:
                err = self._call(lambda: self._unit_command(command, data))
            except Exception as exc:  # noqa: BLE001
                err = f"command_failed:{exc!r}"
            self._reply(query, Ack(ok=err is None, error=err))

        return handler

    def _on_event(self, query) -> None:
        try:
            req = EventRequest.from_wire(decode(query.payload))
        except Exception as exc:
            self._reply(query, Ack(ok=False, error=f"bad_request:{exc!r}"))
            return
        try:
            err = self._call(lambda: self._external_event(req.event, req.data))
        except Exception as exc:  # noqa: BLE001
            err = f"event_failed:{exc!r}"
        self._reply(query, Ack(ok=err is None, error=err))

    # ── load / unload (driver thread) ────────────────────────────────────

    def _load(self, req: LoadRequest) -> str | None:
        if self.unit.state_id not in ("idle", "stopped"):
            return f"invalid_in_state:{self.unit.state_id}"
        self._rescan()
        found = next((d for d in self._catalog if d.entry.name == req.name), None)
        if found is None:
            return f"unknown_program:{req.name}"
        if found.cls is None:
            return f"program_broken:{found.entry.error}"
        if not self._devices:
            self._fetch_devices()
        # Validate bindings now (fail at load, not at start).
        probe = Machine(self.session, self.realm, "probe", self._devices)
        try:
            bindings = probe.resolve_bindings(dict(found.cls.roles), req.bindings)
        except ProgramError as exc:
            return str(exc)
        finally:
            probe.close()
        unknown = set(req.params) - set(found.cls.params)
        if unknown:
            return f"unknown_params:{','.join(sorted(unknown))}"
        params = {**found.cls.params, **req.params}
        self._teardown_program("reload")
        self._loaded = _Loaded(req.name, found.cls, bindings, params)
        self._reason = None
        self._cycle = 0
        _log.info("loaded program %s bindings=%s params=%s", req.name, bindings, params)
        self._publish_state()
        return None

    def _unit_command(self, command: str, data: dict) -> str | None:
        if command == "unload":
            if self.unit.state_id not in ("idle", "stopped"):
                return f"invalid_in_state:{self.unit.state_id}"
            self._teardown_program("unload")
            self._loaded = None
            self._publish_state()
            return None
        if command == "start" and self._loaded is None:
            return "no_program_loaded"
        if not self.unit.accepts(command):
            return f"invalid_in_state:{self.unit.state_id}"
        if command in ("abort", "stop"):
            self._reason = str(data.get("reason") or "operator")
            self._emit_log("warning" if command == "abort" else "info", f"{command}: {self._reason}", source="runner")
        else:
            self._emit_log("info", f"command: {command}", source="runner")
        self.unit.send(command)
        return None

    def _external_event(self, event: str, data: dict) -> str | None:
        program = self._program
        if program is None:
            return "no_program_running"
        if self.unit.state_id not in EXECUTING_STATES:
            return f"invalid_in_state:{self.unit.state_id}"
        if event not in {e.id for e in program.events}:
            return f"unknown_event:{event}"
        self._dispatch(program, event, data)
        return None

    # ── ProgramRuntime protocol (called by the Program) ──────────────────

    def program_event(self, event: str, data: dict) -> None:
        program = self._program
        self._post(lambda: self._dispatch_if_current(program, event, data))

    def state_entered(self, program: Program, state, event) -> None:
        if program is not self._program and self._program is not None:
            return
        if self.unit.state_id in EXECUTING_STATES:
            self._start_action(program, state.id)
            self._arm_timers(program, state.id)

    def state_exited(self, program: Program, state, event) -> None:
        self._cancel_action(state.id)
        self._disarm_timers(state.id)

    def program_transition(self, program: Program, source, target, event) -> None:
        self._publish_transition("program", source, target, event)

    def log(self, message: str) -> None:
        name = self._loaded.name if self._loaded is not None else "?"
        _log.info("[%s] %s", name, message)
        self._emit_log("info", message, source=name)

    # ── program event dispatch (driver thread) ───────────────────────────

    def _dispatch_if_current(self, program, event: str, data: dict) -> None:
        if program is None or program is not self._program:
            return
        if self.unit.state_id not in EXECUTING_STATES:
            _log.debug("dropping event %s while unit is %s", event, self.unit.state_id)
            return
        self._dispatch(program, event, data)

    def _dispatch(self, program: Program, event: str, data: dict) -> None:
        try:
            program.send(event, **data)
        except Exception as exc:  # noqa: BLE001
            self._abort(f"program_error:{event}:{exc!r}")
            return
        if program.is_done and self.unit.state_id in EXECUTING_STATES:
            self.unit.send("program_complete")
        self._publish_state()

    # ── actions ──────────────────────────────────────────────────────────

    def _start_action(self, program: Program, state_id: str) -> None:
        if state_id in self._actions:
            return
        fn = program.action_for(state_id)
        if fn is None:
            return
        ctx = ActionContext(state_id, log=self.log)
        thread = threading.Thread(
            target=self._action_body, args=(program, state_id, fn, ctx),
            name=f"action-{state_id}", daemon=True,
        )
        self._actions[state_id] = _Action(state_id, ctx, thread)
        thread.start()
        self._publish_state()

    def _action_body(self, program: Program, state_id: str, fn, ctx: ActionContext) -> None:
        ctx._bind()
        try:
            fn(ctx)
        except ActionCancelled:
            pass
        except ProgramError as exc:
            reason = f"action_error:{state_id}:{exc}"
            _log.warning("action %s failed: %s", state_id, exc)
            self._emit_log("error", reason)
            self._post(lambda: self._abort(reason))
        except Exception as exc:  # noqa: BLE001
            reason = f"action_crash:{state_id}:{exc!r}"
            _log.exception("action %s crashed", state_id)
            self._emit_log("error", reason)
            self._post(lambda: self._abort(reason))
        finally:
            ctx._unbind()
            self._post(lambda: self._action_finished(state_id, ctx))

    def _action_finished(self, state_id: str, ctx: ActionContext) -> None:
        current = self._actions.get(state_id)
        if current is not None and current.ctx is ctx:
            del self._actions[state_id]
            self._publish_state()

    def _cancel_action(self, state_id: str) -> None:
        action = self._actions.pop(state_id, None)
        if action is None:
            return
        action.ctx.cancel()
        action.thread.join(timeout=_ACTION_JOIN_S)
        if action.thread.is_alive():
            _log.error("action %s did not unwind within %.1fs", state_id, _ACTION_JOIN_S)
            self._post(lambda: self._abort(f"action_hang:{state_id}"))
        self._publish_state()

    def _cancel_all_actions(self) -> None:
        for state_id in list(self._actions):
            self._cancel_action(state_id)

    def _start_active_actions(self) -> None:
        program = self._program
        if program is None:
            return
        for state_id in program.active_state_ids:
            self._start_action(program, state_id)
            self._arm_timers(program, state_id)

    # ── triggers ─────────────────────────────────────────────────────────

    def _install_channel_triggers(self, program: Program) -> None:
        for trig in program.triggers:
            if trig.kind != "channel":
                continue
            role, channel, edge, event = (trig.params["role"], trig.params["channel"], trig.params["edge"], trig.event)
            proxy = self._roles[role]

            def on_change(name, old, new, *, _channel=channel, _edge=edge, _event=event, _program=program):
                if name != _channel:
                    return
                fires = (
                    (_edge == "rising" and new is True and old is not True)
                    or (_edge == "falling" and new is False and old is not False)
                    or (_edge == "change")
                )
                if fires:
                    self._post(lambda: self._dispatch_if_current(_program, _event, {"channel": name, "value": new}))

            self._trigger_unsubs.append(proxy.watch(on_change))

    def _arm_timers(self, program: Program, state_id: str) -> None:
        for trig in program.triggers:
            if trig.kind != "timer" or trig.params["state"] != state_id:
                continue
            key = (state_id, trig.event)
            if key in self._timers:
                continue
            timer = threading.Timer(
                trig.params["seconds"],
                lambda _key=key, _event=trig.event, _program=program: self._post(
                    lambda: self._timer_fired(_key, _program, _event)
                ),
            )
            timer.daemon = True
            self._timers[key] = timer
            timer.start()

    def _timer_fired(self, key, program, event) -> None:
        if self._timers.pop(key, None) is None:
            return  # disarmed
        state_id = key[0]
        if program is self._program and state_id in program.active_state_ids:
            self._dispatch_if_current(program, event, {"timer": state_id})

    def _disarm_timers(self, state_id: str) -> None:
        for key in [k for k in self._timers if k[0] == state_id]:
            self._timers.pop(key).cancel()

    def _disarm_all_timers(self) -> None:
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()

    # ── safety watch: bound arms' estop / protective stop ────────────────

    def _install_status_watch(self) -> None:
        for role, rid in (self._roles.bindings if self._roles is not None else {}).items():
            entry = next((d for d in self._devices if d["id"] == rid), None)
            if entry is None or entry.get("contract") != "arm":
                continue
            self._status_subs.append(
                self.session.declare_subscriber(arm_keys.state_status(self.realm, rid), self._on_arm_status)
            )

    def _on_arm_status(self, sample) -> None:
        try:
            st = ArmStatus.from_wire(decode(sample.payload))
        except Exception:
            return
        active = bool(st.estop or st.protective_stop)
        if active and not self._estop_latched:
            self._estop_latched = True
            reason = "safety:estop" if st.estop else "safety:protective_stop"
            self._post(lambda: self._safety_abort(reason))
        elif not active:
            self._estop_latched = False

    def _safety_abort(self, reason: str) -> None:
        if self.unit.state_id in ("aborting", "aborted", "clearing"):
            return
        self._abort(reason)

    def _abort(self, reason: str) -> None:
        if not self.unit.accepts("abort"):
            _log.warning("abort (%s) ignored in state %s", reason, self.unit.state_id)
            return
        self._reason = reason
        self._emit_log("warning", f"abort: {reason}", source="runner")
        self.unit.send("abort")

    # ── lease ────────────────────────────────────────────────────────────

    def _acquire_lease(self) -> str | None:
        assert self._client_id is not None
        try:
            reply = envelope_request(
                self.session,
                control_keys.cmd_acquire(self.realm),
                {"user": f"program:{self._loaded.name}"},
                client_id=self._client_id,
                timeout_s=3.0,
            )
        except Exception as exc:  # noqa: BLE001
            return f"lease_error:{exc!r}"
        return None if reply.ok else str(reply.error)

    def _release_lease(self) -> None:
        cid = self._client_id
        if cid is None:
            return
        try:
            # Best-effort: conflict:not_holder after expiry is fine.
            envelope_request(self.session, control_keys.cmd_release(self.realm),
                             {}, client_id=cid, timeout_s=2.0)
        except Exception:
            _log.debug("lease release failed", exc_info=True)

    def _lease_loop(self) -> None:
        while not self._stop.wait(_LEASE_RENEW_S):
            if self._client_id is None or self.unit.state_id in LEASE_FREE_STATES:
                continue
            err = self._acquire_lease()
            if err is not None:
                self._post(lambda: self._abort(f"lease_lost:{err}"))

    # ── unit listeners (driver thread; ``sc`` moves acting states on) ────

    def on_transition(self, event=None, source=None, target=None, **kwargs) -> None:
        self._publish_transition(
            "unit",
            None if source is None else source.id,
            "" if target is None else target.id,
            None if event is None else getattr(event, "id", str(event)),
            self._reason if target is not None and target.id in ("aborting", "stopping") else None,
        )

    def on_enter_state(self, state, **kwargs) -> None:
        self._publish_state()

    def on_enter_starting(self, **kwargs) -> None:
        loaded = self._loaded
        assert loaded is not None
        self._client_id = f"program:{loaded.name}:{uuid.uuid4().hex[:8]}"
        err = self._acquire_lease()
        if err is not None:
            self._reason = f"lease:{err}"
            self.unit.send("abort")
            return
        try:
            self._machine = Machine(self.session, self.realm, self._client_id, self._devices, program_name=loaded.name)
            self._roles = self._machine.bind(dict(loaded.cls.roles), loaded.bindings)
            self._program = loaded.cls(self._roles, loaded.params, self)
            self._install_channel_triggers(self._program)
            self._install_status_watch()
        except Exception as exc:  # noqa: BLE001
            _log.exception("program construction failed")
            self._reason = f"construct:{exc!r}"
            self.unit.send("abort")
            return
        self._cycle += 1
        self._emit_log("info", f"started {loaded.name} cycle {self._cycle} bindings={loaded.bindings} params={loaded.params}", source="runner")
        self.unit.send("sc")

    def on_enter_execute(self, source=None, **kwargs) -> None:
        program = self._program
        if program is None:
            self._abort("no_program_instance")
            return
        if source is not None and source.id in ("unholding", "unsuspending"):
            try:
                program.on_resume()
            except Exception:
                _log.exception("on_resume failed")
        if program.is_done:
            self.unit.send("program_complete")
            return
        self._start_active_actions()

    def on_enter_holding(self, **kwargs) -> None:
        self._cancel_all_actions()
        self._disarm_all_timers()
        self._hook("on_hold")
        self.unit.send("sc")

    def on_enter_suspending(self, **kwargs) -> None:
        self._cancel_all_actions()
        self._disarm_all_timers()
        self._hook("on_hold")
        self.unit.send("sc")

    def on_enter_unholding(self, **kwargs) -> None:
        self.unit.send("sc")

    def on_enter_unsuspending(self, **kwargs) -> None:
        self.unit.send("sc")

    def on_enter_completing(self, **kwargs) -> None:
        self._cancel_all_actions()
        self._disarm_all_timers()
        self.unit.send("sc")

    def on_enter_stopping(self, **kwargs) -> None:
        self._cancel_all_actions()
        self._disarm_all_timers()
        self._stop_arms()
        self._hook("on_stop")
        self.unit.send("sc")

    def on_enter_aborting(self, **kwargs) -> None:
        self._cancel_all_actions()
        self._disarm_all_timers()
        self._stop_arms()
        self._hook("on_abort", self._reason or "unknown")
        self.unit.send("sc")

    def on_enter_clearing(self, **kwargs) -> None:
        self.unit.send("sc")

    def on_enter_resetting(self, **kwargs) -> None:
        self._teardown_program("reset")
        self._reason = None
        self.unit.send("sc")

    def on_enter_complete(self, **kwargs) -> None:
        self._release_lease()

    def on_enter_stopped(self, **kwargs) -> None:
        self._release_lease()

    def on_enter_aborted(self, **kwargs) -> None:
        self._release_lease()

    def on_enter_idle(self, **kwargs) -> None:
        self._release_lease()

    # ── helpers ──────────────────────────────────────────────────────────

    def _hook(self, name: str, *args) -> None:
        program = self._program
        if program is None:
            return
        try:
            getattr(program, name)(*args)
        except Exception:
            _log.exception("program hook %s failed", name)

    def _stop_arms(self) -> None:
        if self._roles is None:
            return
        for role, rid in self._roles.bindings.items():
            entry = next((d for d in self._devices if d["id"] == rid), None)
            if entry is None or entry.get("contract") != "arm":
                continue
            try:
                self.session.get(arm_keys.cmd_stop(self.realm, rid), payload=encode({}), timeout=2.0)
            except Exception:
                _log.debug("arm stop failed", exc_info=True)

    def _teardown_program(self, why: str) -> None:
        """Discard the program instance (not the loaded spec)."""
        self._cancel_all_actions()
        self._disarm_all_timers()
        for unsub in self._trigger_unsubs:
            try:
                unsub()
            except Exception:
                pass
        self._trigger_unsubs = []
        for sub in self._status_subs:
            try:
                sub.undeclare()
            except Exception:
                pass
        self._status_subs = []
        if self._machine is not None:
            self._machine.close()
        self._machine = None
        self._roles = None
        self._program = None
        self._estop_latched = False
        _log.debug("program instance torn down (%s)", why)


# ── entrypoint ─────────────────────────────────────────────────────────────


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="wf.services.program_runner", description=__doc__)
    parser.add_argument("--realm", default=os.environ.get("WF_REALM", "cell"))
    parser.add_argument("--programs", default="deploy/programs", help="directory of program modules")
    parser.add_argument("--node", default="main", help="supervisor node id (device inventory)")
    parser.add_argument("--zenoh-config", default=None)
    args = parser.parse_args(argv)

    session = open_session(args.zenoh_config)
    runner = ProgramRunner(session, args.realm, args.programs, node=args.node)
    try:
        runner.start()
        runner.run_forever()
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
