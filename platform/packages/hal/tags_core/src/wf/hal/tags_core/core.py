"""``TagsCore`` = :class:`~wf.hal.channels_core.ChannelsCore` + the tags schema.

Name resolution at construction:

- a cell tag with ``tag: <display name>`` takes type/access/address from the
  backend inventory (an explicit ``type``/``access`` in the cell wins);
- a cell tag with a raw address (``node: …``) is used as declared;
- every inventory variable nobody named becomes an ``auto`` tag named after
  the controller's display name (``ReadyToLoad`` -> ``ready_to_load``), so the
  raw controller stays visible — the tags analogue of unmapped pins.
"""

from __future__ import annotations

from wf.contracts.control.watcher import LeaseWatcher
from wf.contracts.tags import keys
from wf.contracts.tags.messages import (
    Ack,
    ForceTag,
    TagDef,
    TagsState,
    TagValue,
    WriteTag,
    auto_tag_name,
    parse_tags,
)
from wf.core.log import get_logger
from wf.hal.channels_core import ChannelsCore, load_resource_params

from .backend import TagsBackend

_log = get_logger("wf.hal.tags_core")

load_tags_resource = load_resource_params


def _addr_key(address: dict) -> tuple:
    return tuple(sorted((str(k), str(v)) for k, v in address.items() if k != "tag"))


def resolve_tags(declared: dict[str, TagDef], inventory: list[TagDef], *, explicit: dict | None = None) -> dict[str, TagDef]:
    """Merge cell-declared tags with the backend inventory (see module doc).
    ``explicit`` is the raw cell mapping, used to know whether type/access
    were given explicitly (they default in ``parse_tags``)."""
    by_display = {inv.name: inv for inv in inventory}
    explicit = explicit or {}
    out: dict[str, TagDef] = {}
    used_addresses: set[tuple] = set()
    for name, td in declared.items():
        display = td.address.get("tag")
        if display is not None:
            inv = by_display.get(display)
            if inv is None:
                raise ValueError(f"bad_tags:tag {name}: unknown inventory tag {display!r}")
            raw = explicit.get(name) or {}
            td = TagDef(
                name=name,
                type=raw.get("type", inv.type),
                access=raw.get("access", inv.access),
                address={"tag": display, **inv.address},
                unit=td.unit,
            )
        out[name] = td
        used_addresses.add(_addr_key(td.address))
    for inv in inventory:
        if _addr_key(inv.address) in used_addresses:
            continue
        auto = auto_tag_name(inv.name)
        if auto in out:
            _log.warning("auto tag %s collides with a declared tag; skipping inventory %s", auto, inv.name)
            continue
        out[auto] = TagDef(name=auto, type=inv.type, access=inv.access,
                           address={"tag": inv.name, **inv.address}, auto=True)
    return out


class TagsSchema:
    contract = "tags"
    params_key = "tags"

    key_state = staticmethod(keys.state_tags)
    key_set = staticmethod(keys.cmd_write)
    key_force = staticmethod(keys.cmd_force)
    key_alive = staticmethod(keys.alive)

    @staticmethod
    def parse(raw):
        # TagsCore hands over an already-resolved table; a raw mapping is
        # parsed for completeness (no inventory resolution then).
        if isinstance(raw, dict) and raw and all(isinstance(v, TagDef) for v in raw.values()):
            return dict(raw)
        return parse_tags(raw)

    @staticmethod
    def auto_def(kind: str, address: dict) -> TagDef:  # unused: inventory-driven
        return TagDef(name=auto_tag_name(str(address.get("tag", "tag"))), type=kind, address=dict(address), auto=True)

    @staticmethod
    def state_wire(t: int, values) -> dict:
        return TagsState(
            t=t,
            tags={
                td.name: TagValue(type=td.type, value=value, access=td.access, forced=forced,
                                  address=td.address, auto=td.auto)
                for td, value, forced in values
            },
        ).to_wire()

    @staticmethod
    def parse_set(payload: dict):
        req = WriteTag.from_wire(payload)
        return req.client_id, req.tag, req.value

    @staticmethod
    def parse_force(payload: dict):
        req = ForceTag.from_wire(payload)
        return req.client_id, req.tag, req.value

    @staticmethod
    def ack_wire(ok: bool, error: str | None) -> dict:
        return Ack(ok=ok, error=error).to_wire()


TAGS_SCHEMA = TagsSchema()


class TagsCore(ChannelsCore):
    def __init__(self, session, realm: str, rid: str, params: dict, backend: TagsBackend, *,
                 lease: LeaseWatcher | None = None, on_change=None):
        declared = parse_tags(params.get("tags"))
        resolved = resolve_tags(declared, backend.inventory(), explicit=params.get("tags") or {})
        super().__init__(session, realm, rid, {**params, "tags": resolved}, backend, TAGS_SCHEMA,
                         lease=lease, on_change=on_change)

    def snapshot(self) -> TagsState:
        return TagsState.from_wire(self.snapshot_wire())
