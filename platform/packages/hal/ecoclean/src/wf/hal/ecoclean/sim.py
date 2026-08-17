"""EcocleanSimBackend: the Ecoclean PLC emulated in memory.

A ``sim_tags`` backend pre-loaded with the Ecoclean inventory plus a small
PLC program that answers our handshake lines the way the machine does:

- ``ReadyToLoad`` + ``LoadRequest`` (with ``PermissionToClose``) -> the door
  travels open (``door_travel_s``), then ``DoorOpen``;
- door open + ``LoadComplete`` (permission held) -> the door travels closed,
  ``DoorClosed``, then the cycle runs (``WashingInProgress``) for the sum of
  the recipe step times (or ``wash_time_s``) and ends in ``ReadyToUnload``;
- ``ReadyToUnload`` + ``UnLoadComplete`` -> door opens, then ``ReadyToLoad``;
- door open + ``ResetSignalCloseDoor`` -> the door closes without a cycle;
- dropping ``PermissionToClose`` while the door travels stops it (neither
  ``DoorOpen`` nor ``DoorClosed``) until permission returns;
- ``FaultReset`` clears ``GeneralFault``/``stoernummer`` (inject a fault by
  forcing ``general_fault`` on the tags device, or ``fault_at_s`` below).

``time_scale`` multiplies every duration (0.1 -> ten times faster).

Params::

    door_travel_s: 3.0
    wash_time_s: null       # null = sum of recipe step times (min 2 s)
    time_scale: 1.0
    fault_at_s: null        # inject GeneralFault n seconds into the first cycle
    initial_recipe: {name: "Standard", steps: [...], params: {...}}   # optional
"""

from __future__ import annotations

import threading
import time

from wf.contracts.washer.messages import Recipe
from wf.core.log import get_logger
from wf.hal.sim_tags.backend import SimTagsBackend

from . import inventory as inv

_log = get_logger("wf.hal.ecoclean.sim")

_TICK_S = 0.05


