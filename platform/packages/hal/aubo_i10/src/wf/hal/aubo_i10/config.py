"""cell.yaml resource loading for the aubo driver."""

from __future__ import annotations

from pathlib import Path

import yaml

_PARAM_DEFAULTS = {
    "rpc_port": 30004,
    "rtde_port": 30010,
    "servo_cycle_s": 0.005,
    "joint_limit_margin_rad": 0.01,
}

_RUCKIG_DEFAULTS = {
    "vmax": [1.5] * 6,
    "amax": [3.0] * 6,
    "jmax": [20.0] * 6,
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
    ruckig = dict(params.get("ruckig_defaults") or {})
    for key, default in _RUCKIG_DEFAULTS.items():
        ruckig.setdefault(key, list(default))
    params["ruckig_defaults"] = ruckig
    return params
