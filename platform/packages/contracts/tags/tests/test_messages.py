"""tags contract: wire round-trips, schema, auto naming."""

from __future__ import annotations

import pytest

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


@pytest.mark.parametrize(
    "msg",
    [
        TagValue(type="bool", value=True, access="r"),
        TagValue(type="int", value=3, access="rw", forced=True, address={"node": "ns=4;i=1"}, auto=True),
        TagsState(t=1, tags={"a": TagValue("string", "x"), "b": TagValue("float", 1.5, "rw")}),
        WriteTag(client_id="c", tag="load_request", value=True),
        ForceTag(client_id="c", tag="ready", value=None),
        Ack(ok=False, error="read_only"),
    ],
    ids=lambda m: type(m).__name__,
)
def test_round_trip(msg):
    assert type(msg).from_wire(msg.to_wire()) == msg


def test_keys():
    assert keys.state_tags("cell", "plc0") == "cell/tags/plc0/state/tags"
    assert keys.cmd_write("cell", "plc0") == "cell/tags/plc0/cmd/write"
    assert keys.cmd_force("cell", "plc0") == "cell/tags/plc0/cmd/force"


@pytest.mark.parametrize(
    "display, expected",
    [
        ("ReadyToLoad", "ready_to_load"),
        ("DoorOpen", "door_open"),
        ("Programmfolgen[2].BEH", "programmfolgen_2_beh"),
        ("ns=4;i=85", "ns_4_i_85"),
        ("WatchDog1Hz", "watch_dog1_hz"),
        ("stoernummer", "stoernummer"),
        ("2ndValue", "t_2nd_value"),
    ],
)
def test_auto_tag_name(display, expected):
    assert auto_tag_name(display) == expected


def test_parse_tags_and_coercion():
    tags = parse_tags(
        {
            "door_open": {"tag": "DoorOpen"},
            "load_request": {"node": "ns=4;i=118", "type": "bool", "access": "rw"},
            "wash_program": {"tag": "WashProgram", "type": "int", "access": "rw"},
            "temp": {"node": "ns=4;i=200", "type": "float", "unit": "C"},
        }
    )
    assert tags["door_open"].type == "bool" and tags["door_open"].access == "r" and not tags["door_open"].writable
    assert tags["load_request"].writable and tags["load_request"].address == {"node": "ns=4;i=118"}
    assert tags["wash_program"].coerce(3) == 3 and tags["wash_program"].default_value() == 0
    with pytest.raises(ValueError, match="expects an int"):
        tags["wash_program"].coerce(2.5)
    assert tags["temp"].coerce(20) == 20.0 and tags["temp"].unit == "C"
    with pytest.raises(ValueError, match="expects a bool"):
        tags["door_open"].coerce("yes")
    assert TagDef("s", "string").coerce("hi") == "hi"


@pytest.mark.parametrize(
    "raw, reason",
    [
        ([], "must be a mapping"),
        ({"Bad": {"tag": "X"}}, "must match"),
        ({"x": {"tag": "X", "type": "double"}}, "type must be one of"),
        ({"x": {"tag": "X", "access": "w"}}, "access must be one of"),
        ({"x": {"type": "bool"}}, "needs an address"),
    ],
)
def test_parse_tags_rejects(raw, reason):
    with pytest.raises(ValueError, match=reason):
        parse_tags(raw)
