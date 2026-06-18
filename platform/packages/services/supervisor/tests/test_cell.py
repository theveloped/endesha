"""Unit tests for the supervisor cell loader, runtime overlay, source
realization, and role resolution (no bus)."""

from __future__ import annotations

import textwrap

import pytest

from wf.services.supervisor.cell import (
    load_cell,
    load_runtime,
    realize_cell,
    resolve_roles,
)
from wf.services.supervisor.procs import HAL_MODULES

# Legacy single-`hal` cell (still accepted, normalized to one "default" source).
_LEGACY_CELL = textwrap.dedent(
    """
    cell_type: vision-pick-cell-sim@0.1
    platform: 0.1.0
    master_node: main
    resources:
      r1: {contract: arm, hal: arm_sim, node: main, params: {}}
      cam0:
        contract: camera2d
        hal: external
        node: main
        params: {mount: flange, mount_arm: r1}
    bindings:
      demo_inspect: {arm: r1, cam: cam0}
    """
)

# New-schema cell: shared config + a sources map of selectable provider modes.
_SOURCES_CELL = textwrap.dedent(
    """
    cell_type: vision-pick-cell@0.1
    resources:
      r1:
        contract: arm
        model: aubo_i10
        config: {lease_ttl_s: 30.0}
        sources:
          live: {kind: aubo_i10, params: {ip: 1.2.3.4}}
          sim: {kind: arm_sim, params: {}}
          replay: {kind: replay_arm, params: {recording: foo.mcap}}
      cam0:
        contract: camera2d
        config: {mount_arm: r1}
        sources:
          live: {kind: genicam, params: {serial: null}}
          sim: {kind: headless_camera, launch: external, params: {}}
    bindings:
      demo_inspect: {arm: r1, cam: cam0}
    """
)

_DEMO_SPEC = {
    "name": "demo_inspect",
    "poses": ["a"],
    "roles": {"arm": {"contract": "arm"}, "cam": {"contract": "camera2d"}},
    "vision": {"format": "DataMatrix", "min_count": 1, "pipeline": "demo_detect"},
    "conveyor": {"do_pin": 0, "di_pin": 0, "timeout_s": 2.0},
}


def _write(tmp_path, text, name="cell.yaml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


# ── load_cell: legacy normalization ──────────────────────────────────────────


def test_load_cell_normalizes_legacy_hal(tmp_path):
    cell = load_cell(_write(tmp_path, _LEGACY_CELL))
    assert set(cell["resources"]) == {"r1", "cam0"}
    assert cell["resources"]["r1"] == {
        "contract": "arm",
        "node": "main",
        "model": None,
        "config": {},
        "sources": {
            "default": {"kind": "arm_sim", "params": {}, "launch": "module"},
        },
    }
    # hal: external -> a synthetic source with launch external.
    assert cell["resources"]["cam0"]["sources"] == {
        "default": {
            "kind": "external",
            "params": {"mount": "flange", "mount_arm": "r1"},
            "launch": "external",
        },
    }
    assert cell["master_node"] == "main"
    assert cell["bindings"] == {"demo_inspect": {"arm": "r1", "cam": "cam0"}}


def test_load_cell_defaults_node_and_master(tmp_path):
    text = "resources:\n  r1: {contract: arm, hal: arm_sim, params: {}}\n"
    cell = load_cell(_write(tmp_path, text))
    assert cell["resources"]["r1"]["node"] == "main"
    assert cell["master_node"] is None
    assert cell["bindings"] == {}


# ── load_cell: new sources schema ────────────────────────────────────────────


def test_load_cell_accepts_sources_schema(tmp_path):
    cell = load_cell(_write(tmp_path, _SOURCES_CELL))
    r1 = cell["resources"]["r1"]
    assert r1["model"] == "aubo_i10"
    assert r1["config"] == {"lease_ttl_s": 30.0}
    assert set(r1["sources"]) == {"live", "sim", "replay"}
    assert r1["sources"]["live"] == {
        "kind": "aubo_i10",
        "params": {"ip": "1.2.3.4"},
        "launch": "module",
    }
    assert cell["resources"]["cam0"]["sources"]["sim"]["launch"] == "external"


# ── load_cell reject ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "cell_type: x@0.1\n",  # no resources
        "resources: {}\n",  # empty resources
        "resources:\n  r1: {hal: arm_sim, params: {}}\n",  # missing contract
        "resources:\n  r1: {contract: arm, params: {}}\n",  # neither hal nor sources
        "resources:\n  r1: {contract: laser, hal: x, params: {}}\n",  # bad contract
        # both hal and sources
        "resources:\n  r1: {contract: arm, hal: arm_sim, sources: {sim: {kind: arm_sim}}}\n",
        # unknown source mode
        "resources:\n  r1: {contract: arm, sources: {fast: {kind: arm_sim}}}\n",
        # source missing kind
        "resources:\n  r1: {contract: arm, sources: {sim: {params: {}}}}\n",
        # bad launch
        "resources:\n  r1: {contract: arm, sources: {sim: {kind: arm_sim, launch: docker}}}\n",
        # unknown binding -> resource id not present
        textwrap.dedent(
            """
            resources:
              r1: {contract: arm, hal: arm_sim, params: {}}
            bindings:
              demo_inspect: {arm: rZ}
            """
        ),
    ],
)
def test_load_cell_rejects(tmp_path, text):
    with pytest.raises(ValueError) as exc:
        load_cell(_write(tmp_path, text))
    assert str(exc.value).startswith("bad_cell:")


