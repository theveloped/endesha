"""Cell file loader + runtime overlay + role->resource resolution (RFC §3).

A cell is the design-time truth: ``resources`` (each a contract-typed logical
device with shared ``config`` and a ``sources`` map of selectable provider
modes), optional ``bindings`` (``{flow: {role: resource_id}}`` — the role
indirection), and the reserved distributed seams ``master_node`` / per-resource
``node``.

The selected source mode per resource is NOT in the cell — it comes from a thin
runtime overlay (``active_sources: {rid: mode}``, loaded by ``load_runtime``).
``realize_cell`` collapses cell + overlay into the realized inventory the rest
of the supervisor consumes: one concrete provider per resource (``hal`` + merged
``params``), exactly the legacy single-hal shape.

``resolve_roles`` is the supervisor's core duty: for a flow's contract-typed
roles, bind each to a concrete resource id — explicit ``bindings`` win,
otherwise the first resource of the role's contract.

Legacy single-``hal`` resources are still accepted (normalized into a synthetic
single source under mode ``"default"``) so existing cell files keep working
through the migration.

Violations raise ``ValueError("bad_cell:<reason>")`` / ``("bad_runtime:...")``
(mirrors the config store's ``bad_*:`` convention).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .procs import LAUNCH_EXTERNAL, LAUNCH_MODULE

_CONTRACTS = ("arm", "camera2d")
# Selectable provider modes. ``off`` is a selection (no provider), never a
# declared source, so it is not in this tuple.
_MODES = ("live", "sim", "replay")
_LAUNCHES = (LAUNCH_MODULE, LAUNCH_EXTERNAL)
# Synthetic mode under which a legacy single-``hal`` resource is normalized.
_LEGACY_MODE = "default"


def _parse_source(rid: str, mode: str, sdecl: object) -> dict:
    if not isinstance(sdecl, dict):
        raise ValueError(f"bad_cell:resource {rid}.sources.{mode} must be a mapping")
    kind = sdecl.get("kind")
    if not isinstance(kind, str) or not kind:
        raise ValueError(
            f"bad_cell:resource {rid}.sources.{mode}.kind must be a non-empty string"
        )
    params = sdecl.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError(
            f"bad_cell:resource {rid}.sources.{mode}.params must be a mapping"
        )
    launch = sdecl.get("launch", "module")
    if launch not in _LAUNCHES:
        raise ValueError(
            f"bad_cell:resource {rid}.sources.{mode}.launch must be one of {_LAUNCHES}"
        )
    return {"kind": kind, "params": params, "launch": launch}


def load_cell(path: str | Path) -> dict:
    """Load and validate a cell.yaml into a normalized dict.

    Returned shape::

        {
          "cell_type": str | None,
          "master_node": str | None,
          "resources": {rid: {"contract": str, "node": str, "model": str | None,
                              "config": dict,
                              "sources": {mode: {"kind": str, "params": dict,
                                                 "launch": "module"|"external"}}}},
          "bindings": {flow: {role: resource_id}},
        }

    Each resource declares either a new-schema ``sources`` map (with shared
    ``config``) or a legacy single ``hal`` (normalized to one source under mode
    ``"default"``) — not both.
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
        node = decl.get("node", "main")
        if not isinstance(node, str) or not node:
            raise ValueError(f"bad_cell:resource {rid}.node must be a non-empty string")
        model = decl.get("model")
        if model is not None and (not isinstance(model, str) or not model):
            raise ValueError(f"bad_cell:resource {rid}.model must be a non-empty string")

        has_sources = "sources" in decl
        has_hal = "hal" in decl
        if has_sources and has_hal:
            raise ValueError(
                f"bad_cell:resource {rid} must declare 'sources' or 'hal', not both"
            )

        if has_sources:
            config = decl.get("config") or {}
            if not isinstance(config, dict):
                raise ValueError(f"bad_cell:resource {rid}.config must be a mapping")
            sources_in = decl["sources"]
            if not isinstance(sources_in, dict) or not sources_in:
                raise ValueError(
                    f"bad_cell:resource {rid}.sources must be a non-empty mapping"
                )
            sources: dict[str, dict] = {}
            for mode, sdecl in sources_in.items():
                if mode not in _MODES:
                    raise ValueError(
                        f"bad_cell:resource {rid}.sources mode must be one of {_MODES}"
                    )
                sources[mode] = _parse_source(rid, mode, sdecl)
        elif has_hal:
            hal = decl.get("hal")
            if not isinstance(hal, str) or not hal:
                raise ValueError(
                    f"bad_cell:resource {rid}.hal must be a non-empty string"
                )
            params = decl.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError(f"bad_cell:resource {rid}.params must be a mapping")
            config = {}
            launch = LAUNCH_EXTERNAL if hal == LAUNCH_EXTERNAL else LAUNCH_MODULE
            sources = {_LEGACY_MODE: {"kind": hal, "params": params, "launch": launch}}
        else:
            raise ValueError(f"bad_cell:resource {rid} must declare 'sources' or 'hal'")

        resources[rid] = {
            "contract": contract,
            "node": node,
            "model": model,
            "config": config,
            "sources": sources,
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


def load_runtime(path: str | Path) -> dict:
    """Load a runtime overlay into ``{"active_sources": {rid: mode}}``.

    ``mode`` is one of ``live``/``sim``/``replay``/``off``. The overlay selects,
    per logical device, which declared source is currently realized; ``off``
    means the device runs no provider this session.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("bad_runtime:root must be a mapping")
    active_in = raw.get("active_sources")
    if active_in is None:
        active_in = {}
    if not isinstance(active_in, dict):
        raise ValueError("bad_runtime:active_sources must be a mapping")
    allowed = (*_MODES, "off")
    active: dict[str, str] = {}
    for rid, mode in active_in.items():
        if not isinstance(rid, str) or not rid:
            raise ValueError("bad_runtime:active_sources key must be a non-empty string")
        # YAML 1.1 parses bare ``off``/``no``/``false`` as boolean False; accept
        # that as the explicit "off" selection so overlays needn't quote it.
        if mode is False:
            mode = "off"
        if mode not in allowed:
            raise ValueError(f"bad_runtime:{rid}.mode must be one of {allowed}")
        active[rid] = mode
    return {"active_sources": active}


def realize_cell(cell: dict, active_sources: dict[str, str] | None = None) -> dict:
    """Collapse cell + overlay into the realized inventory.

    Returns a cell dict whose ``resources`` carry one concrete provider each:
    ``{contract, kind, launch, node, params}`` — ``kind`` is the chosen source's
    provider kind, ``launch`` is how the supervisor brings it up (module /
    external), and ``params`` is the resource ``config`` merged with the chosen
    source's ``params``. Resources selected ``off`` are omitted.

    Source selection per resource: the overlay's ``active_sources[rid]`` wins;
    otherwise the synthetic legacy ``"default"`` source, otherwise the sole
    declared source. A resource with multiple sources and no selection raises
    ``ValueError("bad_runtime:no_active_source:<rid>")``.
    """
    active = active_sources or {}
    realized: dict[str, dict] = {}
    for rid, res in cell["resources"].items():
        sources = res["sources"]
        mode = active.get(rid)
        if mode == "off":
            continue
        if mode is None:
            mode = _default_mode(sources)
            if mode is None:
                raise ValueError(f"bad_runtime:no_active_source:{rid}")
        elif mode not in sources:
            raise ValueError(f"bad_runtime:no_source:{rid}:{mode}")
        chosen = sources[mode]
        realized[rid] = {
            "contract": res["contract"],
            "kind": chosen["kind"],
            "launch": chosen["launch"],
            "node": res["node"],
            "params": {**res["config"], **chosen["params"]},
        }
    return {
        "cell_type": cell["cell_type"],
        "master_node": cell["master_node"],
        "resources": realized,
        "bindings": cell["bindings"],
    }


def _default_mode(sources: dict) -> str | None:
    """The mode used when no overlay selection exists (legacy ``default`` or the
    sole declared source); None when ambiguous."""
    if _LEGACY_MODE in sources:
        return _LEGACY_MODE
    if len(sources) == 1:
        return next(iter(sources))
    return None


def devices_inventory(cell: dict, active_sources: dict[str, str]) -> list[dict]:
    """The device list the supervisor publishes for the UI tree: each logical
    device with its declared source modes and the currently active mode."""
    devices: list[dict] = []
    for rid, res in cell["resources"].items():
        sources = [
            {"mode": mode, "kind": s["kind"], "launch": s["launch"]}
            for mode, s in res["sources"].items()
        ]
        active = active_sources.get(rid) or _default_mode(res["sources"])
        devices.append(
            {
                "id": rid,
                "contract": res["contract"],
                "model": res.get("model"),
                "active": active,
                "sources": sources,
            }
        )
    return devices


def resolve_roles(cell: dict, flow_spec: dict, flow_name: str) -> dict[str, str]:
    """Bind each of a flow's roles to a concrete resource id.

    Explicit ``bindings[flow_name][role]`` wins; otherwise the first resource
    whose ``contract`` matches the role's declared contract. Raises
    ``KeyError("unresolved_role:<role>")`` when no resource of the role's
    contract exists in the cell. Operates on either a normalized or a realized
    cell (both carry ``resources[rid]["contract"]`` + ``bindings``).
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
