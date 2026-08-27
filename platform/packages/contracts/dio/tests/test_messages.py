"""Wire round-trips + channels schema validation for the dio contract."""

from __future__ import annotations

import pytest

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


@pytest.mark.parametrize(
    "msg",
    [
        ChannelValue(kind="di", value=True, forced=False),
        ChannelValue(kind="ai", value=4.2, forced=True),
        ChannelValue(kind="do", value=False, address={"bank": "tool", "pin": 2}, auto=True),
        ChannelsState(t=1, channels={"a": ChannelValue("do", False), "p": ChannelValue("ai", 1.5, True)}),
        SetChannel(client_id="c1", channel="clamp", value=True),
        SetChannel(client_id="c1", channel="valve", value=0.5),
        ForceChannel(client_id="c1", channel="part_present", value=True),
        ForceChannel(client_id="c1", channel="part_present", value=None),
        Ack(ok=True),
        Ack(ok=False, error="no_control"),
    ],
    ids=lambda m: type(m).__name__,
)
def test_round_trip(msg):
    assert type(msg).from_wire(msg.to_wire()) == msg


def test_keys():
    assert keys.state_channels("cell", "io0") == "cell/dio/io0/state/channels"
    assert keys.cmd_set("cell", "io0") == "cell/dio/io0/cmd/set"
    assert keys.cmd_force("cell", "io0") == "cell/dio/io0/cmd/force"
    assert keys.alive("cell", "io0") == "cell/dio/io0/alive"


def test_parse_channels_ok():
    chans = parse_channels(
        {
            "part_present": {"kind": "di", "bank": "standard", "pin": 3},
            "clamp": {"kind": "do", "bank": "tool", "pin": 0},
            "pressure": {"kind": "ai", "index": 0, "unit": "bar", "scale": 0.1, "offset": -1},
        }
    )
    assert list(chans) == ["part_present", "clamp", "pressure"]
    assert chans["part_present"].address == {"bank": "standard", "pin": 3}
    assert chans["part_present"].is_input and chans["part_present"].is_digital
    assert chans["clamp"].is_input is False
    p = chans["pressure"]
    assert (p.unit, p.scale, p.offset) == ("bar", 0.1, -1.0)
    assert p.default_value() == 0.0 and chans["clamp"].default_value() is False


def test_parse_channels_empty():
    assert parse_channels(None) == {}


@pytest.mark.parametrize(
    "raw, reason",
    [
        ([], "channels must be a mapping"),
        ({"Bad-Name": {"kind": "di"}}, "must match"),
        ({"x": "di"}, "must be a mapping"),
        ({"x": {"kind": "relay"}}, "kind must be one of"),
        ({"x": {"kind": "di", "scale": 2}}, "scale/offset only apply to analog"),
        ({"x": {"kind": "ai", "unit": 3}}, "unit must be a string"),
        ({"x": {"kind": "ai", "scale": "big"}}, "scale must be a number"),
    ],
)
def test_parse_channels_rejects(raw, reason):
    with pytest.raises(ValueError, match=reason):
        parse_channels(raw)


def test_coerce():
    di = ChannelDef("a", "di")
    ai = ChannelDef("b", "ai")
    assert di.coerce(True) is True and di.coerce(0) is False
    assert ai.coerce(3) == 3.0
    with pytest.raises(ValueError):
        di.coerce(0.5)
    with pytest.raises(ValueError):
        ai.coerce(True)
    with pytest.raises(ValueError):
        ai.coerce("x")


def test_channel_def_wire_omits_defaults():
    assert ChannelDef("a", "di", {"pin": 1}).to_wire() == {"name": "a", "kind": "di", "address": {"pin": 1}}


@pytest.mark.parametrize(
    "kind, address, expected",
    [
        ("di", {"bank": "standard", "pin": 3}, "di3"),
        ("do", {"pin": 7}, "do7"),
        ("do", {"bank": "tool", "pin": 0}, "tool_do0"),
        ("ai", {"index": 1}, "ai1"),
        ("di", {"node": "ns=2;i=5"}, "di_ns_2_i_5"),
    ],
)
def test_auto_channel_name(kind, address, expected):
    assert auto_channel_name(kind, address) == expected
