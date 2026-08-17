"""Declarative event sources a program lists in ``triggers = [...]``.

The runner evaluates them (not user code) and injects the named event into
the program while the unit is executing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

EDGES = ("rising", "falling", "change")


@dataclass(frozen=True)
class Trigger:
    kind: str  # "channel" | "timer"
    event: str
    params: dict = field(default_factory=dict)


def on_channel(role: str, channel: str, *, edge: str = "rising", event: str) -> Trigger:
    """Emit ``event`` when ``role``'s channel/tag ``channel`` shows ``edge``
    (``rising`` False->True, ``falling`` True->False, ``change`` any). Works for
    dio channels and PLC tags alike (any table-shaped device)."""
    if edge not in EDGES:
        raise ValueError(f"edge must be one of {EDGES}")
    return Trigger("channel", event, {"role": role, "channel": channel, "edge": edge})


def after(seconds: float, *, state: str, event: str) -> Trigger:
    """Emit ``event`` ``seconds`` after ``state`` was entered (cancelled when
    the state is left first) — a per-state timeout/dwell."""
    if seconds <= 0:
        raise ValueError("seconds must be > 0")
    return Trigger("timer", event, {"seconds": float(seconds), "state": state})
