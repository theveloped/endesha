"""Unit tests for the supervisor's node-editor doc endpoints (_doc_reply /
_save_reply): validate + persist an authored graph as a repo file and read it
back. Built on a bare service instance wired with only the attributes these
methods touch (no bus / no child processes)."""

from __future__ import annotations

import threading

import yaml

from wf.services.supervisor.service import SupervisorService

_GOOD_GRAPH = {
    "name": "authored_pick",
    "kind": "flow",
    "roles": {"arm": {"contract": "arm"}},
    "nodes": [
        {"id": "s", "type": "start"},
        {"id": "m", "type": "move", "params": {"pose_name": "grasp"}},
    ],
    "edges": [{"from": "s", "to": "m"}],
}


class _FakePub:
    def put(self, *a, **k):
        pass


class _FakeProcs:
    def alive(self, _name):
        return False


def _svc(tmp_path):
    svc = object.__new__(SupervisorService)
    svc.realm = "cell"
    svc._catalog = {}
    svc._flow_files = {}
    svc._errors = {}
    svc.graphs_dir = tmp_path / "graphs" / "flows"
    svc._lock = threading.Lock()
    svc._catalog_pub = _FakePub()
    svc._procs = _FakeProcs()
    svc.cell = {"resources": {"r1": {"contract": "arm"}}, "bindings": {}}
    return svc


def test_save_and_read_roundtrip(tmp_path):
    svc = _svc(tmp_path)
    reply = svc._save_reply("authored_pick", dict(_GOOD_GRAPH))
    assert reply == {"ok": True, "name": "authored_pick"}

    path = svc.graphs_dir / "authored_pick.yaml"
    assert path.exists()
    on_disk = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert on_disk["name"] == "authored_pick"
    assert svc._catalog["authored_pick"]["kind"] == "graph"

    doc_reply = svc._doc_reply("authored_pick")
    assert doc_reply["ok"] is True
    assert doc_reply["kind"] == "graph"
    assert {n["id"] for n in doc_reply["doc"]["nodes"]} == {"s", "m"}


def test_save_forces_name(tmp_path):
    svc = _svc(tmp_path)
    doc = {**_GOOD_GRAPH, "name": "ignored"}
    reply = svc._save_reply("renamed", doc)
    assert reply["ok"] is True
    assert (svc.graphs_dir / "renamed.yaml").exists()
    assert svc._catalog["renamed"]["name"] == "renamed"


def test_save_rejects_invalid_graph(tmp_path):
    svc = _svc(tmp_path)
    bad = {"nodes": [{"id": "a"}]}  # node without a type
    reply = svc._save_reply("broken", bad)
    assert reply["ok"] is False
    assert reply["error"].startswith("bad_graph:")
    assert not (svc.graphs_dir / "broken.yaml").exists()


def test_save_rejects_non_mapping_doc(tmp_path):
    svc = _svc(tmp_path)
    reply = svc._save_reply("x", ["not", "a", "dict"])
    assert reply["ok"] is False
    assert reply["error"].startswith("bad_save:")


def test_save_refuses_to_shadow_a_spec(tmp_path):
    svc = _svc(tmp_path)
    # a legacy spec flow living outside the graphs dir
    svc._flow_files["demo_inspect"] = str(tmp_path / "flows" / "demo_inspect.yaml")
    reply = svc._save_reply("demo_inspect", dict(_GOOD_GRAPH))
    assert reply == {"ok": False, "error": "exists_as_spec:demo_inspect"}


def test_doc_reply_unknown_flow(tmp_path):
    svc = _svc(tmp_path)
    reply = svc._doc_reply("nope")
    assert reply["ok"] is False
    assert reply["error"].startswith("unknown_flow:")
