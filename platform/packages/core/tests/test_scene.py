"""SceneObject wire round-trip + geometry validation."""

from __future__ import annotations

import pytest

from wf.core.scene import SceneObject


def _obj(geometry: dict) -> dict:
    return {
        "frame": "table",
        "pose": {"xyz": [0.0, 0.0, -0.025], "quat": [0.0, 0.0, 0.0, 1.0]},
        "geometry": geometry,
    }


def test_box_round_trips():
    wire = _obj({"type": "box", "size": [0.8, 0.8, 0.05]})
    obj = SceneObject.from_wire(wire)
    assert obj.frame == "table"
    assert obj.geometry["type"] == "box"
    back = obj.to_wire()
    assert back["frame"] == "table"
    assert back["pose"]["xyz"] == [0.0, 0.0, -0.025]
    assert back["geometry"]["size"] == [0.8, 0.8, 0.05]


def test_cylinder_parses():
    obj = SceneObject.from_wire(_obj({"type": "cylinder", "radius": 0.1, "length": 0.3}))
    assert obj.geometry["radius"] == 0.1


def test_sphere_parses():
    obj = SceneObject.from_wire(_obj({"type": "sphere", "radius": 0.05}))
    assert obj.geometry["radius"] == 0.05


def test_mesh_parses():
    obj = SceneObject.from_wire(
        _obj({"type": "mesh", "uri": "aubo_description/meshes/table.glb"})
    )
    assert obj.geometry["uri"].endswith(".glb")


def test_rejects_unknown_geometry_type():
    with pytest.raises(ValueError, match="bad_geometry:type"):
        SceneObject.from_wire(_obj({"type": "torus"}))


def test_rejects_box_missing_size():
    with pytest.raises(ValueError, match="box size"):
        SceneObject.from_wire(_obj({"type": "box"}))


def test_rejects_mesh_missing_uri():
    with pytest.raises(ValueError, match="mesh uri"):
        SceneObject.from_wire(_obj({"type": "mesh"}))
