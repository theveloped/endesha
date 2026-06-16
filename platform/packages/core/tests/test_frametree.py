"""FrameTree tests: chain math, identity short-circuit, validation errors."""

import numpy as np
import pytest

from wf.core.frames import make_transform, quaternion_to_rotation_matrix
from wf.core.frametree import (
    DynamicFrameSample,
    FrameCycle,
    FrameDef,
    FrameTree,
    FrameUnknown,
)

_QUAT_90Z = [0.0, 0.0, 0.7071067811865476, 0.7071067811865476]


def test_two_stacked_frames_chain_math():
    tree = FrameTree(
        {
            "table": FrameDef(parent="world", xyz=[0.6, 0.0, 0.0], quat=_QUAT_90Z),
            "fixture": FrameDef(parent="table", xyz=[0.1, 0.2, 0.05], quat=[0, 0, 0, 1]),
        }
    )
    expected = make_transform(
        quaternion_to_rotation_matrix(_QUAT_90Z), [0.6, 0.0, 0.0]
    ) @ make_transform(np.eye(3), [0.1, 0.2, 0.05])
    np.testing.assert_allclose(tree.transform_to_root("fixture"), expected, atol=1e-12)
    # resolve against a sibling: T_table<-fixture is just the local offset.
    np.testing.assert_allclose(
        tree.resolve("fixture", "table"),
        make_transform(np.eye(3), [0.1, 0.2, 0.05]),
        atol=1e-12,
    )


def test_resolve_same_frame_identity_on_empty_tree():
    tree = FrameTree({})
    np.testing.assert_allclose(
        tree.resolve("arm/r1/base", "arm/r1/base"), np.eye(4), atol=0
    )


def test_unknown_parent_raises_at_construction():
    with pytest.raises(FrameUnknown) as excinfo:
        FrameTree({"a": FrameDef(parent="nope", xyz=[0, 0, 0], quat=[0, 0, 0, 1])})
    assert excinfo.value.frame == "nope"


def test_two_cycle_raises_at_construction():
    with pytest.raises(FrameCycle):
        FrameTree(
            {
                "a": FrameDef(parent="b", xyz=[0, 0, 0], quat=[0, 0, 0, 1]),
                "b": FrameDef(parent="a", xyz=[0, 0, 0], quat=[0, 0, 0, 1]),
            }
        )


def test_resolve_unknown_target_raises():
    tree = FrameTree(
        {"table": FrameDef(parent="world", xyz=[0.6, 0, 0], quat=[0, 0, 0, 1])}
    )
    with pytest.raises(FrameUnknown) as excinfo:
        tree.resolve("nope", "table")
    assert excinfo.value.frame == "nope"


def test_chain_returns_path_to_root():
    tree = FrameTree(
        {
            "table": FrameDef(parent="world", xyz=[0.6, 0, 0], quat=[0, 0, 0, 1]),
            "fixture": FrameDef(parent="table", xyz=[0.1, 0, 0], quat=[0, 0, 0, 1]),
        }
    )
    assert set(tree.chain("fixture")) == {"fixture", "table"}
    assert tree.chain("world") == {}


def test_from_wire_tolerates_missing_optionals():
    tree = FrameTree.from_wire(
        {"f": {"parent": "world", "xyz": [1, 0, 0], "quat": [0, 0, 0, 1]}}
    )
    np.testing.assert_allclose(
        tree.transform_to_root("f"), make_transform(np.eye(3), [1, 0, 0]), atol=1e-12
    )


# ── dynamic frame sample ───────────────────────────────────────────────────


def test_dynamic_frame_sample_round_trips():
    s = DynamicFrameSample(
        t=123, parent="world", xyz=[0.1, 0.2, 0.3], quat=_QUAT_90Z,
        source="vision", confidence=0.8,
    )
    assert DynamicFrameSample.from_wire(s.to_wire()) == s


def test_dynamic_frame_sample_wire_defaults():
    s = DynamicFrameSample.from_wire(
        {"parent": "world", "xyz": [1, 0, 0], "quat": [0, 0, 0, 1]}
    )
    assert s.source == "vision" and s.confidence == 1.0 and s.t == 0


def test_as_frame_def_resolves_identically_to_static():
    sample = DynamicFrameSample(
        t=5, parent="world", xyz=[0.6, 0.0, 0.0], quat=_QUAT_90Z
    )
    dyn = FrameTree({"pallet_1": sample.as_frame_def()})
    static = FrameTree(
        {"pallet_1": FrameDef(parent="world", xyz=[0.6, 0.0, 0.0], quat=_QUAT_90Z)}
    )
    np.testing.assert_allclose(
        dyn.transform_to_root("pallet_1"),
        static.transform_to_root("pallet_1"),
        atol=1e-12,
    )


def test_dynamic_frame_shadows_static_of_same_name():
    static = FrameDef(parent="world", xyz=[1.0, 0.0, 0.0], quat=[0, 0, 0, 1])
    dynamic = DynamicFrameSample(
        t=1, parent="world", xyz=[2.0, 0.0, 0.0], quat=[0, 0, 0, 1]
    ).as_frame_def()
    merged = FrameTree({**{"pallet_1": static}, **{"pallet_1": dynamic}})
    np.testing.assert_allclose(
        merged.transform_to_root("pallet_1")[:3, 3], [2.0, 0.0, 0.0], atol=1e-12
    )