class EcocleanSimBackend(SimTagsBackend):
    def __init__(self, params: dict):
        super().__init__({**params, "inventory": inv.inventory_dict(), "script": None})
        self.time_scale = float(params.get("time_scale", 1.0))
        self.door_travel_s = float(params.get("door_travel_s", 3.0))
        self.wash_time_s = params.get("wash_time_s")
        self.fault_at_s = params.get("fault_at_s")
        self._plc_stop = threading.Event()
        self._plc_thread: threading.Thread | None = None
        # PLC internals
        self._door_pos = 0.0  # 0 closed .. 1 open
        self._door_target = 0.0
        self._wash_pending = False
        self._wash_left = 0.0
        self._cycles = 0
        self._prev: dict[str, object] = {}
        # defaults: door closed, machine ready, auto
        for display, decl in inv.inventory_dict().items():
            self._values.setdefault(display, {"bool": False, "int": 0, "float": 0.0, "string": ""}[decl["type"]])
        self._values.update({"DoorClosed": True, "ReadyToLoad": True, "Auto": True, "PermissionToClose": False})
        initial = params.get("initial_recipe")
        if initial:
            self.load_recipe(Recipe.from_wire(initial))
        elif not self._values.get("Kommentar"):
            self._values["Kommentar"] = "Standard"
            self._values["Programmfolgen[0].BEH"] = 1
            self._values["Programmfolgen[0].ZEIT"] = 60
            self._values["Programmfolgen[1].BEH"] = 2
            self._values["Programmfolgen[1].ZEIT"] = 30
            self._values["UPM"] = 4

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self, core) -> None:
        super().start(core)
        self._plc_thread = threading.Thread(target=self._plc_loop, name="ecoclean-sim-plc", daemon=True)
        self._plc_thread.start()

    def shutdown(self) -> None:
        self._plc_stop.set()
        if self._plc_thread is not None:
            self._plc_thread.join(timeout=2.0)
            self._plc_thread = None
        super().shutdown()

    # ── helpers ──────────────────────────────────────────────────────────

    def load_recipe(self, recipe: Recipe) -> None:
        with self._lock:
            self._values["Kommentar"] = recipe.name
            for k in range(inv.RECIPE_STEPS):
                step = recipe.steps[k] if k < len(recipe.steps) else None
                for field in inv.STEP_FIELDS:
                    default = False if field == "pump_off" else 0
                    self._values[inv.step_display(k, field)] = getattr(step, field) if step else default
            for name, value in recipe.params.items():
                display = inv.RECIPE_PARAMS[name][0]
                self._values[display] = int(value)

    def _get(self, display: str):
        with self._lock:
            return self._values.get(display)

    def _set(self, display: str, value) -> None:
        with self._lock:
            if self._values.get(display) == value:
                return
            self._values[display] = value
        if self.core is not None:
            self.core.notify()

    def _rising(self, display: str) -> bool:
        cur = bool(self._get(display))
        was = bool(self._prev.get(display, False))
        self._prev[display] = cur
        return cur and not was

    def _cycle_time_s(self) -> float:
        if self.wash_time_s is not None:
            return float(self.wash_time_s)
        total = 0
        for k in range(inv.RECIPE_STEPS):
            if int(self._get(inv.step_display(k, "cleaning")) or 0) > 0:
                total += int(self._get(inv.step_display(k, "time_s")) or 0)
        return float(max(total, 2))

    # ── the PLC program ──────────────────────────────────────────────────

    def _plc_loop(self) -> None:
        t_last = time.monotonic()
        wd = False
        wd_last = t_last
        while not self._plc_stop.wait(_TICK_S):
            now = time.monotonic()
            dt = (now - t_last) / max(self.time_scale, 1e-6)
            t_last = now
            if now - wd_last >= 0.5:
                wd = not wd
                wd_last = now
                self._set("WatchDog1Hz", wd)
            self._step(dt)

    def _step(self, dt: float) -> None:
        permission = bool(self._get("PermissionToClose"))
        door_open = self._door_pos >= 1.0
        door_closed = self._door_pos <= 0.0
        ready_to_load = bool(self._get("ReadyToLoad"))
        ready_to_unload = bool(self._get("ReadyToUnload"))
        washing = bool(self._get("WashingInProgress"))
        fault = bool(self._get("GeneralFault"))

        load_request = self._rising("LoadRequest")
        load_complete = self._rising("LoadComplete")
        unload_complete = self._rising("UnLoadComplete")
        close_signal = self._rising("ResetSignalCloseDoor")
        fault_reset = self._rising("FaultReset")

        if fault_reset and fault:
            self._set("GeneralFault", False)
            self._set("stoernummer", 0)
            fault = False

        if fault:
            self._door_target = self._door_pos  # everything freezes
            return

        # requests
        # edge-triggered like the PLC: a LoadRequest still high after a close
        # does not re-open the door
        if door_closed and ready_to_load and not washing and load_request:
            self._door_target = 1.0
        if door_closed and ready_to_unload and unload_complete:
            self._door_target = 1.0
        if door_open and permission and load_complete:
            self._door_target = 0.0
            self._wash_pending = True
        if door_open and permission and close_signal:
            self._door_target = 0.0
            self._wash_pending = False

        # door travel (only with permission)
        if self._door_pos != self._door_target and permission:
            speed = 1.0 / max(self.door_travel_s, 1e-3)
            if self._door_target > self._door_pos:
                self._door_pos = min(1.0, self._door_pos + speed * dt)
            else:
                self._door_pos = max(0.0, self._door_pos - speed * dt)
        door_open = self._door_pos >= 1.0
        door_closed = self._door_pos <= 0.0
        self._set("DoorOpen", door_open)
        self._set("DoorClosed", door_closed)

        # arriving open after an unload: back to ready-to-load
        if door_open and ready_to_unload:
            self._set("ReadyToUnload", False)
            self._set("ReadyToLoad", True)
        # arriving closed with a load: run the cycle
        if door_closed and self._wash_pending and not washing:
            self._wash_pending = False
            self._wash_left = self._cycle_time_s()
            self._cycles += 1
            self._set("ReadyToLoad", False)
            self._set("WashingInProgress", True)
            washing = True
        if washing:
            self._wash_left -= dt
            if self.fault_at_s is not None and self._cycles == 1 and self._wash_left <= self._cycle_time_s() - float(self.fault_at_s):
                self.fault_at_s = None
                self._set("GeneralFault", True)
                self._set("stoernummer", 42)
                self._set("WashingInProgress", False)
                return
            if self._wash_left <= 0:
                self._set("WashingInProgress", False)
                self._set("ReadyToUnload", True)
