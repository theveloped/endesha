"""`dio` contract wire messages + the ``channels:`` cell-config schema.

Wire conventions: timestamps int ns; digital values ``bool``; analog values
``float`` (engineering units after the provider's ``scale``/``offset``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

KIND_DI = "di"
KIND_DO = "do"
KIND_AI = "ai"
KIND_AO = "ao"
KINDS = (KIND_DI, KIND_DO, KIND_AI, KIND_AO)
INPUT_KINDS = (KIND_DI, KIND_AI)
OUTPUT_KINDS = (KIND_DO, KIND_AO)
DIGITAL_KINDS = (KIND_DI, KIND_DO)
ANALOG_KINDS = (KIND_AI, KIND_AO)

# Channel names are identifiers so programs can use them as attributes and
# the UI can render them without escaping: ``part_present``, ``clamp_2``.
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _fail(reason: str) -> ValueError:
    return ValueError(f"bad_channels:{reason}")


@dataclass(frozen=True)
class ChannelDef:
    """One declared channel: ``name`` + ``kind`` + provider-specific ``address``
    (bank/pin/index/…), plus optional presentation ``unit`` and analog
    ``scale``/``offset`` (``value = raw * scale + offset``)."""

    name: str
    kind: str
    address: dict = field(default_factory=dict)
    unit: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    # True for a channel the provider synthesized for a physical point nobody
    # named in cell.yaml (raw pin view); False for an operator-named channel.
    auto: bool = False

    @property
    def is_input(self) -> bool:
        return self.kind in INPUT_KINDS

    @property
    def writable(self) -> bool:
        return not self.is_input

    @property
    def is_digital(self) -> bool:
        return self.kind in DIGITAL_KINDS

    def default_value(self):
        return False if self.is_digital else 0.0

    def to_engineering(self, raw):
        """Raw backend value -> engineering units (``raw * scale + offset``)."""
        if self.is_digital:
            return bool(raw)
        return float(raw) * self.scale + self.offset

    def to_raw(self, value):
        if self.is_digital:
            return bool(value)
        return (float(value) - self.offset) / self.scale

    def coerce(self, value):
        """Validate/normalize a value for this channel; raises ValueError."""
        if self.is_digital:
            if isinstance(value, bool):
                return value
            if isinstance(value, int) and value in (0, 1):
                return bool(value)
            raise ValueError(f"bad_value:{self.name} expects a bool")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"bad_value:{self.name} expects a number")
        return float(value)

    def to_wire(self) -> dict:
        d = {"name": self.name, "kind": self.kind, "address": dict(self.address)}
        if self.unit is not None:
            d["unit"] = self.unit
        if self.scale != 1.0:
            d["scale"] = self.scale
        if self.offset != 0.0:
            d["offset"] = self.offset
        if self.auto:
            d["auto"] = True
        return d


def auto_channel_name(kind: str, address: dict) -> str:
    """Deterministic name for an unmapped physical point: ``di3``, ``do7``,
    ``tool_do0``, ``ai1`` — a valid channel name derived from kind + address."""
    if kind not in KINDS:
        raise ValueError(f"bad_kind:{kind}")
    bank = address.get("bank")
    prefix = f"{bank}_" if isinstance(bank, str) and bank not in ("", "standard") else ""
    if "pin" in address:
        return f"{prefix}{kind}{int(address['pin'])}"
    if "index" in address:
        return f"{prefix}{kind}{int(address['index'])}"
    # Fallback: kind + a stable slug of the address values.
    slug = "_".join(str(v) for _, v in sorted(address.items()))
    slug = re.sub(r"[^a-z0-9_]", "_", slug.lower())
    return f"{kind}_{slug}" if slug else kind


def parse_channels(raw: object) -> dict[str, ChannelDef]:
    """Validate a cell ``channels:`` mapping into ordered ``{name: ChannelDef}``.

    Shape::

        channels:
          part_present: { kind: di, bank: standard, pin: 3 }
          clamp:        { kind: do, bank: standard, pin: 0 }
          pressure:     { kind: ai, index: 0, unit: bar, scale: 0.1 }

    Every key other than ``kind``/``unit``/``scale``/``offset`` is the
    provider-specific address and is passed through untouched.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _fail("channels must be a mapping")
    out: dict[str, ChannelDef] = {}
    for name, decl in raw.items():
        if not isinstance(name, str) or not _NAME_RE.match(name):
            raise _fail(f"channel name {name!r} must match [a-z][a-z0-9_]*")
        if not isinstance(decl, dict):
            raise _fail(f"channel {name} must be a mapping")
        kind = decl.get("kind")
        if kind not in KINDS:
            raise _fail(f"channel {name}.kind must be one of {KINDS}")
        unit = decl.get("unit")
        if unit is not None and not isinstance(unit, str):
            raise _fail(f"channel {name}.unit must be a string")
        scale = decl.get("scale", 1.0)
        offset = decl.get("offset", 0.0)
        for label, v in (("scale", scale), ("offset", offset)):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise _fail(f"channel {name}.{label} must be a number")
        if kind in DIGITAL_KINDS and (scale != 1.0 or offset != 0.0):
            raise _fail(f"channel {name}: scale/offset only apply to analog kinds")
        address = {
            k: v for k, v in decl.items() if k not in ("kind", "unit", "scale", "offset")
        }
        out[name] = ChannelDef(
            name=name,
            kind=kind,
            address=address,
            unit=unit,
            scale=float(scale),
            offset=float(offset),
        )
    return out


