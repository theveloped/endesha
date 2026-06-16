"""LiveFrameTree merge/drop semantics + dynamic-frame bus round-trip."""

from __future__ import annotations

import time

import numpy as np
import pytest

from wf.core.frametree import DynamicFrameSample, FrameDef, FrameUnknown
from wf.world_model.frames_live import (
    LiveFrameTree,
    build_live_tree,
    delete_dynamic_frame,
    publish_dynamic_frame,
)

_STATIC = {
    "table": FrameDef(parent="world", xyz=[0.6, 0.0, 0.0], quat=[0, 0, 0, 1]),
}


def _sample(xyz, parent="world", t=1):
    return DynamicFrameSample(t=t, parent=parent, xyz=list(xyz), quat=[0, 0, 0, 1])


def test_update_then_snapshot_resolves_posed_transform():
    live = LiveFrameTree(_STATIC)
    live.update("pallet_1", _sample([1.0, 2.0, 3.0]))
    T = live.snapshot().resolve("pallet_1", "world")
    np.testing.assert_allclose(T[:3, 3], [1.0, 2.0, 3.0], atol=1e-12)
    # static frame still resolves
    np.testing.assert_allclose(
        live.snapshot().resolve("table", "world")[:3, 3], [0.6, 0.0, 0.0], atol=1e-12
    )


def test_update_none_removes_frame():
    live = LiveFrameTree(_STATIC)
    live.update("pallet_1", _sample([1.0, 0.0, 0.0]))
    assert "pallet_1" in live.snapshot().names()
    live.update("pallet_1", None)
    with pytest.raises(FrameUnknown):
        live.snapshot().resolve("pallet_1", "world")


def test_unknown_parent_frame_is_dropped_others_resolve():
    live = LiveFrameTree(_STATIC)
    live.update("ghost", _sample([0.0, 0.0, 0.0], parent="missing_parent"))
    live.update("pallet_1", _sample([1.0, 0.0, 0.0]))
    snap = live.snapshot()
    assert "ghost" not in snap.names()
    np.testing.assert_allclose(
        snap.resolve("pallet_1", "world")[:3, 3], [1.0, 0.0, 0.0], atol=1e-12
    )


def test_dropped_frame_resolves_once_parent_appears():
    live = LiveFrameTree(_STATIC)
    live.update("child", _sample([0.1, 0.0, 0.0], parent="pallet_1"))
    assert "child" not in live.snapshot().names()  # parent unknown -> dropped
    live.update("pallet_1", _sample([1.0, 0.0, 0.0]))
    snap = live.snapshot()
    np.testing.assert_allclose(
        snap.resolve("child", "world")[:3, 3], [1.1, 0.0, 0.0], atol=1e-12
    )


def test_latest_wins_out_of_order_updates():
    live = LiveFrameTree(_STATIC)
    live.update("pallet_1", _sample([1.0, 0.0, 0.0], t=10))
    live.update("pallet_1", _sample([5.0, 0.0, 0.0], t=20))
    np.testing.assert_allclose(
        live.snapshot().resolve("pallet_1", "world")[:3, 3],
        [5.0, 0.0, 0.0],
        atol=1e-12,
    )


def test_set_static_swaps_config_layer_preserving_dynamic():
    """set_static (used by refresh_static after a config re-fetch) replaces the
    static config layer while the dynamic layer is untouched — a UI-added frame
    becomes resolvable without dropping live dynamic frames."""
    live = LiveFrameTree(_STATIC)
    live.update("pallet_1", _sample([1.0, 0.0, 0.0]))
    live.set_static(
        {
            **_STATIC,
            "bench": FrameDef(parent="world", xyz=[0.0, 0.7, 0.0], quat=[0, 0, 0, 1]),
        }
    )
    tree = live.snapshot()
    assert tree.resolve("bench", "world")[1, 3] == 0.7  # new static frame
    assert tree.resolve("pallet_1", "world")[0, 3] == 1.0  # dynamic preserved


# ── bus round-trip (in-process peer self-delivery) ──────────────────────────


def _poll_resolves(live, name, timeout_s=3.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if name in live.snapshot().names():
            return True
        time.sleep(0.02)
    return False


def test_bus_round_trip_publish_and_delete():
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    try:
        live, sub = build_live_tree(session, "sim")
        try:
            publish_dynamic_frame(
                session, "sim", "blocker_frame", _sample([1.0, 0.0, 0.0])
            )
            assert _poll_resolves(live, "blocker_frame"), "publish not delivered"
            np.testing.assert_allclose(
                live.snapshot().resolve("blocker_frame", "world")[:3, 3],
                [1.0, 0.0, 0.0],
                atol=1e-12,
            )
            delete_dynamic_frame(session, "sim", "blocker_frame")
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                if "blocker_frame" not in live.snapshot().names():
                    break
                time.sleep(0.02)
            assert "blocker_frame" not in live.snapshot().names(), "delete not applied"
        finally:
            sub.undeclare()
    finally:
        session.close()
