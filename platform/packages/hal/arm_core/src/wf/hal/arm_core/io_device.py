"""The arm's onboard IO bank served as a first-class ``dio`` device — by the
SAME provider process (one HAL per robot, two contracts).

An arm resource may ``provide`` dio devices in cell.yaml::

    r1:
      contract: arm
      provides:
        io0:
          contract: dio
          channels: { part_present: {kind: di, bank: standard, pin: 0}, … }
          layout:   { di: 16, do: 16, tool_do: 4, ai: 0, ao: 0 }   # optional

For each one :class:`~wf.hal.arm_core.core.ArmCore` hosts a
:class:`~wf.hal.dio_core.DioCore` over :class:`ArmIoBackend`, which reads the
values the arm backend last handed to ``core.publish_io`` and writes through
``ArmBackend.set_do`` — no bus hop, and it works identically for the aubo
driver, ``arm_sim`` and ``replay_arm`` (whose DIs are static/recorded, so in
sim they are driven by ``force``).

Addresses: ``di``/``do`` -> ``{bank: standard|tool, pin}``; ``ai``/``ao`` ->
``{index}``. The arm contract's ``state/io`` only carries the standard bank
and tool DOs are write-only, so a tool ``do`` reports the last value written.
"""

from __future__ import annotations

import threading

from wf.contracts.dio.messages import ChannelDef
from wf.hal.dio_core import DioBackend

DEFAULT_LAYOUT = {"di": 16, "do": 16, "tool_do": 4, "ai": 0, "ao": 0}


def parse_layout(raw: object) -> dict[str, int]:
    layout = dict(DEFAULT_LAYOUT)
    if raw is None:
        return layout
    if not isinstance(raw, dict):
        raise ValueError("bad_layout:layout must be a mapping")
    for key, count in raw.items():
        if key not in DEFAULT_LAYOUT:
            raise ValueError(f"bad_layout:unknown key {key!r} (di/do/tool_do/ai/ao)")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"bad_layout:{key} must be a non-negative int")
        layout[key] = count
    return layout


class ArmIoBackend(DioBackend):
    def __init__(self, arm_core, layout: dict | None = None):
        self.arm = arm_core
        self.layout = parse_layout(layout)
        self._lock = threading.Lock()
        self._io: tuple[int, int, list, list] | None = None
        self._tool_do: dict[int, bool] = {}
        self.core = None

    # ── fed by ArmCore.publish_io ────────────────────────────────────────

    def on_io(self, di: int, do_: int, ai, ao) -> None:
        with self._lock:
            self._io = (int(di), int(do_), list(ai), list(ao))
        if self.core is not None:
            self.core.notify()

    # ── DioBackend ───────────────────────────────────────────────────────

    def points(self) -> list[tuple[str, dict]]:
        pts: list[tuple[str, dict]] = []
        pts += [("di", {"bank": "standard", "pin": i}) for i in range(self.layout["di"])]
        pts += [("do", {"bank": "standard", "pin": i}) for i in range(self.layout["do"])]
        pts += [("do", {"bank": "tool", "pin": i}) for i in range(self.layout["tool_do"])]
        pts += [("ai", {"index": i}) for i in range(self.layout["ai"])]
        pts += [("ao", {"index": i}) for i in range(self.layout["ao"])]
        return pts

    def start(self, core) -> None:
        self.core = core

    def shutdown(self) -> None:
        pass

    def read(self) -> dict:
        with self._lock:
            io = self._io
            tool_do = dict(self._tool_do)
        out: dict = {}
        for name, ch in self.core.channels.items():
            addr = ch.address
            if ch.kind in ("di", "do"):
                bank = addr.get("bank", "standard")
                pin = int(addr.get("pin", 0))
                if bank == "tool":
                    if ch.kind == "do" and pin in tool_do:
                        out[name] = tool_do[pin]
                    continue
                if io is None:
                    continue
                bits = io[0] if ch.kind == "di" else io[1]
                out[name] = bool(bits >> pin & 1)
            else:
                if io is None:
                    continue
                idx = int(addr.get("index", 0))
                vec = io[2] if ch.kind == "ai" else io[3]
                if 0 <= idx < len(vec):
                    out[name] = float(vec[idx])
        return out

    def write(self, channel: ChannelDef, raw) -> None:
        if channel.kind != "do":
            raise ValueError(f"unsupported:{channel.kind} (the arm has no analog output command)")
        bank = channel.address.get("bank", "standard")
        pin = int(channel.address.get("pin", 0))
        self.arm.backend.set_do(bank, pin, 1 if raw else 0)
        if bank == "tool":
            with self._lock:
                self._tool_do[pin] = bool(raw)
