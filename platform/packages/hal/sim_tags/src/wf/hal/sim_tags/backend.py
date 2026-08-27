"""SimTagsBackend: in-memory variables.

``params.inventory`` declares the simulated controller's variables (the raw
view — same shape a live provider would discover)::

    inventory:
      ReadyToLoad: { type: bool, access: r,  node: "ns=4;i=85" }
      LoadRequest: { type: bool, access: rw, node: "ns=4;i=118" }
      WashProgram: { type: int,  access: rw, node: "ns=4;i=134" }

Writable variables remember what was written; read-only ones are driven by
``cmd/force`` or an optional ``script`` (same shape as sim_dio:
``{steps: [{at_s, set: {Display: value}}], loop}``, values keyed by
inventory display name).
"""

from __future__ import annotations

import threading
import time

from wf.contracts.tags.messages import ACCESS, TYPES, TagDef
from wf.core.log import get_logger
from wf.hal.tags_core import TagsBackend

_log = get_logger("wf.hal.sim_tags")


def parse_inventory(raw: object) -> list[TagDef]:
    if raw is None:
        return []
    if not isinstance(raw, dict):
        raise ValueError("bad_inventory:inventory must be a mapping")
    out: list[TagDef] = []
    for display, decl in raw.items():
        if not isinstance(display, str) or not display:
            raise ValueError("bad_inventory:tag display name must be a non-empty string")
        if not isinstance(decl, dict):
            raise ValueError(f"bad_inventory:{display} must be a mapping")
        typ = decl.get("type", "bool")
        if typ not in TYPES:
            raise ValueError(f"bad_inventory:{display}.type must be one of {TYPES}")
        access = decl.get("access", "r")
        if access not in ACCESS:
            raise ValueError(f"bad_inventory:{display}.access must be one of {ACCESS}")
        address = {k: v for k, v in decl.items() if k not in ("type", "access", "unit")}
        out.append(TagDef(name=display, type=typ, access=access, address=address, unit=decl.get("unit")))
    return out


def parse_script(raw: object) -> tuple[list[tuple[float, dict]], bool]:
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
    return steps, loop


class SimTagsBackend(TagsBackend):
    def __init__(self, params: dict):
        self._inventory = parse_inventory(params.get("inventory"))
        self._values: dict[str, object] = {}  # keyed by DISPLAY name
        self._lock = threading.Lock()
        self._steps, self._loop = parse_script(params.get("script"))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.core = None
        self._display_of: dict[str, str] = {}  # channel name -> display name

    def inventory(self) -> list[TagDef]:
        return list(self._inventory)

    def start(self, core) -> None:
        self.core = core
        # channel name -> display name (all resolved tags carry address["tag"])
        self._display_of = {name: str(td.address.get("tag", name)) for name, td in core.channels.items()}
        if self._steps:
            self._thread = threading.Thread(target=self._script_loop, name="sim-tags-script", daemon=True)
            self._thread.start()
        _log.info("sim_tags up: rid=%s inventory=%d script_steps=%d", core.rid, len(self._inventory), len(self._steps))

    def shutdown(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def read(self) -> dict:
        with self._lock:
            values = dict(self._values)
        return {name: values[disp] for name, disp in self._display_of.items() if disp in values}

    def write(self, channel, raw) -> None:
        with self._lock:
            self._values[str(channel.address.get("tag", channel.name))] = raw

    def drive(self, display: str, raw) -> None:
        """Set a raw value by inventory display name (script / tests)."""
        with self._lock:
            self._values[display] = raw
        if self.core is not None:
            self.core.notify()

    def _script_loop(self) -> None:
        while not self._stop.is_set():
            t0 = time.monotonic()
            for at, values in self._steps:
                delay = t0 + at - time.monotonic()
                if delay > 0 and self._stop.wait(delay):
                    return
                for display, raw in values.items():
                    self.drive(display, raw)
            if not self._loop:
                return
