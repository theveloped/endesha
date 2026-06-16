"""ObjectDef validation/round-trip + instantiate frame/scene expansion."""

from __future__ import annotations

import pytest

from wf.core.cad_object import ObjectDef, instantiate

_BOARD = {
    "name": "board",
    "units": "m",
    "render": {"mesh_uri": "asset://wf/board.glb"},
    "frames": [
        {"name": "datum", "xyz": [0.1, 0.0, 0.0], "quat": [0, 0, 0, 1], "meta": {}},
    ],
    "collision": [
        {
            "xyz": [0.0, 0.0, 0.001],
            "quat": [0, 0, 0, 1],
            "geometry": {"type": "box", "size": [0.3, 0.2, 0.005]},
        },
    ],
    "markers": [
        {
            "name": "tag0",
            "family": "aruco_4x4_50",
            "id": 7,
            "size_m": 0.04,
            "xyz": [0.05, 0.0, 0.005],
            "quat": [0, 0, 0, 1],
        },
    ],
}


def test_from_wire_round_trip():
    obj = ObjectDef.from_wire(_BOARD)
    again = ObjectDef.from_wire(obj.to_wire())
    assert again.to_wire() == obj.to_wire()
    assert obj.render == {"mesh_uri": "asset://wf/board.glb"}


def test_bad_units_rejected():
    with pytest.raises(ValueError, match="^bad_units:"):
        ObjectDef.from_wire(dict(_BOARD, units="mm"))


def test_bad_geometry_rejected():
    bad = dict(_BOARD)
    bad["collision"] = [{"xyz": [0, 0, 0], "quat": [0, 0, 0, 1],
                         "geometry": {"type": "box", "size": [1, 2]}}]
    with pytest.raises(ValueError, match="^bad_object:"):
        ObjectDef.from_wire(bad)


def test_bad_xyz_length_rejected():
    bad = dict(_BOARD)
    bad["frames"] = [{"name": "d", "xyz": [0, 0], "quat": [0, 0, 0, 1]}]
    with pytest.raises(ValueError, match="^bad_object:"):
        ObjectDef.from_wire(bad)


def test_bad_quat_length_rejected():
    bad = dict(_BOARD)
    bad["markers"] = [{"name": "t", "family": "x", "id": 1, "size_m": 0.04,
                       "xyz": [0, 0, 0], "quat": [0, 0, 0]}]
    with pytest.raises(ValueError, match="^bad_object:"):
        ObjectDef.from_wire(bad)


def test_marker_size_must_be_positive():
    bad = dict(_BOARD)
    bad["markers"] = [{"name": "t", "family": "x", "id": 1, "size_m": 0.0,
                       "xyz": [0, 0, 0], "quat": [0, 0, 0, 1]}]
    with pytest.raises(ValueError, match="^bad_object:"):
        ObjectDef.from_wire(bad)


def test_instantiate_expands_frames_and_scene():
    obj = ObjectDef.from_wire(_BOARD)
    frames, scene = instantiate(
        obj, instance="b1", parent_frame="table",
        xyz=[1.0, 2.0, 0.0], quat=[0, 0, 0, 1],
    )
    # root frame
    assert frames["b1"].parent == "table"
    assert frames["b1"].xyz == [1.0, 2.0, 0.0]
    assert frames["b1"].source == "cad"
    assert frames["b1"].meta == {"object": "board"}
    # child frame
    assert frames["b1/datum"].parent == "b1"
    assert frames["b1/datum"].xyz == [0.1, 0.0, 0.0]
    # marker frame
    mf = frames["b1/marker/tag0"]
    assert mf.parent == "b1"
    assert mf.meta["marker"]["id"] == 7
    assert mf.meta["marker"]["size_m"] == 0.04
    assert mf.meta["marker"]["family"] == "aruco_4x4_50"
    # scene object
    so = scene["b1/0"]
    assert so.frame == "b1"
    assert so.meta["name"] == "b1/0"
    assert so.meta["object"] == "board"
    assert so.geometry["type"] == "box"


def test_wire_asymmetry_flat_frame_nested_scene():
    obj = ObjectDef.from_wire(_BOARD)
    frames, scene = instantiate(
        obj, instance="b1", parent_frame="world",
        xyz=[0, 0, 0], quat=[0, 0, 0, 1],
    )
    fw = frames["b1"].to_wire()
    assert "xyz" in fw and "pose" not in fw  # FrameDef wire is flat
    sw = scene["b1/0"].to_wire()
    assert "pose" in sw and "xyz" in sw["pose"]  # SceneObject wire nests pose
