"""`tags` contract wire messages + the ``tags:`` cell-config schema.

Cell config::

    tags:
      door_open:    { tag: DoorOpen }                       # by provider tag name (inventory)
      load_request: { node: "ns=4;i=118", type: bool, access: rw }   # by explicit address
      wash_program: { tag: WashProgram, type: int, access: rw }

``type`` in bool/int/float/string; ``access`` in r/rw. Both may be omitted
when the provider's inventory knows the tag (``tag:``); they are required for
raw addresses the provider does not know. Every key other than
type/access/unit is the provider-specific address.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TYPES = ("bool", "int", "float", "string")
ACCESS = ("r", "rw")
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _fail(reason: str) -> ValueError:
    return ValueError(f"bad_tags:{reason}")


def auto_tag_name(display: str) -> str:
    """Controller display name -> channel name: ``ReadyToLoad`` -> ``ready_to_load``,
    ``Programmfolgen[2].BEH`` -> ``programmfolgen_2_beh``, ``ns=4;i=85`` -> ``ns_4_i_85``."""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", display)          # camelCase boundaries
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", s)               # ABCDef -> ABC_Def
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    if not s:
        s = "tag"
    if not s[0].isalpha():
        s = "t_" + s
    return s


@dataclass(frozen=True)
class TagDef:
    name: str
    type: str
    access: str = "r"
    address: dict = field(default_factory=dict)
    unit: str | None = None
    auto: bool = False

    # ChannelDefLike (wf.hal.channels_core)
    @property
    def kind(self) -> str:
        return self.type

    @property
    def writable(self) -> bool:
        return self.access == "rw"

    def default_value(self):
        return {"bool": False, "int": 0, "float": 0.0, "string": ""}[self.type]

    def coerce(self, value):
        t = self.type
        if t == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, int) and value in (0, 1):
                return bool(value)
            raise ValueError(f"bad_value:{self.name} expects a bool")
        if t == "int":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
                raise ValueError(f"bad_value:{self.name} expects an int")
            return int(value)
        if t == "float":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"bad_value:{self.name} expects a number")
            return float(value)
        if not isinstance(value, str):
            raise ValueError(f"bad_value:{self.name} expects a string")
        return value

    def to_engineering(self, raw):
        return self.coerce(raw)

    def to_raw(self, value):
        return value

    def to_wire(self) -> dict:
        d = {"name": self.name, "type": self.type, "access": self.access, "address": dict(self.address)}
        if self.unit is not None:
            d["unit"] = self.unit
        if self.auto:
            d["auto"] = True
        return d


def parse_tags(raw: object) -> dict[str, TagDef]:
    """Validate a cell ``tags:`` mapping into ordered ``{name: TagDef}``.

    A tag given only by ``tag:`` (provider inventory name) may omit
    ``type``/``access``; the provider fills them from its inventory at start.
    Here they default to ``bool``/``r`` when absent so the definition is
    always complete.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _fail("tags must be a mapping")
    out: dict[str, TagDef] = {}
    for name, decl in raw.items():
        if not isinstance(name, str) or not _NAME_RE.match(name):
            raise _fail(f"tag name {name!r} must match [a-z][a-z0-9_]*")
        if not isinstance(decl, dict):
            raise _fail(f"tag {name} must be a mapping")
        typ = decl.get("type", "bool")
        if typ not in TYPES:
            raise _fail(f"tag {name}.type must be one of {TYPES}")
        access = decl.get("access", "r")
        if access not in ACCESS:
            raise _fail(f"tag {name}.access must be one of {ACCESS}")
        unit = decl.get("unit")
        if unit is not None and not isinstance(unit, str):
            raise _fail(f"tag {name}.unit must be a string")
        address = {k: v for k, v in decl.items() if k not in ("type", "access", "unit")}
        if not address:
            raise _fail(f"tag {name} needs an address (tag: <inventory name> or e.g. node: ...)")
        out[name] = TagDef(name=name, type=typ, access=access, address=address, unit=unit)
    return out


@dataclass
class TagValue:
    type: str
    value: object
    access: str = "r"
    forced: bool = False
    address: dict = field(default_factory=dict)
    auto: bool = False

    def to_wire(self) -> dict:
        d = {"type": self.type, "value": self.value, "access": self.access, "forced": bool(self.forced)}
        if self.address:
            d["address"] = dict(self.address)
        if self.auto:
            d["auto"] = True
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "TagValue":
        return cls(type=d["type"], value=d["value"], access=d.get("access", "r"),
                   forced=bool(d.get("forced", False)), address=dict(d.get("address") or {}),
                   auto=bool(d.get("auto", False)))


@dataclass
class TagsState:
    t: int
    tags: dict[str, TagValue] = field(default_factory=dict)

    def to_wire(self) -> dict:
        return {"t": int(self.t), "tags": {n: v.to_wire() for n, v in self.tags.items()}}

    @classmethod
    def from_wire(cls, d: dict) -> "TagsState":
        return cls(t=int(d["t"]), tags={n: TagValue.from_wire(v) for n, v in (d.get("tags") or {}).items()})


@dataclass
class WriteTag:
    """``cmd/write`` envelope ``args`` — the acting ``client_id`` travels
    top-level in the envelope request (wire-contract RFC §4.1)."""

    tag: str
    value: object

    def to_wire(self) -> dict:
        return {"tag": self.tag, "value": self.value}

    @classmethod
    def from_wire(cls, d: dict) -> "WriteTag":
        return cls(tag=d["tag"], value=d["value"])


@dataclass
class ForceTag:
    """``cmd/force`` envelope ``args``; ``value: None`` clears the force."""

    tag: str
    value: object  # None clears

    def to_wire(self) -> dict:
        return {"tag": self.tag, "value": self.value}

    @classmethod
    def from_wire(cls, d: dict) -> "ForceTag":
        return cls(tag=d["tag"], value=d.get("value"))


#: Registered envelope error ``reason`` values (wire-contract RFC §5).
ERROR_REASONS = (
    "bad_request",
    "unknown_channel",
    "no_control",
    "read_only",
    "forced",
    "bad_value",
    "write_failed",
)
