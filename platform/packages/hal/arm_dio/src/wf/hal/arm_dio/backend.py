"""ArmDioBackend: the arm's IO bank exposed as a dio device — pure bus client.

Subscribes ``arm/{arm}/state/io`` (bit-packed :class:`IoState`) and writes
through ``arm/{arm}/cmd/set_do``. Works over a live *or* simulated arm; the
runtime overlay decides which. Channel addresses::

    di / do : { bank: standard|tool, pin: int }
    ai / ao : { index: int }

Only the standard bank is surfaced by the arm's ``state/io`` (tool DOs are
write-only there), so a tool-bank ``do`` reports the last value written here.
"""

from __future__ import annotations

import threading

from wf.contracts.arm import keys as arm_keys
from wf.contracts.arm.messages import Ack as ArmAck
from wf.contracts.arm.messages import IoState, SetDo
from wf.contracts.dio.messages import ChannelDef
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.hal.dio_core import DioBackend

_log = get_logger("wf.hal.arm_dio")


class ArmDioBackend(DioBackend):
    def __init__(self, params: dict):
        self.arm = params.get("arm")
        if not isinstance(self.arm, str) or not self.arm:
            raise ValueError("bad_params:arm_dio requires params.arm (the arm resource id)")
        self.core = None
        self._lock = threading.Lock()
        self._io: IoState | None = None
        self._tool_do: dict[int, bool] = {}
        self._sub = None

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self, core) -> None:
        self.core = core
        self._sub = core.session.declare_subscriber(
            arm_keys.state_io(core.realm, self.arm), self._on_io
        )
        _log.info("arm_dio up: rid=%s fronting arm=%s", core.rid, self.arm)

    def shutdown(self) -> None:
        if self._sub is not None:
            try:
                self._sub.undeclare()
            except Exception:
                pass
            self._sub = None

    # ── bus ──────────────────────────────────────────────────────────────

    def _on_io(self, sample) -> None:
        try:
            io = IoState.from_wire(decode(sample.payload))
        except Exception as exc:
            _log.warning("io sample decode failed: %r", exc)
            return
        with self._lock:
            self._io = io
        if self.core is not None:
            self.core.notify()

    # ── DioBackend ───────────────────────────────────────────────────────

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
                    continue  # tool DIs are not surfaced by the arm contract
                if io is None:
                    continue
                bits = io.di if ch.kind == "di" else io.do_
                out[name] = bool(bits >> pin & 1)
            else:
                if io is None:
                    continue
                idx = int(addr.get("index", 0))
                vec = io.ai if ch.kind == "ai" else io.ao
                if 0 <= idx < len(vec):
                    out[name] = float(vec[idx])
        return out

    def write(self, channel: ChannelDef, raw) -> None:
        if channel.kind != "do":
            raise ValueError(f"unsupported:{channel.kind} (the arm contract has no cmd/set_ao)")
        bank = channel.address.get("bank", "standard")
        pin = int(channel.address.get("pin", 0))
        req = SetDo(bank=bank, pin=pin, value=bool(raw))
        replies = self.core.session.get(
            arm_keys.cmd_set_do(self.core.realm, self.arm),
            payload=encode(req.to_wire()),
            timeout=3.0,
        )
        for reply in replies:
            if reply.ok is not None:
                ack = ArmAck.from_wire(decode(reply.ok.payload))
                if not ack.ok:
                    raise RuntimeError(ack.error or "set_do failed")
                if bank == "tool":
                    with self._lock:
                        self._tool_do[pin] = bool(raw)
                return
        raise TimeoutError("no reply from arm cmd/set_do")
