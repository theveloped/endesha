"""dio contract core = the generic :class:`ChannelsCore` + the dio schema.

Everything contract-agnostic (channel table, auto channels for unmapped pins,
force overlay, lease gate, publish-on-change + keepalive, state queryable)
lives in ``wf.hal.channels_core``; this module only binds the dio keys and
messages. ``DioCore``/``DioBackend``/``load_dio_resource`` keep their API.
"""

from __future__ import annotations

from wf.contracts.control.watcher import LeaseWatcher
from wf.contracts.dio import keys
from wf.contracts.dio.messages import (
    Ack,
    ChannelDef,
    ChannelsState,
    ChannelValue,
    ForceChannel,
    SetChannel,
    auto_channel_name,
    parse_channels,
)
from wf.hal.channels_core import ChannelsCore, load_resource_params

from .backend import DioBackend

load_dio_resource = load_resource_params


class DioSchema:
    contract = "dio"
    params_key = "channels"

    key_state = staticmethod(keys.state_channels)
    key_set = staticmethod(keys.cmd_set)
    key_force = staticmethod(keys.cmd_force)
    key_alive = staticmethod(keys.alive)

    @staticmethod
    def parse(raw):
        return parse_channels(raw)

    @staticmethod
    def auto_def(kind: str, address: dict) -> ChannelDef:
        return ChannelDef(name=auto_channel_name(kind, address), kind=kind, address=dict(address), auto=True)

    @staticmethod
    def state_wire(t: int, values) -> dict:
        return ChannelsState(
            t=t,
            channels={
                ch.name: ChannelValue(kind=ch.kind, value=value, forced=forced, address=ch.address, auto=ch.auto)
                for ch, value, forced in values
            },
        ).to_wire()

    @staticmethod
    def parse_set(payload: dict):
        req = SetChannel.from_wire(payload)
        return req.client_id, req.channel, req.value

    @staticmethod
    def parse_force(payload: dict):
        req = ForceChannel.from_wire(payload)
        return req.client_id, req.channel, req.value

    @staticmethod
    def ack_wire(ok: bool, error: str | None) -> dict:
        return Ack(ok=ok, error=error).to_wire()


DIO_SCHEMA = DioSchema()


class DioCore(ChannelsCore):
    def __init__(self, session, realm: str, rid: str, params: dict, backend: DioBackend, *,
                 lease: LeaseWatcher | None = None):
        super().__init__(session, realm, rid, params, backend, DIO_SCHEMA, lease=lease)

    def snapshot(self) -> ChannelsState:
        return ChannelsState.from_wire(self.snapshot_wire())
