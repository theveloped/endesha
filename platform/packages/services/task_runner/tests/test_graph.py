"""Unit tests for the node-graph doc model, control-flow interpreter, and the
motion waypoint builder (no bus — handlers are fakes)."""

from __future__ import annotations

import pytest

from wf.contracts.arm.messages import Freedom, Pose
from wf.services.task_runner.graph import (
    Aborted,
    DEFAULT_PORT,
    GraphError,
    GraphRunner,
    is_graph_doc,
    validate_graph,
)
from wf.services.task_runner.leaves import build_move_waypoint

# ── doc detection ──────────────────────────────────────────────────────────


def test_is_graph_doc():
    assert is_graph_doc({"name": "x", "nodes": []})
    assert not is_graph_doc({"name": "x", "poses": ["a"]})
    assert not is_graph_doc("nope")


# ── validation ─────────────────────────────────────────────────────────────

_SEQ = {
    "name": "pick",
    "nodes": [
        {"id": "s", "type": "start"},
        {"id": "a", "type": "move", "params": {"pose_name": "grasp"}},
        {"id": "b", "type": "grip", "params": {"action": "close"}},
    ],
    "edges": [
        {"from": "s", "to": "a"},
        {"from": "a", "to": "b"},
    ],
}


def test_validate_sequence():
    g = validate_graph(dict(_SEQ))
    assert g.name == "pick"
    assert g.kind == "flow"
    assert set(g.nodes) == {"s", "a", "b"}
    assert g.start == "s"  # single type:start node
    assert g.roles == {"arm": {"contract": "arm"}, "cam": {"contract": "camera2d"}}
    assert g.nodes["a"].params == {"pose_name": "grasp"}


def test_start_explicit_wins():
    doc = {
        "name": "x",
        "start": "b",
        "nodes": [{"id": "a", "type": "move"}, {"id": "b", "type": "move"}],
        "edges": [{"from": "a", "to": "b"}],
    }
    assert validate_graph(doc).start == "b"


def test_start_unique_root():
    doc = {
        "name": "x",
        "nodes": [{"id": "a", "type": "move"}, {"id": "b", "type": "grip"}],
        "edges": [{"from": "a", "to": "b"}],
    }
    assert validate_graph(doc).start == "a"  # b has an incoming exec edge


def test_data_edge_parsed():
    doc = {
        "name": "x",
        "nodes": [{"id": "d", "type": "detect"}, {"id": "m", "type": "move"}],
        "edges": [
            {"from": "d", "to": "m"},
            {"from": "d.detections", "to": "m.frame", "kind": "data"},
        ],
    }
    g = validate_graph(doc)
    data = g.data_edges_into("m")
    assert len(data) == 1
    assert (data[0].src, data[0].src_key, data[0].dst_key) == ("d", "detections", "frame")


def test_roles_override():
    doc = {
        "name": "x",
        "roles": {"arm": {"contract": "arm"}},
        "nodes": [{"id": "a", "type": "move"}],
    }
    assert validate_graph(doc).roles == {"arm": {"contract": "arm"}}


@pytest.mark.parametrize(
    "bad",
    [
        {"nodes": [{"id": "a", "type": "move"}]},  # no name
        {"name": "a b", "nodes": [{"id": "a", "type": "move"}]},  # ws in name
        {"name": "x", "kind": "weird", "nodes": [{"id": "a", "type": "move"}]},
        {"name": "x", "nodes": []},  # empty nodes
        {"name": "x", "nodes": [{"id": "a"}]},  # node without type
        {"name": "x", "nodes": [{"type": "move"}]},  # node without id
        {"name": "x", "nodes": [{"id": "a", "type": "m"}, {"id": "a", "type": "m"}]},
        {  # edge to unknown node
            "name": "x",
            "nodes": [{"id": "a", "type": "move"}],
            "edges": [{"from": "a", "to": "ghost"}],
        },
        {  # two start nodes, no explicit start
            "name": "x",
            "nodes": [{"id": "a", "type": "start"}, {"id": "b", "type": "start"}],
        },
    ],
)
def test_validate_rejects(bad):
    with pytest.raises(ValueError) as exc:
        validate_graph(bad)
    assert str(exc.value).startswith("bad_graph:")


# ── interpreter ────────────────────────────────────────────────────────────


def _recording_handlers(calls, ports=None):
    ports = ports or {}

    def make(kind):
        def handler(node, bb, graph):
            calls.append(node.id)
            return ports.get(node.id)

        return handler

    return {t: make(t) for t in ("start", "move", "grip", "detect", "branch", "end")}


