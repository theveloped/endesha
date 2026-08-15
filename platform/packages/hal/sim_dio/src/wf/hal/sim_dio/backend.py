"""SimDioBackend: in-memory channel table.

Outputs remember what was written; inputs are driven by the operator via
``cmd/force`` (the core's overlay) or by an optional repeatable ``script``::

    params:
      script:
        loop: true               # restart from t=0 after the last step (default false)
        steps:
          - { at_s: 2.0, set: { part_present: true } }
          - { at_s: 3.5, set: { part_present: false, pressure: 4.2 } }

Script values are RAW (pre scale/offset) and apply to inputs *and* outputs.
"""

from __future__ import annotations

import threading
import time

from wf.contracts.dio.messages import ChannelDef
from wf.core.log import get_logger
from wf.hal.dio_core import DioBackend

_log = get_logger("wf.hal.sim_dio")


def parse_script(raw: object) -> tuple[list[tuple[float, dict]], bool]:
    """Validate ``script`` into ``([(at_s, {name: raw}), ...] sorted, loop)``."""
    if raw is None:
        return [], False
    if not isinstance(raw, dict):
        raise ValueError("bad_script:script must be a mapping")
    loop = bool(raw.get("loop", False))
    steps_in = raw.get("steps")
    if steps_in is None:
        steps_in = []
    if not isinstance(steps_in, list):
        raise ValueError("bad_script:steps must be a list")
    steps: list[tuple[float, dict]] = []
    for i, step in enumerate(steps_in):
        if not isinstance(step, dict):
            raise ValueError(f"bad_script:step {i} must be a mapping")
        at = step.get("at_s")
        if isinstance(at, bool) or not isinstance(at, (int, float)) or at < 0:
            raise ValueError(f"bad_script:step {i}.at_s must be a number >= 0")
        values = step.get("set")
        if values is None:
            values = {}
        if not isinstance(values, dict):
            raise ValueError(f"bad_script:step {i}.set must be a mapping")
        steps.append((float(at), dict(values)))
    steps.sort(key=lambda s: s[0])
    if loop and not steps:
        raise ValueError("bad_script:loop requires at least one step")
    return steps, loop


class SimDioBackend(DioBackend):
    def __init__(self, params: dict):
        self._values: dict[str, bool | float] = {}
        self._lock = threading.Lock()
        self._steps, self._loop = parse_script(params.get("script"))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.core = None

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self, core) -> None:
        self.core = core
        if self._steps:
            self._thread = threading.Thread(
                target=self._script_loop, name="sim-dio-script", daemon=True
            )
            self._thread.start()
        _log.info("sim_dio up: rid=%s script_steps=%d", core.rid, len(self._steps))

    def shutdown(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ── DioBackend ───────────────────────────────────────────────────────

    def read(self) -> dict:
        with self._lock:
            return dict(self._values)

    def write(self, channel: ChannelDef, raw) -> None:
        with self._lock:
            self._values[channel.name] = raw

    # ── testing / scripting hooks ────────────────────────────────────────

    def drive(self, name: str, raw) -> None:
        """Set a raw value from outside (script step / test)."""
        with self._lock:
            self._values[name] = raw
        if self.core is not None:
            self.core.notify()

    def _script_loop(self) -> None:
        while not self._stop.is_set():
            t0 = time.monotonic()
            for at, values in self._steps:
                delay = t0 + at - time.monotonic()
                if delay > 0 and self._stop.wait(delay):
                    return
                for name, raw in values.items():
                    self.drive(name, raw)
            if not self._loop:
                return
