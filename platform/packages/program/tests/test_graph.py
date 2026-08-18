"""``Program.describe()["graph"]``: states, transitions (event / cond / unless),
triggers and source anchors — on a small program and on the shipped ones."""

from __future__ import annotations

import sys
from pathlib import Path

from wf.program import Program, State, after, on_channel
from wf.program.graph import build_graph

DEPLOY = Path(__file__).resolve().parents[3] / "deploy"


class Tiny(Program):
    """tiny"""

    program_name = "tiny"
    roles = {"io": "dio"}
    triggers = [on_channel("io", "part", event="go"), after(2.0, state="a", event="late")]

    a = State(initial=True)
    b = State()
    c = State(final=True)

    go = a.to(b, cond="ready", unless="blocked") | a.to(c, cond="skip")
    late = a.to(c)
    back = b.to(a)

    def ready(self) -> bool:
        return True

    def blocked(self) -> bool:
        return False

    def skip(self) -> bool:
        return False

    def run_b(self, ctx):
        self.emit("back")

    def on_abort(self, reason: str) -> None: ...


def test_graph_of_a_small_program():
    g = build_graph(Tiny)
    assert [s["id"] for s in g["states"]] == ["a", "b", "c"]
    assert g["states"][0]["initial"] and g["states"][2]["final"] and g["states"][1]["kind"] == "atomic"
    by = {(t["source"], t["target"], t["event"]): t for t in g["transitions"]}
    assert by[("a", "b", "go")]["cond"] == ["ready"] and by[("a", "b", "go")]["unless"] == ["blocked"]
    assert by[("a", "c", "go")]["cond"] == ["skip"]
    assert by[("a", "c", "late")]["cond"] == [] and by[("b", "a", "back")]["internal"] is False
    assert [t["kind"] for t in g["triggers"]] == ["channel", "timer"]
    assert g["triggers"][1]["params"] == {"seconds": 2.0, "state": "a"}
    src = g["source"]
    assert src["class"] is not None
    assert set(src["states"]) == {"a", "b", "c"} and src["states"]["a"] < src["states"]["b"] < src["states"]["c"]
    assert set(src["transitions"]) == {"go", "late", "back"}
    assert set(src["actions"]) == {"b"} and set(src["guards"]) == {"ready", "blocked", "skip"}
    assert "on_abort" in src["hooks"]
    assert Tiny.describe()["graph"] == g


def test_shipped_programs_export_graphs():
    from wf.services.program_runner.discovery import discover  # noqa: PLC0415

    found = {d.entry.name: d.entry for d in discover(DEPLOY / "programs")}
    demo = found["demo_pick"]
    assert demo.error is None
    g = demo.graph
    assert {s["id"] for s in g["states"]} >= {"homing", "waiting", "picking", "placing", "parked", "done"}
    assert any(t["cond"] == ["cycles_left_none"] for t in g["transitions"])
    assert g["source"]["actions"]["picking"] > g["source"]["states"]["picking"] > 0

    found = {d.entry.name: d.entry for d in discover(DEPLOY / "ecoclean" / "programs")}
    cyc = found["ecoclean_cycle"].graph
    assert {t["event"] for t in cyc["transitions"]} >= {"ready", "door_open", "loaded", "skip", "washed", "unloaded", "closed"}


def test_source_anchors_without_sys_modules_registration(tmp_path):
    """A class loaded straight from a file (not registered in sys.modules)
    still gets anchors via the module __file__ fallback."""
    import importlib.util  # noqa: PLC0415

    path = tmp_path / "p.py"
    path.write_text(
        "from wf.program import Program, State\n\nclass P(Program):\n    x = State(initial=True)\n"
        "    y = State(final=True)\n    go = x.to(y)\n\n    def run_x(self, ctx):\n        self.emit('go')\n\nPROGRAM = P\n",
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("p_unregistered", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    assert "p_unregistered" not in sys.modules
    src = build_graph(module.P)["source"]
    assert src["states"] == {"x": 4, "y": 5} and src["transitions"] == {"go": 6} and src["actions"] == {"x": 8}
