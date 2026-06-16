"""Cell file loader + role->resource resolution (design §8.2).

``load_cell`` parses the operator-authored ``cell.yaml`` into a normalized dict
the supervisor consumes. A cell declares ``resources`` (each a contract-typed
HAL), optional ``bindings`` (``{flow: {role: resource_id}}`` — the role
indirection §8.2), and the reserved distributed seams ``master_node`` /
per-resource ``node`` (single node defaults to ``"main"`` and is its own
master; cross-node dispatch is NOT built this slice).

``resolve_roles`` is the supervisor's core duty: for a flow's contract-typed
roles, bind each to a concrete resource id — explicit ``bindings`` win,
otherwise the first resource of the role's contract. The task_runner is then
told its resolved ``--rid``/``--cid``; it never picks resources itself.

Violations raise ``ValueError("bad_cell:<reason>")`` (mirrors the config
store's ``bad_*:`` convention).
"""

from __future__ import annotations

from pathlib import Path

import yaml

_CONTRACTS = ("arm", "camera2d")


def load_cell(path: str | Path) -> dict:
    """Load and validate a cell.yaml into a normalized dict.

    Returned shape::

        {
          "cell_type": str | None,
          "master_node": str | None,
          "resources": {rid: {"contract": str, "hal": str, "node": str,
                              "params": dict}},
          "bindings": {flow: {role: resource_id}},
        }
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("bad_cell:root must be a mapping")

    resources_in = raw.get("resources")
    if not isinstance(resources_in, dict) or not resources_in:
        raise ValueError("bad_cell:resources must be a non-empty mapping")

    resources: dict[str, dict] = {}
    for rid, decl in resources_in.items():
        if not isinstance(rid, str) or not rid:
            raise ValueError("bad_cell:resource id must be a non-empty string")
        if not isinstance(decl, dict):
            raise ValueError(f"bad_cell:resource {rid} must be a mapping")
        contract = decl.get("contract")
        if contract not in _CONTRACTS:
            raise ValueError(
                f"bad_cell:resource {rid}.contract must be one of {_CONTRACTS}"
            )
        hal = decl.get("hal")
        if not isinstance(hal, str) or not hal:
            raise ValueError(f"bad_cell:resource {rid}.hal must be a non-empty string")
        node = decl.get("node", "main")
        if not isinstance(node, str) or not node:
            raise ValueError(f"bad_cell:resource {rid}.node must be a non-empty string")
        params = decl.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError(f"bad_cell:resource {rid}.params must be a mapping")
        resources[rid] = {
            "contract": contract,
            "hal": hal,
            "node": node,
            "params": params,
        }

    bindings_in = raw.get("bindings") or {}
    if not isinstance(bindings_in, dict):
        raise ValueError("bad_cell:bindings must be a mapping")
    bindings: dict[str, dict] = {}
    for flow_name, role_map in bindings_in.items():
        if not isinstance(flow_name, str) or not flow_name:
            raise ValueError("bad_cell:binding flow must be a non-empty string")
        if not isinstance(role_map, dict):
            raise ValueError(f"bad_cell:binding {flow_name} must be a mapping")
        resolved: dict[str, str] = {}
        for role, resource_id in role_map.items():
            if not isinstance(role, str) or not role:
                raise ValueError(
                    f"bad_cell:binding {flow_name} role must be a non-empty string"
                )
            if resource_id not in resources:
                raise ValueError(
                    f"bad_cell:unknown_binding:{flow_name}.{role}={resource_id}"
                )
            resolved[role] = resource_id
        bindings[flow_name] = resolved

    master_node = raw.get("master_node")
    if master_node is not None and (
        not isinstance(master_node, str) or not master_node
    ):
        raise ValueError("bad_cell:master_node must be a non-empty string")

    return {
        "cell_type": raw.get("cell_type"),
        "master_node": master_node,
        "resources": resources,
        "bindings": bindings,
    }


def resolve_roles(cell: dict, flow_spec: dict, flow_name: str) -> dict[str, str]:
    """Bind each of a flow's roles to a concrete resource id.

    Explicit ``bindings[flow_name][role]`` wins; otherwise the first resource
    whose ``contract`` matches the role's declared contract. Raises
    ``KeyError("unresolved_role:<role>")`` when no resource of the role's
    contract exists in the cell.
    """
    resources = cell["resources"]
    explicit = cell["bindings"].get(flow_name, {})
    out: dict[str, str] = {}
    for role, decl in flow_spec["roles"].items():
        if role in explicit:
            out[role] = explicit[role]
            continue
        contract = decl["contract"]
        match = next(
            (rid for rid, r in resources.items() if r["contract"] == contract),
            None,
        )
        if match is None:
            raise KeyError(f"unresolved_role:{role}")
        out[role] = match
    return out
