"""Flow YAML schema + validation (design: task_runner).

``load_spec(path)`` reads an operator-authored statechart definition and
validates it into a plain dict the runtime consumes. Pose EXISTENCE is checked
at run start (in the service's ``cmd/start``), not here — load validates shape
only. Violations raise ``ValueError("bad_flow:<reason>")`` (mirrors the
config store's ``bad_*:`` convention).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .graph import Graph, is_graph_doc, validate_graph

_FORMATS = ("DataMatrix", "QRCode", "Any")


def _fail(reason: str) -> "ValueError":
    return ValueError(f"bad_flow:{reason}")


def load_flow(path: str | Path) -> dict | Graph:
    """Load a flow file as either a node :class:`Graph` (has ``nodes``) or a
    legacy statechart spec dict. The task_runner + supervisor consume both."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if is_graph_doc(raw):
        return validate_graph(raw)
    return validate_spec(raw)


def load_spec(path: str | Path) -> dict:
    """Load and validate a flow YAML file into a normalized spec dict.

    Returned shape::

        {
          "name": str,
          "poses": [str, ...],
          "roles": {role: {"contract": str}, ...},
          "vision": {"format": str, "min_count": int, "pipeline": str},
          "conveyor": {"do_pin": int, "di_pin": int, "timeout_s": float},
        }
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return validate_spec(raw)


def validate_spec(raw: object) -> dict:
    """Validate an already-parsed mapping; same rules as ``load_spec``."""
    if not isinstance(raw, dict):
        raise _fail("root must be a mapping")

    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise _fail("name must be a non-empty string")
    if any(c.isspace() for c in name) or "/" in name:
        raise _fail("name must not contain whitespace or '/'")

    poses = raw.get("poses")
    if not isinstance(poses, list) or not poses:
        raise _fail("poses must be a non-empty list")
    if not all(isinstance(p, str) and p for p in poses):
        raise _fail("poses must be non-empty strings")

    vision_in = raw.get("vision") or {}
    if not isinstance(vision_in, dict):
        raise _fail("vision must be a mapping")
    fmt = vision_in.get("format", "Any")
    if fmt not in _FORMATS:
        raise _fail(f"vision.format must be one of {_FORMATS}")
    min_count = vision_in.get("min_count", 1)
    if not isinstance(min_count, int) or isinstance(min_count, bool) or min_count < 0:
        raise _fail("vision.min_count must be a non-negative int")
    pipeline = vision_in.get("pipeline", f"{name}_detect")
    if not isinstance(pipeline, str) or not pipeline:
        raise _fail("vision.pipeline must be a non-empty string")

    conveyor_in = raw.get("conveyor") or {}
    if not isinstance(conveyor_in, dict):
        raise _fail("conveyor must be a mapping")
    do_pin = conveyor_in.get("do_pin", 0)
    di_pin = conveyor_in.get("di_pin", 0)
    for label, pin in (("do_pin", do_pin), ("di_pin", di_pin)):
        if not isinstance(pin, int) or isinstance(pin, bool) or pin < 0:
            raise _fail(f"conveyor.{label} must be a non-negative int")
    timeout_s = conveyor_in.get("timeout_s", 3.0)
    if not isinstance(timeout_s, (int, float)) or isinstance(timeout_s, bool):
        raise _fail("conveyor.timeout_s must be a number")
    if timeout_s <= 0:
        raise _fail("conveyor.timeout_s must be positive")

    roles_in = raw.get("roles")
    if roles_in is None:
        roles = {"arm": {"contract": "arm"}, "cam": {"contract": "camera2d"}}
    else:
        if not isinstance(roles_in, dict) or not roles_in:
            raise _fail("roles must be a non-empty mapping")
        roles = {}
        for role_name, decl in roles_in.items():
            if not isinstance(role_name, str) or not role_name:
                raise _fail("roles_must_be_named")
            if not isinstance(decl, dict):
                raise _fail(f"roles.{role_name}_must_be_a_mapping")
            contract = decl.get("contract")
            if not isinstance(contract, str) or not contract:
                raise _fail(f"roles.{role_name}.contract_must_be_a_string")
            roles[role_name] = {"contract": contract}

    return {
        "name": name,
        "poses": list(poses),
        "roles": roles,
        "vision": {
            "format": fmt,
            "min_count": int(min_count),
            "pipeline": pipeline,
        },
        "conveyor": {
            "do_pin": int(do_pin),
            "di_pin": int(di_pin),
            "timeout_s": float(timeout_s),
        },
    }