def test_runner_walks_sequence_in_order():
    g = validate_graph(dict(_SEQ))
    calls: list[str] = []
    runner = GraphRunner(g, _recording_handlers(calls))
    runner.run()
    assert calls == ["s", "a", "b"]
    assert runner.trace == ["s", "a", "b"]


def test_runner_follows_branch_port():
    doc = {
        "name": "x",
        "start": "c",
        "nodes": [
            {"id": "c", "type": "branch"},
            {"id": "yes", "type": "move"},
            {"id": "no", "type": "grip"},
        ],
        "edges": [
            {"from": "c", "to": "yes", "port": "true"},
            {"from": "c", "to": "no", "port": "false"},
        ],
    }
    g = validate_graph(doc)
    calls: list[str] = []
    runner = GraphRunner(g, _recording_handlers(calls, ports={"c": "false"}))
    runner.run()
    assert calls == ["c", "no"]


def test_runner_threads_blackboard():
    doc = {
        "name": "x",
        "nodes": [{"id": "d", "type": "detect"}, {"id": "m", "type": "move"}],
        "edges": [{"from": "d", "to": "m"}],
    }
    g = validate_graph(doc)
    seen = {}

    def detect(node, bb, graph):
        bb[node.id] = {"count": 3}
        return None

    def move(node, bb, graph):
        seen["from_upstream"] = bb["d"]["count"]
        return None

    GraphRunner(g, {"detect": detect, "move": move}).run()
    assert seen == {"from_upstream": 3}


def test_runner_abort_between_nodes():
    g = validate_graph(dict(_SEQ))
    calls: list[str] = []
    flag = {"abort": False}

    def handler(node, bb, graph):
        calls.append(node.id)
        flag["abort"] = True  # abort after the first node
        return None

    runner = GraphRunner(
        g,
        {t: handler for t in ("start", "move", "grip")},
        is_aborted=lambda: flag["abort"],
    )
    with pytest.raises(Aborted):
        runner.run()
    assert calls == ["s"]


def test_runner_missing_handler_raises():
    g = validate_graph(dict(_SEQ))
    with pytest.raises(GraphError):
        GraphRunner(g, {"start": lambda *a: None}).run()


def test_runner_ambiguous_exec_raises():
    doc = {
        "name": "x",
        "start": "a",
        "nodes": [
            {"id": "a", "type": "move"},
            {"id": "b", "type": "move"},
            {"id": "c", "type": "move"},
        ],
        "edges": [{"from": "a", "to": "b"}, {"from": "a", "to": "c"}],
    }
    g = validate_graph(doc)
    with pytest.raises(GraphError):
        GraphRunner(g, {"move": lambda *a: DEFAULT_PORT}).run()


def test_runner_step_limit():
    doc = {
        "name": "x",
        "start": "a",
        "nodes": [{"id": "a", "type": "move"}, {"id": "b", "type": "move"}],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}],
    }
    g = validate_graph(doc)
    runner = GraphRunner(g, {"move": lambda *a: None}, max_steps=10)
    with pytest.raises(GraphError):
        runner.run()


# ── waypoint builder ───────────────────────────────────────────────────────


def test_build_movej_joint():
    wp = build_move_waypoint(motion="movej", q=[0, 1, 2, 3, 4, 5])
    assert wp.type == "movej"
    assert wp.target == {"q": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]}


def test_build_movel_pose():
    pose = Pose(frame="arm/r1/base", xyz=[0.1, 0.2, 0.3], quat=[0, 0, 0, 1])
    wp = build_move_waypoint(motion="movel", pose=pose)
    assert wp.type == "movel"
    assert wp.target["pose"]["frame"] == "arm/r1/base"
    assert "free" not in wp.target


def test_build_pose_with_free():
    pose = Pose(frame="tag", xyz=[0, 0, 0], quat=[0, 0, 0, 1])
    wp = build_move_waypoint(motion="movej", pose=pose, free=Freedom(dof="yaw"))
    assert wp.target["free"]["dof"] == "yaw"
    assert wp.target["free"]["frame"] == "reference"


def test_build_rejects_both_and_neither():
    with pytest.raises(Exception):
        build_move_waypoint(motion="movej")
    with pytest.raises(Exception):
        build_move_waypoint(motion="movej", q=[0] * 6, pose={"frame": "f"})


def test_build_rejects_free_with_joint():
    with pytest.raises(Exception):
        build_move_waypoint(motion="movej", q=[0] * 6, free=Freedom(dof="yaw"))


def test_build_rejects_bad_motion():
    with pytest.raises(Exception):
        build_move_waypoint(motion="movec", q=[0] * 6)
