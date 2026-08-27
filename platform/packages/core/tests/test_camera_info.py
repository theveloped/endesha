"""CameraInfo (ROS layout) round trips + legacy pinhole acceptance."""

from __future__ import annotations

import pytest

from wf.core.camera_info import CameraInfo


def test_pinhole_defaults_and_wire():
    info = CameraInfo.pinhole(width=1280, height=800, fx=900.0, fy=910.0)
    assert (info.cx, info.cy) == (639.5, 399.5)
    assert info.is_ideal
    wire = info.to_wire()
    assert wire["K"] == [900.0, 0.0, 639.5, 0.0, 910.0, 399.5, 0.0, 0.0, 1.0]
    assert wire["D"] == [] and wire["distortion_model"] == "plumb_bob"
    assert "P" not in wire
    assert info.projection()[:3] == [900.0, 0.0, 639.5]
    assert CameraInfo.from_wire(wire) == info


def test_legacy_flat_shape_accepted():
    info = CameraInfo.from_wire({"fx": 900.0, "fy": 900.0, "cx": 600.0, "cy": 400.0, "w": 1280, "h": 800})
    assert (info.width, info.height, info.fx, info.cx) == (1280, 800, 900.0, 600.0)
    assert CameraInfo.is_legacy({"fx": 1, "fy": 1, "cx": 1, "cy": 1, "w": 1, "h": 1})
    assert not CameraInfo.is_legacy(info.to_wire())


@pytest.mark.parametrize(
    "bad, reason",
    [
        ({"width": 0, "height": 8, "K": [1, 0, 0, 0, 1, 0, 0, 0, 1]}, "width"),
        ({"width": 8, "height": 8, "K": [0, 0, 0, 0, 1, 0, 0, 0, 1]}, "fx/fy"),
        ({"width": 8, "height": 8, "K": [1, 0, 0, 0, 1, 0, 0, 0, 1], "distortion_model": "nope"}, "distortion_model"),
        ({"width": 8, "height": 8, "K": [1, 0, 0, 0, 1, 0, 0, 0, 1], "D": ["a"]}, "D must be numeric"),
        ({"fx": -1, "fy": 1, "cx": 1, "cy": 1, "w": 1, "h": 1}, "fx/fy"),
        ({"fx": 1, "fy": 1, "cx": 1, "w": 1, "h": 1}, "missing cy"),
    ],
)
def test_rejects(bad, reason):
    with pytest.raises(ValueError, match=reason):
        CameraInfo.from_wire(bad)
