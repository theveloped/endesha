"""LiveSceneList merge/shadow/drop semantics + runtime-scene bus round-trip."""

from __future__ import annotations

import time

import pytest

from wf.core.scene import SceneObject
from wf.world_model.scene_live import (
    LiveSceneList,
    build_live_scene,
    delete_scene_object,
    publish_scene_object,
)


def _obj(frame="world", size=(0.1, 0.1, 0.1)):
    return SceneObject(
        frame=frame, xyz=[0, 0, 0], quat=[0, 0, 0, 1],
        geometry={"type": "box", "size": list(size)},
    )


_STATIC = {"crate": _obj(size=(1.0, 1.0, 1.0))}


def _names(objs):
    return {o.meta.get("name") or o.geometry["size"][0] for o in objs}


def test_static_only_snapshot():
    live = LiveSceneList(dict(_STATIC))
    snap = live.snapshot()
    assert len(snap) == 1
    assert snap[0].geometry["size"] == [1.0, 1.0, 1.0]


def test_live_shadows_static_of_same_name():
    live = LiveSceneList(dict(_STATIC))
    live.update("crate", _obj(size=(2.0, 2.0, 2.0)))
    snap = live.snapshot()
    assert len(snap) == 1  # shadows, not appends
    assert snap[0].geometry["size"] == [2.0, 2.0, 2.0]


def test_live_update_then_none_removes():
    live = LiveSceneList(dict(_STATIC))
    live.update("box1", _obj())
    assert len(live.snapshot()) == 2
    live.update("box1", None)
    assert len(live.snapshot()) == 1
    # static survives the dynamic removal
    assert live.snapshot()[0].geometry["size"] == [1.0, 1.0, 1.0]


def test_set_static_swaps_config_layer_preserving_dynamic():
    """set_static (used by refresh_static after a config re-fetch) replaces the
    static config layer while the dynamic layer is untouched — a config scene
    edit (e.g. a collision opt-out) lands without a driver restart."""
    live = LiveSceneList(dict(_STATIC))
    live.update("part", _obj(size=(0.2, 0.2, 0.2)))  # dynamic object
    live.set_static({"crate": _obj(size=(3.0, 3.0, 3.0))})  # re-fetched config
    sizes = sorted(o.geometry["size"][0] for o in live.snapshot())
    assert sizes == [0.2, 3.0]  # new static value + preserved dynamic


# ── bus round-trip (in-process peer self-delivery) ──────────────────────────


def _poll(live, name, present, timeout_s=3.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        names = {o.meta.get("name") for o in live.snapshot()}
        if (name in names) == present:
            return True
        time.sleep(0.02)
    return False


def test_bus_round_trip_publish_and_delete():
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    try:
        live, sub = build_live_scene(session, "sim")
        try:
            obj = _obj()
            obj.meta = {"name": "blocker"}
            publish_scene_object(session, "sim", "blocker", obj)
            assert _poll(live, "blocker", True), "publish not delivered"
            delete_scene_object(session, "sim", "blocker")
            assert _poll(live, "blocker", False), "delete not applied"
        finally:
            sub.undeclare()
    finally:
        session.close()
