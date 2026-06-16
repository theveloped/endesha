"""cell.yaml resource loading for the genicam driver."""

from __future__ import annotations

from pathlib import Path

import yaml

_PARAM_DEFAULTS = {
    "serial": None,  # None -> first enumerated device (index 0)
    "cti_path": "C:/Program Files/Teledyne/Spinnaker/cti64/vs2015/Spinnaker_GenTL_v140.cti",
    "pixel_format": "BayerRG8",
    "ptp": False,
    # Eye-in-hand mount: the arm whose flange this camera rides and the rigid
    # flange->optical transform (OpenCV optical: +Z forward). Used to stamp the
    # per-frame world<-optical pose into the FrameHeader (the UI frustum).
    "mount_arm": "r1",
    "mount_xyz": [0.0, 0.0, 0.05],
    "mount_rpy_deg": [0.0, 0.0, 0.0],
}

_STREAM_DEFAULTS = {
    "rate_hz": 15.0,
    "scale": 0.25,
    "roi": None,
    "encoding": "jpeg",
    "quality": 75,
}

_GRAB_DEFAULTS = {
    "scale": 1.0,
    "roi": None,
    "encoding": "BayerRG8",
    "quality": 95,
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
    for name, defaults in (
        ("stream_defaults", _STREAM_DEFAULTS),
        ("grab_defaults", _GRAB_DEFAULTS),
    ):
        merged = dict(params.get(name) or {})
        for key, default in defaults.items():
            merged.setdefault(key, default)
        params[name] = merged
    return params