@dataclass
class ChannelValue:
    """Reported value of one channel. ``forced`` marks an operator override;
    ``address`` is the provider address (bank/pin/index…) so a UI can show raw
    pins; ``auto`` marks a synthesized unmapped-point channel."""

    kind: str
    value: bool | float
    forced: bool = False
    address: dict = field(default_factory=dict)
    auto: bool = False

    def to_wire(self) -> dict:
        d = {"kind": self.kind, "value": self.value, "forced": bool(self.forced)}
        if self.address:
            d["address"] = dict(self.address)
        if self.auto:
            d["auto"] = True
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "ChannelValue":
        return cls(
            kind=d["kind"],
            value=d["value"],
            forced=bool(d.get("forced", False)),
            address=dict(d.get("address") or {}),
            auto=bool(d.get("auto", False)),
        )


@dataclass
class ChannelsState:
    """Payload of ``state/channels`` (latest-wins)."""

    t: int
    channels: dict[str, ChannelValue] = field(default_factory=dict)

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "channels": {name: cv.to_wire() for name, cv in self.channels.items()},
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ChannelsState":
        return cls(
            t=int(d["t"]),
            channels={
                name: ChannelValue.from_wire(v) for name, v in (d.get("channels") or {}).items()
            },
        )


@dataclass
class SetChannel:
    """``cmd/set`` envelope ``args``: write an OUTPUT channel. Lease-guarded —
    the acting ``client_id`` travels top-level in the envelope request
    (wire-contract RFC §4.1), not here."""

    channel: str
    value: bool | float

    def to_wire(self) -> dict:
        return {"channel": self.channel, "value": self.value}

    @classmethod
    def from_wire(cls, d: dict) -> "SetChannel":
        return cls(channel=d["channel"], value=d["value"])


@dataclass
class ForceChannel:
    """``cmd/force`` envelope ``args``: override ANY channel's reported value
    (``value``) or clear the override (``value: null``). Forcing an output is
    lease-guarded; forcing an input is not."""

    channel: str
    value: bool | float | None

    def to_wire(self) -> dict:
        return {"channel": self.channel, "value": self.value}

    @classmethod
    def from_wire(cls, d: dict) -> "ForceChannel":
        return cls(channel=d["channel"], value=d.get("value"))


#: Registered ``reason`` values this contract's providers may emit in the
#: envelope's error branch (wire-contract RFC §5); conformance asserts
#: every emitted error uses one of these.
ERROR_REASONS = (
    "bad_request",
    "unknown_channel",
    "no_control",
    "read_only",
    "forced",
    "bad_value",
    "write_failed",
)
