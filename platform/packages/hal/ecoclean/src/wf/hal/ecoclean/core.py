"""``WasherCore``: the ``washer`` contract on top of an Ecoclean PLC tag table.

One process serves two contracts (like the arm serving its io pins):

- the raw ``tags`` device (``provides.<rid>: {contract: tags, tags: {...}}``
  in cell.yaml) — a :class:`TagsCore` over the sim / OPC-UA backend, so the
  PLC stays fully visible and forceable on the IO page;
- the ``washer`` device — this class: derives the phase from the machine's
  status lines, drives the load/unload handshakes as actions, exposes the
  wash program as a recipe.

Handshakes (ported from ecoclean-controller ``u1``/``u2``/``u3``/``u4``):

    open_door   ready_to_load:    PermissionToClose=1, LoadRequest=1 … DoorOpen
                ready_to_unload:  UnLoadRequest/InProgress/Complete pulse … DoorOpen … ReadyToLoad,
                                  then UnLoadComplete=0, LoadRequest=1
    close_door  door_open:        PermissionToClose=1, ResetSignalCloseDoor pulse … DoorClosed, LoadRequest=0
    start_wash  door_open:        [WashProgram=n], PermissionToClose=1, LoadInProgress=1, LoadRequest=0,
                                  LoadComplete=1, LoadInProgress=0 … DoorClosed, LoadComplete=0 … WashingInProgress
    reset       any:              all handshake lines 0, PermissionToClose=1, FaultReset pulse if faulted
    cancel / stop_door:           PermissionToClose=0 (a travelling door stops)

Every write is a host write on the tags core (no lease check there: the
washer *is* the device); the washer's own commands are lease-gated.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from wf.contracts.control.watcher import LeaseWatcher
from wf.contracts.washer import keys
from wf.contracts.washer.messages import (
    Recipe,
    RecipeReply,
    RecipeStep,
    SetRecipe,
    WasherStatus,
)
from wf.core.action import ActionServer, GoalHandle
from wf.core.codec import decode, encode
from wf.core.envelope import RecentReplies, Request, fail, ok_value, serve_query
from wf.core.log import get_logger
from wf.core.time import now_ns
from wf.hal.tags_core import TagsBackend, TagsCore

from . import inventory as inv

_log = get_logger("wf.hal.ecoclean")

_KEEPALIVE_S = 1.0


class SequenceCancelled(Exception):
    pass


class SequenceFailed(Exception):
    pass


class WasherCore:
    def __init__(self, session, realm: str, rid: str, params: dict, backend: TagsBackend):
        self.session = session
        self.realm = realm
        self.rid = rid
        self.params = params
        self.backend = backend
        self.door_timeout_s = float(params.get("door_timeout_s", 90.0))
        self.cycle_start_timeout_s = float(params.get("cycle_start_timeout_s", 30.0))
        self.settle_s = float(params.get("settle_s", 0.5))

        self._lease = LeaseWatcher(session, realm)
        self._recent = RecentReplies()

        # ── the provided raw tags device ─────────────────────────────────
        provides = params.get("provides") or {}
        tags_entries = [(pid, spec) for pid, spec in provides.items() if spec.get("contract") == "tags"]
        if len(tags_entries) > 1:
            raise ValueError("bad_cell:a washer provides at most one tags device")
        if tags_entries:
            tags_rid, spec = tags_entries[0]
            tags_params = {k: v for k, v in spec.items() if k != "contract"}
        else:
            tags_rid, tags_params = f"{rid}_plc", {}
            _log.warning("no provides.<id> {contract: tags} for %s; publishing the PLC as %s", rid, tags_rid)
        tags_params.setdefault("poll_hz", params.get("poll_hz", 20))
        self.tags = TagsCore(session, realm, tags_rid, tags_params, backend, lease=self._lease,
                             on_change=self._on_tag_change)
        # display name -> channel name (whatever the cell called it)
        self._name_of: dict[str, str] = {}
        for name, td in self.tags.channels.items():
            display = td.address.get("tag")
            if display is not None:
                self._name_of.setdefault(str(display), name)

        self._lock = threading.Lock()
        self._sequence: str | None = None
        self._detail = ""
        self._status = WasherStatus(t=now_ns())
        self._pub = session.declare_publisher(keys.state_status(realm, rid))
        self._actions = ActionServer(session, keys.action_prefix(realm, rid))
        self._queryables: list = []
        self._alive_token = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._initialised = False

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._lease.start()
        self.tags.start()
        for name, fn in (
            ("open_door", self._seq_open_door),
            ("close_door", self._seq_close_door),
            ("start_wash", self._seq_start_wash),
            ("reset", self._seq_reset),
        ):
            self._actions.register(name, self._make_accept(name), self._make_execute(name, fn))
        self._queryables = [
            self.session.declare_queryable(keys.state_status(self.realm, self.rid), self._on_status_query),
            self.session.declare_queryable(keys.cmd_stop_door(self.realm, self.rid), self._on_stop_door),
            self.session.declare_queryable(keys.cmd_get_recipe(self.realm, self.rid), self._on_get_recipe),
            self.session.declare_queryable(keys.cmd_set_recipe(self.realm, self.rid), self._on_set_recipe),
        ]
        self._alive_token = self.session.liveliness().declare_token(keys.alive(self.realm, self.rid))
        self._refresh()
        self._thread = threading.Thread(target=self._loop, name="washer-core", daemon=True)
        self._thread.start()
        _log.info("washer core up: realm=%s rid=%s tags=%s", self.realm, self.rid, self.tags.rid)

    def run_forever(self) -> None:
        try:
            while not self._stop.wait(1.0):
                pass
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._actions.close()
        for q in self._queryables:
            try:
                q.undeclare()
            except Exception:
                pass
        self._queryables = []
        if self._alive_token is not None:
            try:
                self._alive_token.undeclare()
            except Exception:
                pass
            self._alive_token = None
        self.tags.shutdown()
        self._lease.close()
        _log.info("washer core stopped")

    # ── tag access by PLC display name ───────────────────────────────────

    def _chan(self, display: str) -> str:
        name = self._name_of.get(display)
        if name is None:
            raise KeyError(f"plc_tag_missing:{display}")
        return name

    def get(self, display: str):
        return self.tags.reported(self._chan(display))

    def write(self, display: str, value) -> None:
        self.tags.write(self._chan(display), value)
        self._refresh()

    def _wait(self, display: str, expect: bool, timeout_s: float, handle: GoalHandle | None,
              detail: str) -> None:
        """Block until ``display`` reports ``expect``; raises on cancel/timeout."""
        name = self._chan(display)
        self._set_detail(detail)
        deadline = time.monotonic() + timeout_s
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise SequenceFailed(f"timeout:{display}")
            if self.tags.wait_until(lambda get: bool(get(name)) is expect, min(0.2, left)):
                return
            if handle is not None and handle.cancel_requested:
                raise SequenceCancelled()
            if bool(self.get("GeneralFault")):
                raise SequenceFailed(f"fault:{int(self.get('stoernummer') or 0)}")

    def _sleep(self, seconds: float, handle: GoalHandle | None) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if handle is not None and handle.cancel_requested:
                raise SequenceCancelled()
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))

    @property
    def connected(self) -> bool:
        return bool(getattr(self.backend, "connected", True))

    # ── status ───────────────────────────────────────────────────────────

    def _derive(self) -> WasherStatus:
        g = self.get
        try:
            door_open, door_closed = bool(g("DoorOpen")), bool(g("DoorClosed"))
            ready_to_load, ready_to_unload = bool(g("ReadyToLoad")), bool(g("ReadyToUnload"))
            washing, fault, auto = bool(g("WashingInProgress")), bool(g("GeneralFault")), bool(g("Auto"))
            fault_code = int(g("stoernummer") or 0)
            program = str(g(inv.RECIPE_NAME_DISPLAY) or "")
            program_no = int(g("WashProgram") or 0)
        except KeyError:
            return WasherStatus(t=now_ns(), connected=self.connected, detail="plc tags missing")
        connected = self.connected
        if door_open and not door_closed:
            door = "open"
        elif door_closed and not door_open:
            door = "closed"
        elif not door_open and not door_closed:
            door = "moving"
        else:
            door = "unknown"
        if not connected:
            phase = "initializing"
        elif fault:
            phase = "fault"
        elif washing:
            phase = "washing"
        elif ready_to_unload and door == "closed":
            phase = "ready_to_unload"
        elif door == "open":
            phase = "door_open"
        elif door == "closed" and ready_to_load:
            phase = "ready_to_load"
        elif door == "moving":
            phase = "door_moving"
        else:
            phase = "initializing"
        with self._lock:
            sequence, detail = self._sequence, self._detail
        return WasherStatus(
            t=now_ns(), phase=phase, door=door, connected=connected, auto=auto, fault=fault,
            fault_code=fault_code, washing=washing, ready_to_load=ready_to_load,
            ready_to_unload=ready_to_unload, program=program, program_no=program_no,
            sequence=sequence, detail=detail,
        )

    @property
    def status(self) -> WasherStatus:
        with self._lock:
            return self._status

    def _refresh(self, *, force: bool = False) -> None:
        st = self._derive()
        with self._lock:
            prev = self._status
            self._status = st
        changed = force or (
            (st.phase, st.door, st.connected, st.auto, st.fault, st.fault_code, st.washing,
             st.ready_to_load, st.ready_to_unload, st.program, st.program_no, st.sequence, st.detail)
            != (prev.phase, prev.door, prev.connected, prev.auto, prev.fault, prev.fault_code, prev.washing,
                prev.ready_to_load, prev.ready_to_unload, prev.program, prev.program_no, prev.sequence, prev.detail)
        )
        if changed:
            try:
                self._pub.put(encode(st.to_wire()))
            except Exception as exc:
                _log.warning("status publish failed: %r", exc)
        if st.connected and not self._initialised:
            self._initialised = True
            self._on_connected(st)

    def _on_connected(self, st: WasherStatus) -> None:
        """Bring the handshake lines in line with what the machine shows
        (the old controller's ``init_ECM_state``); best-effort."""
        try:
            if st.ready_to_load and st.door == "closed":
                self.write("LoadRequest", False)
            elif st.door == "open" and st.ready_to_load:
                self.write("PermissionToClose", False)
                self.write("LoadRequest", True)
        except Exception as exc:
            _log.warning("init writes failed: %r", exc)

    def _on_tag_change(self, name, old, new) -> None:
        self._refresh()

    def _set_detail(self, detail: str) -> None:
        with self._lock:
            self._detail = detail
        self._refresh()

    def _loop(self) -> None:
        while not self._stop.wait(_KEEPALIVE_S):
            self._refresh(force=True)

    def _on_status_query(self, query) -> None:
        query.reply(str(query.key_expr), encode(self.status.to_wire()))

    # ── actions ──────────────────────────────────────────────────────────

    def _make_accept(self, name: str) -> Callable[[dict], str | None]:
        allowed = {
            "open_door": ("ready_to_load", "ready_to_unload"),
            "close_door": ("door_open",),
            "start_wash": ("door_open",),
            "reset": None,
        }[name]

        def accept(goal: dict, client_id: str | None = None) -> str | None:
            if not self._lease.holds(client_id):
                return "no_control"
            st = self.status
            if not st.connected:
                return "not_connected"
            if allowed is not None and st.phase not in allowed:
                return f"wrong_phase:{st.phase}"
            return None

        return accept

    def _make_execute(self, name: str, fn: Callable[[GoalHandle], None]) -> Callable[[GoalHandle], None]:
        def execute(handle: GoalHandle) -> None:
            with self._lock:
                self._sequence, self._detail = name, ""
            self._refresh()
            try:
                fn(handle)
            except SequenceCancelled:
                self._release_permission()
                handle.set_canceled()
            except SequenceFailed as exc:
                self._release_permission()
                handle.fail(str(exc))
            except Exception as exc:
                _log.exception("%s failed", name)
                self._release_permission()
                handle.fail(f"error:{exc!r}")
            else:
                if not handle.is_terminal:
                    handle.succeed(phase=self.status.phase)
            finally:
                with self._lock:
                    self._sequence, self._detail = None, ""
                self._refresh()

        return execute

    def _release_permission(self) -> None:
        try:
            self.write("PermissionToClose", False)
        except Exception:
            _log.debug("release permission failed", exc_info=True)

    def _seq_open_door(self, handle: GoalHandle) -> None:
        phase = self.status.phase
        if phase == "ready_to_load":
            self.write("PermissionToClose", True)
            self._sleep(self.settle_s, handle)
            self.write("LoadRequest", True)
            handle.feedback(0.3, step="load_request")
            self._wait("DoorOpen", True, self.door_timeout_s, handle, "waiting for door open")
            self.write("PermissionToClose", False)
        elif phase == "ready_to_unload":
            self.write("PermissionToClose", True)
            self.write("UnLoadRequest", True)
            self.write("UnLoadInProgress", True)
            self._sleep(0.1, handle)
            self.write("UnLoadRequest", False)
            self._sleep(0.1, handle)
            self.write("UnLoadComplete", True)
            self._sleep(0.1, handle)
            self.write("UnLoadInProgress", False)
            handle.feedback(0.3, step="unload_complete")
            self._wait("DoorOpen", True, self.door_timeout_s, handle, "waiting for door open")
            handle.feedback(0.8, step="door_open")
            try:
                self._wait("ReadyToLoad", True, 10.0, None, "waiting for ready to load")
            except SequenceFailed:
                _log.warning("machine did not report ReadyToLoad after unload")
            self.write("UnLoadComplete", False)
            self.write("LoadRequest", True)
            self.write("PermissionToClose", False)
        else:
            raise SequenceFailed(f"wrong_phase:{phase}")

    def _seq_close_door(self, handle: GoalHandle) -> None:
        self.write("PermissionToClose", True)
        self.write("ResetSignalCloseDoor", True)
        try:
            self._sleep(1.0, handle)
        finally:
            self.write("ResetSignalCloseDoor", False)
        self._wait("DoorClosed", True, self.door_timeout_s, handle, "waiting for door closed")
        self.write("LoadRequest", False)
        self.write("LoadComplete", False)

    def _seq_start_wash(self, handle: GoalHandle) -> None:
        program = handle.goal.get("program")
        if program is not None:
            self.write("WashProgram", int(program))
        self.write("PermissionToClose", True)
        self.write("LoadInProgress", True)
        self._sleep(self.settle_s, handle)
        self.write("LoadRequest", False)
        self._sleep(self.settle_s, handle)
        self.write("LoadComplete", True)
        self.write("LoadInProgress", False)
        handle.feedback(0.3, step="load_complete")
        self._wait("DoorClosed", True, self.door_timeout_s, handle, "waiting for door closed")
        self.write("LoadComplete", False)
        handle.feedback(0.7, step="door_closed")
        self._wait("WashingInProgress", True, self.cycle_start_timeout_s, None, "waiting for cycle start")

    def _seq_reset(self, handle: GoalHandle) -> None:
        for line in inv.HANDSHAKE_LINES:
            self.write(line, False)
        self.write("ResetSignalCloseDoor", False)
        self.write("PermissionToClose", True)
        if bool(self.get("GeneralFault")):
            self.write("FaultReset", True)
            self._sleep(0.5, None)
            self.write("FaultReset", False)
            self._sleep(0.5, None)
        self._initialised = False  # re-run the init writes against the fresh state
        self._refresh()

    # ── commands ─────────────────────────────────────────────────────────

    def _reply(self, query, payload: dict) -> None:
        query.reply(str(query.key_expr), encode(payload))

    def _on_stop_door(self, query) -> None:
        serve_query(query, self._do_stop_door, recent=self._recent)

    def _do_stop_door(self, req: Request) -> dict:
        if not self._lease.holds(req.client_id):
            return fail("conflict", "no_control")
        try:
            self.write("PermissionToClose", False)
        except Exception as exc:
            return fail("internal", "write_failed", str(exc))
        return ok_value()

    def read_recipe(self) -> Recipe:
        steps: list[RecipeStep] = []
        for k in range(inv.RECIPE_STEPS):
            steps.append(RecipeStep(
                cleaning=int(self.get(inv.step_display(k, "cleaning")) or 0),
                time_s=int(self.get(inv.step_display(k, "time_s")) or 0),
                movement=int(self.get(inv.step_display(k, "movement")) or 0),
                additional=int(self.get(inv.step_display(k, "additional")) or 0),
                pump_off=bool(self.get(inv.step_display(k, "pump_off"))),
            ))
        params = {name: int(self.get(display) or 0) for name, (display, _i, _t, _s) in inv.RECIPE_PARAMS.items()}
        return Recipe(name=str(self.get(inv.RECIPE_NAME_DISPLAY) or ""), steps=steps, params=params)

    def write_recipe(self, recipe: Recipe) -> None:
        for k in range(inv.RECIPE_STEPS):
            step = recipe.steps[k] if k < len(recipe.steps) else RecipeStep()
            for field in inv.STEP_FIELDS:
                self.write(inv.step_display(k, field), getattr(step, field))
        for name, value in recipe.params.items():
            self.write(inv.RECIPE_PARAMS[name][0], int(value))
        self.write(inv.RECIPE_NAME_DISPLAY, recipe.name)

    def _on_get_recipe(self, query) -> None:
        serve_query(query, self._do_get_recipe)

    def _do_get_recipe(self, req: Request) -> dict:
        try:
            recipe = self.read_recipe()
        except Exception as exc:
            return fail("internal", "read_failed", str(exc))
        return ok_value(RecipeReply(recipe=recipe, schema=inv.RECIPE_SCHEMA).to_wire())

    def _on_set_recipe(self, query) -> None:
        serve_query(query, self._do_set_recipe, recent=self._recent)

    def _do_set_recipe(self, req: Request) -> dict:
        try:
            args = SetRecipe.from_wire(req.args)
        except Exception as exc:
            return fail("invalid", "bad_request", repr(exc))
        if not self._lease.holds(req.client_id):
            return fail("conflict", "no_control")
        err = inv.RECIPE_SCHEMA.validate(args.recipe)
        if err is not None:
            # validate() reports "bad_recipe:<what>"
            return fail("invalid", "bad_recipe", err.removeprefix("bad_recipe:"))
        if self.status.phase == "washing":
            return fail("busy", "washing")
        try:
            self.write_recipe(args.recipe)
        except Exception as exc:
            return fail("internal", "write_failed", str(exc))
        return ok_value()