def test_load_cell_unknown_binding_message(tmp_path):
    text = textwrap.dedent(
        """
        resources:
          r1: {contract: arm, hal: arm_sim, params: {}}
        bindings:
          demo_inspect: {arm: rZ}
        """
    )
    with pytest.raises(ValueError) as exc:
        load_cell(_write(tmp_path, text))
    assert str(exc.value) == "bad_cell:unknown_binding:demo_inspect.arm=rZ"


# ── load_runtime ─────────────────────────────────────────────────────────────


def test_load_runtime_parses_active_sources(tmp_path):
    text = "active_sources:\n  r1: sim\n  cam0: live\n"
    assert load_runtime(_write(tmp_path, text, "runtime.yaml")) == {
        "active_sources": {"r1": "sim", "cam0": "live"}
    }


def test_load_runtime_allows_off(tmp_path):
    text = "active_sources:\n  cam0: off\n"
    assert load_runtime(_write(tmp_path, text, "runtime.yaml")) == {
        "active_sources": {"cam0": "off"}
    }


def test_load_runtime_empty(tmp_path):
    assert load_runtime(_write(tmp_path, "{}\n", "runtime.yaml")) == {
        "active_sources": {}
    }


@pytest.mark.parametrize(
    "text",
    [
        "active_sources: []\n",  # not a mapping
        "active_sources:\n  r1: fast\n",  # invalid mode
    ],
)
def test_load_runtime_rejects(tmp_path, text):
    with pytest.raises(ValueError) as exc:
        load_runtime(_write(tmp_path, text, "runtime.yaml"))
    assert str(exc.value).startswith("bad_runtime:")


# ── realize_cell ─────────────────────────────────────────────────────────────


def test_realize_legacy_uses_default_source(tmp_path):
    cell = load_cell(_write(tmp_path, _LEGACY_CELL))
    realized = realize_cell(cell)
    assert realized["resources"]["r1"] == {
        "contract": "arm",
        "hal": "arm_sim",
        "node": "main",
        "params": {},
    }
    # legacy external -> hal sentinel preserved.
    assert realized["resources"]["cam0"]["hal"] == "external"
    assert realized["bindings"] == {"demo_inspect": {"arm": "r1", "cam": "cam0"}}


