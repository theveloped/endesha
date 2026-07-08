"""Unit tests for the supervisor's flow-descriptor normalization: legacy specs
and node graphs collapse to a uniform {name, roles, kind, vision_pipelines}
shape the catalog / role resolution / vision-runtime discovery consume."""

from __future__ import annotations

from wf.services.supervisor.service import _describe_flow
from wf.services.task_runner.spec import validate_graph, validate_spec


def test_describe_legacy_spec():
    spec = validate_spec(
        {
            "name": "demo_inspect",
            "poses": ["a", "b"],
            "vision": {"format": "DataMatrix", "pipeline": "demo_detect"},
        }
    )
    desc = _describe_flow(spec)
    assert desc["name"] == "demo_inspect"
    assert desc["kind"] == "spec"
    assert desc["vision_pipelines"] == [("demo_detect", "DataMatrix")]
    assert desc["roles"] == {"arm": {"contract": "arm"}, "cam": {"contract": "camera2d"}}


def test_describe_arm_only_graph():
    graph = validate_graph(
        {
            "name": "demo_pick",
            "roles": {"arm": {"contract": "arm"}},
            "nodes": [
                {"id": "s", "type": "start"},
                {"id": "m", "type": "move", "params": {"pose_name": "grasp"}},
            ],
            "edges": [{"from": "s", "to": "m"}],
        }
    )
    desc = _describe_flow(graph)
    assert desc["name"] == "demo_pick"
    assert desc["kind"] == "graph"
    assert desc["vision_pipelines"] == []  # no camera / vision
    assert desc["roles"] == {"arm": {"contract": "arm"}}


def test_describe_graph_with_vision():
    graph = validate_graph(
        {
            "name": "vguided",
            "nodes": [
                {
                    "id": "v",
                    "type": "vision.start",
                    "params": {"pipeline": "parts_detect", "format": "QRCode"},
                },
                {"id": "d", "type": "detect"},
                {"id": "off", "type": "vision.stop"},
            ],
            "edges": [{"from": "v", "to": "d"}, {"from": "d", "to": "off"}],
        }
    )
    desc = _describe_flow(graph)
    assert desc["vision_pipelines"] == [("parts_detect", "QRCode")]


def test_describe_graph_vision_defaults_pipeline():
    graph = validate_graph(
        {
            "name": "vg2",
            "nodes": [{"id": "v", "type": "vision.start"}],
        }
    )
    desc = _describe_flow(graph)
    assert desc["vision_pipelines"] == [("vg2_detect", "Any")]
