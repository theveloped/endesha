"""Importer sink: config-mode + live-mode round-trips and indistinguishability."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from wf.core.cad_object import ObjectDef, instantiate
from wf.tools import scene_import

_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "src" / "wf" / "tools" / "objects" / "calib_board.yaml"
)


def _instantiate_board(instance="b1", parent="world"):
    import yaml

    obj = ObjectDef.from_wire(yaml.safe_load(_MANIFEST.read_text()))
    return instantiate(
        obj, instance=instance, parent_frame=parent,
        xyz=[0.5, 0.0, 0.1], quat=[0, 0, 0, 1],
    )


def _config_service(session):
    import tempfile

    from wf.services.config.service import ConfigService
    from wf.services.config.store import ConfigStore

    tmp = tempfile.mkdtemp()
    svc = ConfigService(session, ConfigStore(tmp))
    svc.start()
    return svc


def test_config_mode_round_trips_through_store():
    zenoh = pytest.importorskip("zenoh")
    from wf.world_model.validate import fetch_frame_tree, fetch_scene

    session = zenoh.open(zenoh.Config())
    svc = _config_service(session)
    try:
        frames, scene = _instantiate_board()
        errors = scene_import.apply(
            frames, scene, session=session, realm="sim", mode="config"
        )
        assert errors == [], errors  # parent-before-child order avoids unknown_parent
        tree = fetch_frame_tree(session)
        # instance root + child frames resolve to world
        assert "b1" in tree.names()
        assert "b1/datum" in tree.names()
        assert "b1/marker/tag0" in tree.names()
        tree.resolve("b1/marker/tag0", "world")  # does not raise
        objs = {o.meta.get("name"): o for o in fetch_scene(session)}
        assert "b1/0" in objs
        assert objs["b1/0"].frame == "b1"
    finally:
        session.close()


def test_live_mode_round_trips_and_matches_config_wire():
    zenoh = pytest.importorskip("zenoh")
    from wf.world_model.frames_live import build_live_tree
    from wf.world_model.scene_live import build_live_scene

    session = zenoh.open(zenoh.Config())
    try:
        live_frames, fsub = build_live_tree(session, "sim")
        live_scene, ssub = build_live_scene(session, "sim")
        try:
            frames, scene = _instantiate_board()
            errors = scene_import.apply(
                frames, scene, session=session, realm="sim", mode="live"
            )
            assert errors == []
            # frames resolve via the live tree
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                if "b1/marker/tag0" in live_frames.snapshot().names():
                    break
                time.sleep(0.02)
            assert "b1/marker/tag0" in live_frames.snapshot().names()
            live_frames.snapshot().resolve("b1/marker/tag0", "world")
            # scene objects listed via the live view
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                names = {o.meta.get("name") for o in live_scene.snapshot()}
                if "b1/0" in names:
                    break
                time.sleep(0.02)
            live_names = {o.meta.get("name"): o for o in live_scene.snapshot()}
            assert "b1/0" in live_names
            # indistinguishability: the live SceneObject wire equals what a
            # config consumer would have seen (same instantiate() output).
            assert live_names["b1/0"].to_wire() == scene["b1/0"].to_wire()
        finally:
            ssub.undeclare()
            fsub.undeclare()
    finally:
        session.close()


def test_cli_cmd_object_imports_into_config():
    zenoh = pytest.importorskip("zenoh")
    from types import SimpleNamespace

    from wf.tools import wfctl
    from wf.world_model.validate import fetch_frame_tree

    session = zenoh.open(zenoh.Config())
    svc = _config_service(session)
    try:
        args = SimpleNamespace(
            manifest=str(_MANIFEST), instance="cli1", frame="world",
            xyz="0,0,0", quat=None, rpy_deg=None, mode="config", realm="sim",
        )
        rc = wfctl.cmd_object(session, args)
        assert rc == 0
        tree = fetch_frame_tree(session)
        assert "cli1" in tree.names()
    finally:
        session.close()
