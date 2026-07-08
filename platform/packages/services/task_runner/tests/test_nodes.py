"""Unit tests for the node vocabulary handlers, driven against a fake Leaves
(no bus). Asserts each node type calls the right Leaves method with params +
data-edge inputs, and that branch steers on its predicate."""

from __future__ import annotations

from wf.services.task_runner.graph import GraphRunner, validate_graph
from wf.services.task_runner.nodes import build_handlers


class FakeLeaves:
    """Records the leaf calls the handlers make; feeds canned detect results."""

    def __init__(self, detections=None):
        self.calls: list[tuple] = []
        self._detections = detections if detections is not None else []
        self._enabled = None

    def move(self, **kw):
        self.calls.append(("move", kw))

    def grip(self, **kw):
        self.calls.append(("grip", kw))

    def _set_do(self, pin, value):
        self.calls.append(("set_do_standard", pin, value))

    def _set_tool_do(self, pin, value):
        self.calls.append(("set_do_tool", pin, value))

    def wait_di(self, pin, *, timeout_s=5.0, level=True):
        self.calls.append(("wait_di", pin, timeout_s, level))
        return {"tripped": True, "elapsed_s": 0.0}

    def enable_pipeline(self, fmt):
        self.calls.append(("enable_pipeline", fmt))
        self._enabled = fmt

    def read_results(self):
        self.calls.append(("read_results",))
        return list(self._detections)


def _run(doc, leaves):
    g = validate_graph(doc)
    GraphRunner(g, build_handlers(leaves)).run()
    return g


def test_move_uses_params():
    leaves = FakeLeaves()
    _run(
        {
            "name": "x",
            "nodes": [
                {
                    "id": "m",
                    "type": "move",
                    "params": {"motion": "movel", "pose_name": "grasp"},
                }
            ],
        },
        leaves,
    )
    kind, kw = leaves.calls[0]
    assert kind == "move"
    assert kw["motion"] == "movel"
    assert kw["pose_name"] == "grasp"


def test_detect_writes_blackboard_frame():
    # A detect node whose output dict is consumed via a data edge (src_key).
    leaves = FakeLeaves(detections=[{"text": "WF-1"}])
    g = validate_graph(
        {
            "name": "x",
            "nodes": [
                {"id": "d", "type": "detect"},
                {"id": "m", "type": "move"},
            ],
            "edges": [
                {"from": "d", "to": "m"},
                {"from": "d.detections", "to": "m.pose", "kind": "data"},
            ],
        }
    )
    runner = GraphRunner(g, build_handlers(leaves))
    bb = runner.run()
    assert bb["d"] == {"detections": [{"text": "WF-1"}]}
    # move received the detections list as its pose input (routing check)
    move_call = next(c for c in leaves.calls if c[0] == "move")
    assert move_call[1]["pose"] == [{"text": "WF-1"}]


def test_grip_close():
    leaves = FakeLeaves()
    _run(
        {"name": "x", "nodes": [{"id": "g", "type": "grip", "params": {"action": "close"}}]},
        leaves,
    )
    assert leaves.calls[0] == ("grip", {"action": "close", "value": None, "pin": 0})


def test_set_do_bank_dispatch():
    leaves = FakeLeaves()
    _run(
        {
            "name": "x",
            "start": "a",
            "nodes": [
                {"id": "a", "type": "set_do", "params": {"bank": "tool", "pin": 1, "value": True}},
                {"id": "b", "type": "set_do", "params": {"pin": 2, "value": False}},
            ],
            "edges": [{"from": "a", "to": "b"}],
        },
        leaves,
    )
    assert leaves.calls == [
        ("set_do_tool", 1, True),
        ("set_do_standard", 2, False),
    ]


def test_wait_di_stores_result():
    leaves = FakeLeaves()
    g = validate_graph(
        {"name": "x", "nodes": [{"id": "w", "type": "wait_di", "params": {"pin": 3}}]}
    )
    bb = GraphRunner(g, build_handlers(leaves)).run()
    assert leaves.calls[0] == ("wait_di", 3, 5.0, True)
    assert bb["w"]["tripped"] is True


def test_vision_start_stop():
    leaves = FakeLeaves()
    _run(
        {
            "name": "x",
            "start": "on",
            "nodes": [
                {"id": "on", "type": "vision.start", "params": {"format": "DataMatrix"}},
                {"id": "off", "type": "vision.stop"},
            ],
            "edges": [{"from": "on", "to": "off"}],
        },
        leaves,
    )
    assert leaves.calls == [
        ("enable_pipeline", "DataMatrix"),
        ("enable_pipeline", False),
    ]


def test_branch_truthy_takes_true_port():
    leaves = FakeLeaves(detections=[{"text": "WF-1"}])
    doc = {
        "name": "x",
        "nodes": [
            {"id": "d", "type": "detect"},
            {"id": "c", "type": "branch", "params": {"input": "d.detections"}},
            {"id": "yes", "type": "grip", "params": {"action": "close"}},
            {"id": "no", "type": "grip", "params": {"action": "open"}},
        ],
        "edges": [
            {"from": "d", "to": "c"},
            {"from": "c", "to": "yes", "port": "true"},
            {"from": "c", "to": "no", "port": "false"},
        ],
    }
    g = validate_graph(doc)
    GraphRunner(g, build_handlers(leaves)).run()
    grip = next(c for c in leaves.calls if c[0] == "grip")
    assert grip[1]["action"] == "close"  # detections non-empty -> true port


def test_branch_empty_takes_false_port():
    leaves = FakeLeaves(detections=[])
    doc = {
        "name": "x",
        "nodes": [
            {"id": "d", "type": "detect"},
            {"id": "c", "type": "branch", "params": {"input": "d.detections"}},
            {"id": "yes", "type": "grip", "params": {"action": "close"}},
            {"id": "no", "type": "grip", "params": {"action": "open"}},
        ],
        "edges": [
            {"from": "d", "to": "c"},
            {"from": "c", "to": "yes", "port": "true"},
            {"from": "c", "to": "no", "port": "false"},
        ],
    }
    g = validate_graph(doc)
    GraphRunner(g, build_handlers(leaves)).run()
    grip = next(c for c in leaves.calls if c[0] == "grip")
    assert grip[1]["action"] == "open"  # empty -> false port
