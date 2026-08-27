"""The state-machine graph of a ``Program`` class, as data.

Derived from the class at import time (python-statemachine's class-level
``states`` / ``transitions``, our ``triggers``) so a design view can be drawn
without a runner, and the code stays the only source of truth::

    {
      "states": [{"id", "initial", "final", "parent", "kind"}],
      "transitions": [{"id", "source", "target", "event", "cond": [..], "unless": [..], "internal"}],
      "triggers": [{"kind", "event", "params"}],
      "source": {"states": {id: line}, "transitions": {event: line}, "actions": {state: line},
                 "guards": {name: line}, "hooks": {name: line}, "class": line}
    }

Source anchors are best-effort line numbers in the program file (regex over
``inspect.getsourcelines``): ``x = State(...)``, ``ev = a.to(b)``,
``def run_<state>``, ``def <guard>``; a click on a node can jump to them.
"""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path
from typing import Any

_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
_DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_HOOKS = ("on_hold", "on_resume", "on_abort", "on_stop", "on_start", "on_complete", "on_enter_state",
          "on_exit_state", "on_transition")


def _state_kind(state) -> str:
    if getattr(state, "parallel", False) or getattr(state, "is_parallel", False):
        return "parallel"
    if getattr(state, "is_compound", False):
        return "compound"
    return "atomic"


def _all_states(states) -> list:
    """Depth-first walk (parents before children) into compound/parallel
    states; ``cls.states`` only lists the top level."""
    out: list = []
    for st in states:
        out.append(st)
        out.extend(_all_states(getattr(st, "states", None) or ()))
    return out


def build_graph(cls) -> dict[str, Any]:
    states: list[dict] = []
    transitions: list[dict] = []
    walked = _all_states(cls.states)
    for st in walked:
        parent = getattr(st, "parent", None)
        states.append({
            "id": st.id,
            "initial": bool(getattr(st, "initial", False)),
            "final": bool(getattr(st, "final", False)),
            "parent": getattr(parent, "id", None) if parent is not None else None,
            "kind": _state_kind(st),
        })
    for st in walked:
        for tr in st.transitions:
            targets = list(getattr(tr, "targets", None) or [tr.target])
            for tgt in targets:
                # Skip the synthetic eventless edges that enter a compound
                # state's initial child — the child's `initial` flag plus its
                # `parent` already say this.
                if not tr.event and getattr(tgt, "parent", None) is st:
                    continue
                cond: list[str] = []
                unless: list[str] = []
                for spec in getattr(tr, "cond", None) or ():
                    name = str(getattr(spec, "func", None) or getattr(spec, "attr_name", None) or spec)
                    if getattr(spec, "expected_value", True):
                        cond.append(name)
                    else:
                        unless.append(name)
                event = tr.event
                if not isinstance(event, str):
                    event = getattr(event, "id", None) or (str(event) if event is not None else None)
                transitions.append({
                    "id": f"{st.id}->{tgt.id}:{event or ''}:{len(transitions)}",
                    "source": st.id,
                    "target": tgt.id,
                    "event": event,
                    "cond": cond,
                    "unless": unless,
                    "internal": bool(getattr(tr, "internal", False)),
                })
    triggers = [
        {"kind": t.kind, "event": t.event, "params": dict(t.params)}
        for t in getattr(cls, "triggers", None) or ()
    ]
    return {
        "states": states,
        "transitions": transitions,
        "triggers": triggers,
        "source": source_anchors(cls, [s["id"] for s in states], sorted({t["event"] for t in transitions if t["event"]}),
                                 sorted({n for t in transitions for n in t["cond"] + t["unless"]})),
    }


def _class_source(cls) -> tuple[list[str] | None, int]:
    """``(lines, first_lineno)`` of the class body; ``inspect`` first, else the
    module file (a program loaded outside ``sys.modules`` registration)."""
    try:
        return inspect.getsourcelines(cls)
    except (OSError, TypeError):
        pass
    module = sys.modules.get(cls.__module__)
    path = getattr(module, "__file__", None) or getattr(cls, "__source_path__", None)
    if not path:
        return None, 0
    try:
        text = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return None, 0
    head = re.compile(rf"^class\s+{re.escape(cls.__name__)}(?=[\s(:])")
    for i, line in enumerate(text):
        if head.match(line):
            end = len(text)
            for j in range(i + 1, len(text)):
                if text[j].strip() and not text[j][0].isspace():
                    end = j
                    break
            return text[i:end], i + 1
    return None, 0


def source_anchors(cls, state_ids: list[str], event_ids: list[str], guard_names: list[str]) -> dict[str, Any]:
    lines, start = _class_source(cls)
    if lines is None:
        return {"class": None, "states": {}, "transitions": {}, "actions": {}, "guards": {}, "hooks": {}}
    states: dict[str, int] = {}
    transitions: dict[str, int] = {}
    actions: dict[str, int] = {}
    guards: dict[str, int] = {}
    hooks: dict[str, int] = {}
    state_set, event_set, guard_set = set(state_ids), set(event_ids), set(guard_names)
    for offset, line in enumerate(lines):
        lineno = start + offset
        m = _ASSIGN_RE.match(line)
        if m:
            name, rhs = m.group(1), m.group(2)
            if name in state_set and "State(" in rhs and name not in states:
                states[name] = lineno
            elif name in event_set and ".to(" in rhs and name not in transitions:
                transitions[name] = lineno
            continue
        m = _DEF_RE.match(line)
        if m:
            name = m.group(1)
            if name.startswith("run_") and name[4:] in state_set:
                actions.setdefault(name[4:], lineno)
            elif name in guard_set:
                guards.setdefault(name, lineno)
            elif name in _HOOKS:
                hooks.setdefault(name, lineno)
    return {"class": start, "states": states, "transitions": transitions, "actions": actions,
            "guards": guards, "hooks": hooks}