def test_realize_overlay_selects_mode_and_merges_config(tmp_path):
    cell = load_cell(_write(tmp_path, _SOURCES_CELL))
    realized = realize_cell(cell, {"r1": "live", "cam0": "sim"})
    # config merged under params; live params win on overlap.
    assert realized["resources"]["r1"] == {
        "contract": "arm",
        "hal": "aubo_i10",
        "node": "main",
        "params": {"lease_ttl_s": 30.0, "ip": "1.2.3.4"},
    }
    # external launch -> hal sentinel.
    assert realized["resources"]["cam0"]["hal"] == "external"
    assert realized["resources"]["cam0"]["params"] == {"mount_arm": "r1"}


def test_realize_off_omits_resource(tmp_path):
    cell = load_cell(_write(tmp_path, _SOURCES_CELL))
    realized = realize_cell(cell, {"r1": "sim", "cam0": "off"})
    assert set(realized["resources"]) == {"r1"}


def test_realize_multi_source_without_selection_errors(tmp_path):
    cell = load_cell(_write(tmp_path, _SOURCES_CELL))
    with pytest.raises(ValueError) as exc:
        realize_cell(cell)  # r1 has 3 sources, no overlay
    assert str(exc.value).startswith("bad_runtime:no_active_source:r1")


def test_realize_unknown_mode_errors(tmp_path):
    cell = load_cell(_write(tmp_path, _SOURCES_CELL))
    with pytest.raises(ValueError) as exc:
        realize_cell(cell, {"r1": "sim", "cam0": "replay"})  # cam0 has no replay
    assert str(exc.value) == "bad_runtime:no_source:cam0:replay"


# ── resolve_roles ────────────────────────────────────────────────────────────


def test_resolve_roles_explicit_binding_wins(tmp_path):
    text = textwrap.dedent(
        """
        resources:
          r1: {contract: arm, hal: arm_sim, params: {}}
          r2: {contract: arm, hal: arm_sim, params: {}}
          cam0: {contract: camera2d, hal: genicam, params: {}}
        bindings:
          demo_inspect: {arm: r2, cam: cam0}
        """
    )
    cell = load_cell(_write(tmp_path, text))
    assert resolve_roles(cell, _DEMO_SPEC, "demo_inspect") == {
        "arm": "r2",
        "cam": "cam0",
    }


def test_resolve_roles_falls_back_to_first_of_contract(tmp_path):
    text = textwrap.dedent(
        """
        resources:
          r1: {contract: arm, hal: arm_sim, params: {}}
          cam0: {contract: camera2d, hal: genicam, params: {}}
        """
    )
    cell = load_cell(_write(tmp_path, text))
    assert resolve_roles(cell, _DEMO_SPEC, "demo_inspect") == {
        "arm": "r1",
        "cam": "cam0",
    }


def test_resolve_roles_unresolved_when_no_resource_of_contract(tmp_path):
    text = "resources:\n  r1: {contract: arm, hal: arm_sim, params: {}}\n"
    cell = load_cell(_write(tmp_path, text))
    with pytest.raises(KeyError) as exc:
        resolve_roles(cell, _DEMO_SPEC, "demo_inspect")
    assert exc.value.args[0] == "unresolved_role:cam"


def test_resolve_roles_works_on_realized_cell(tmp_path):
    cell = load_cell(_write(tmp_path, _SOURCES_CELL))
    realized = realize_cell(cell, {"r1": "sim", "cam0": "live"})
    assert resolve_roles(realized, _DEMO_SPEC, "demo_inspect") == {
        "arm": "r1",
        "cam": "cam0",
    }


# ── HAL_MODULES coverage ─────────────────────────────────────────────────────


def test_hal_modules_cover_all_pairs():
    # camera2d_sim (pyrender) was retired: the sim camera is now the external
    # headless-browser HAL (launch: external), not a supervisor-spawned process.
    assert HAL_MODULES == {
        ("arm", "arm_sim"): "wf.hal.arm_sim",
        ("arm", "aubo_i10"): "wf.hal.aubo_i10",
        ("camera2d", "genicam"): "wf.hal.genicam",
    }
