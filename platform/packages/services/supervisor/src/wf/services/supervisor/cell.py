"""Cell definition and runtime source selection.

A cell is the design-time truth: contract-typed logical resources with shared
configuration and selectable provider sources. A runtime overlay selects one
live, simulated, replay, or off source per resource. ``realize_cell`` collapses
both documents into the concrete provider inventory consumed by the supervisor.

Legacy single-``hal`` resources remain accepted and are normalized into one
synthetic ``default`` source.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from wf.contracts.dio.messages import parse_channels

from .procs import LAUNCH_EXTERNAL, LAUNCH_MODULE

_CONTRACTS = ("arm", "camera2d", "dio")
# Selectable provider source names. ``off`` is a selection (no provider), never
# a declared source. The camera exposes two independent simulated providers.
_MODES = ("live", "sim", "browser_sim", "replay")
_LAUNCHES = (LAUNCH_MODULE, LAUNCH_EXTERNAL)
# Synthetic mode under which a legacy single-``hal`` resource is normalized.
_LEGACY_MODE = "default"
# Cell-level control lease TTL when cell.yaml has no ``control:`` block.
DEFAULT_LEASE_TTL_S = 30.0


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

    Returned resources contain their contract, node, model, shared config, and
    selectable provider sources. Each resource declares either a ``sources``
    map or a legacy single ``hal``.
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
            raise ValueError(
                f"bad_cell:resource {rid}.model must be a non-empty string"
            )

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
            if contract == "dio":
                # Named channels are the program-facing surface of a dio device;
                # validate the schema at load so a typo fails the cell, not a run.
                try:
                    channels = parse_channels(config.get("channels"))
                except ValueError as exc:
                    raise ValueError(f"bad_cell:resource {rid}.{exc}") from exc
                if not channels:
                    raise ValueError(
                        f"bad_cell:resource {rid}.config.channels must declare at least one channel"
                    )
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

    master_node = raw.get("master_node")
    if master_node is not None and (
        not isinstance(master_node, str) or not master_node
    ):
        raise ValueError("bad_cell:master_node must be a non-empty string")

    return {
        "cell_type": raw.get("cell_type"),
        "master_node": master_node,
        "control": _parse_control(raw.get("control")),
        "resources": resources,
    }


def _parse_control(decl: object) -> dict:
    """Cell-level control lease settings (``control: {lease_ttl_s}``)."""
    if decl is None:
        return {"lease_ttl_s": DEFAULT_LEASE_TTL_S}
    if not isinstance(decl, dict):
        raise ValueError("bad_cell:control must be a mapping")
    ttl = decl.get("lease_ttl_s", DEFAULT_LEASE_TTL_S)
    if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or ttl <= 0:
        raise ValueError("bad_cell:control.lease_ttl_s must be a positive number")
    return {"lease_ttl_s": float(ttl)}


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
            raise ValueError(
                "bad_runtime:active_sources key must be a non-empty string"
            )
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
        "control": cell.get("control", {"lease_ttl_s": DEFAULT_LEASE_TTL_S}),
        "resources": realized,
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
                "config": res.get("config", {}),
                "sources": sources,
            }
        )
    return devices
