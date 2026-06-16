"""cell.yaml resource loading for the sim camera driver.

Reads the SAME resource entry as the genicam driver (same ``cid``,
``stream_defaults``); hardware-only params (``serial``, ``cti_path``,
``ip``) pass through unused. The ``render`` block carries this HAL's
ground-truth scene/optics — nominal intrinsics, the flange->optical mount,
and the calibration target geometry — merged with the defaults below.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_PARAM_DEFAULTS = {
    "serial": None,  # informational; ignored by the sim
    "mount": "flange",  # eye-in-hand
    "mount_arm": "r1",  # arm whose flange this camera rides
}

# Ground-truth optics + scene. Lengths in meters, angles in degrees.
_RENDER_DEFAULTS = {
    "width": 1280,
    "height": 800,
    "fx": 900.0,  # focal length, px
    "fy": 900.0,
    "cx": None,  # None -> (width  - 1) / 2
    "cy": None,  # None -> (height - 1) / 2
    "exposure_us": 10000.0,  # virtual; reported in status + FrameHeader
    "gain_db": 0.0,
    "background_gray": 90,  # scene background fill (0-255)
    # T_flange_optical: camera rigidly mounted on the flange. rpy=0 => the
    # optical axis (+Z, OpenCV convention) coincides with the flange +Z.
    "mount_xyz": [0.0, 0.0, 0.05],  # 5 cm beyond the flange face
    "mount_rpy_deg": [0.0, 0.0, 0.0],
    # Calibration target: a flat checkerboard lying on the floor (z=0) in
    # front of the base. ``squares`` are columns x rows.
    "board_squares_x": 7,
    "board_squares_y": 5,
    "board_square_m": 0.03,
    "board_xyz": [0.5, 0.0, 0.0],
    "board_rpy_deg": [0.0, 0.0, 0.0],
    # Camera pose used until the first flange sample arrives (and when no arm
    # runs, e.g. the conformance suite): straight down over the board center.
    "fallback_height_m": 0.45,
}

_STREAM_DEFAULTS = {
    "rate_hz": 15.0,
    "scale": 0.25,
    "roi": None,
    "encoding": "jpeg",
    "quality": 75,
}

# Unlike genicam (Bayer default), the sim defaults grabs to JPEG: the render
# is already debayered, JPEG is what every consumer (UI, calibration) wants.
_GRAB_DEFAULTS = {
    "scale": 1.0,
    "roi": None,
    "encoding": "jpeg",
    "quality": 90,
}


def load_resource(cell_yaml_path: str, resource_id: str) -> dict:
    """Return the ``resources[resource_id].params`` dict merged with defaults.

    Raises FileNotFoundError / KeyError with clear messages when the file or
    resource id is missing.
    """
    path = Path(cell_yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"cell file not found: {cell_yaml_path}")
    with open(path, encoding="utf-8") as f:
        cell = yaml.safe_load(f) or {}

    resources = cell.get("resources") or {}
    if resource_id not in resources:
        available = ", ".join(sorted(resources)) or "<none>"
        raise KeyError(
            f"resource {resource_id!r} not found in {cell_yaml_path} "
            f"(available: {available})"
        )

    params = dict(resources[resource_id].get("params") or {})
    for key, default in _PARAM_DEFAULTS.items():
        params.setdefault(key, default)

    render = dict(params.get("render") or {})
    for key, default in _RENDER_DEFAULTS.items():
        render.setdefault(key, list(default) if isinstance(default, list) else default)
    params["render"] = render

    for name, defaults in (
        ("stream_defaults", _STREAM_DEFAULTS),
        ("grab_defaults", _GRAB_DEFAULTS),
    ):
        merged = dict(params.get(name) or {})
        for key, default in defaults.items():
            merged.setdefault(key, default)
        params[name] = merged
    return params
