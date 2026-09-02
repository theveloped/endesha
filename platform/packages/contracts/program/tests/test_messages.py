"""Wire round-trips for the program contract."""

from __future__ import annotations

import pytest

from wf.contracts.program import keys
from wf.contracts.program.messages import (
    Catalog,
    CatalogEntry,
    EventRequest,
    LoadRequest,
    ProgramState,
    TransitionEvent,
)


@pytest.mark.parametrize(
    "msg",
    [
        CatalogEntry(name="pick", roles={"arm": "arm"}, params={"n": 1}, doc="d", path="p.py"),
        CatalogEntry(name="broken", path="b.py", error="ImportError: x"),
        Catalog(t=1, programs=[CatalogEntry(name="a")]),
        LoadRequest(name="pick", bindings={"arm": "r1"}, params={"n": 2}),
        EventRequest(event="go", data={"x": 1}),
        ProgramState(t=1, unit="execute", program="pick", program_states=["waiting"], actions=["waiting"],
                     reason=None, params={"n": 1}, bindings={"arm": "r1"}, client_id="program:pick:ab", cycle=2),
        ProgramState(t=2, unit="idle"),
        TransitionEvent(t=3, scope="unit", source="idle", target="starting", event="start"),
        TransitionEvent(t=4, scope="program", source=None, target="waiting", event="__initial__", detail="x"),
    ],
    ids=lambda m: type(m).__name__,
)
def test_round_trip(msg):
    assert type(msg).from_wire(msg.to_wire()) == msg


def test_keys():
    assert keys.catalog("cell") == "cell/programs/catalog"
    assert keys.cmd_load("cell") == "cell/programs/cmd/load"
    assert keys.state("cell") == "cell/program/state"
    assert keys.cmd("cell", "hold") == "cell/program/cmd/hold"
    assert keys.cmd_event("cell") == "cell/program/cmd/event"
    assert keys.transitions("cell") == "cell/program/transitions"
    with pytest.raises(ValueError):
        keys.cmd("cell", "launch")
