"""PackML unit machine: the operator command graph."""

from __future__ import annotations

import warnings

import pytest

from wf.services.program_runner.unit import UnitMachine

warnings.filterwarnings("ignore", category=DeprecationWarning)


def _run(u: UnitMachine, *events: str) -> str:
    for e in events:
        u.send(e)
    return u.state_id


def test_happy_path_and_reset():
    u = UnitMachine()
    assert u.state_id == "idle"
    assert _run(u, "start") == "starting"
    assert _run(u, "sc") == "execute"
    assert _run(u, "program_complete") == "completing"
    assert _run(u, "sc") == "complete"
    assert _run(u, "reset") == "resetting"
    assert _run(u, "sc") == "idle"


def test_hold_and_suspend_return_to_execute():
    u = UnitMachine()
    _run(u, "start", "sc")
    assert _run(u, "hold", "sc") == "held"
    assert _run(u, "unhold", "sc") == "execute"
    assert _run(u, "suspend", "sc") == "suspended"
    assert _run(u, "unsuspend", "sc") == "execute"


def test_stop_reset_and_abort_clear_reset():
    u = UnitMachine()
    _run(u, "start", "sc")
    assert _run(u, "stop", "sc") == "stopped"
    assert _run(u, "reset", "sc") == "idle"
    _run(u, "start", "sc")
    assert _run(u, "abort", "sc") == "aborted"
    assert not u.accepts("reset")
    assert _run(u, "clear", "sc") == "stopped"
    assert _run(u, "reset", "sc") == "idle"


def test_abort_from_held_and_stopped():
    u = UnitMachine()
    _run(u, "start", "sc", "hold", "sc")
    assert _run(u, "abort", "sc") == "aborted"
    u = UnitMachine()
    _run(u, "start", "sc", "stop", "sc")
    assert _run(u, "abort", "sc") == "aborted"


@pytest.mark.parametrize("state_events, event", [
    ((), "hold"),
    ((), "unhold"),
    (("start", "sc"), "start"),
    (("start", "sc", "hold", "sc"), "hold"),
    (("start", "sc", "abort", "sc"), "reset"),
])
def test_accepts_reflects_graph(state_events, event):
    u = UnitMachine()
    _run(u, *state_events)
    assert not u.accepts(event)
