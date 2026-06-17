"""Unit tests for the supervisor cell loader + role resolution (no bus)."""

from __future__ import annotations

import textwrap

import pytest

from wf.services.supervisor.cell import load_cell, resolve_roles
from wf.services.supervisor.procs import HAL_MODULES

_SIM_CELL = textwrap.dedent(
    """
    cell_type: vision-pick-cell-sim@0.1
    platform: 0.1.0
    master_node: main
    resources:
      r1: {contract: arm, hal: arm_sim, node: main, params: {}}
      cam0:
        contract: camera2d
        hal: camera2d_sim
        node: main
        params: {mount: flange, mount_arm: r1}
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


def _write(tmp_path, text):
    p = tmp_path / "cell.yaml"
    p.write_text(text, encoding="utf-8")
    return str(p)


# ── load_cell accept ────────────────────────────────────────────────────────


def test_load_cell_accepts_sim_cell(tmp_path):
    cell = load_cell(_write(tmp_path, _SIM_CELL))
    assert set(cell["resources"]) == {"r1", "cam0"}
    assert cell["resources"]["r1"] == {
        "contract": "arm",
        "hal": "arm_sim",
        "node": "main",
        "params": {},
    }
    assert cell["master_node"] == "main"
    assert cell["bindings"] == {"demo_inspect": {"arm": "r1", "cam": "cam0"}}


def test_load_cell_defaults_node_and_master(tmp_path):
    text = textwrap.dedent(
        """
        resources:
          r1: {contract: arm, hal: arm_sim, params: {}}
        """
    )
    cell = load_cell(_write(tmp_path, text))
    assert cell["resources"]["r1"]["node"] == "main"
    assert cell["master_node"] is None
    assert cell["bindings"] == {}


# ── load_cell reject ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "cell_type: x@0.1\n",  # no resources
        "resources: {}\n",  # empty resources
        "resources:\n  r1: {hal: arm_sim, params: {}}\n",  # missing contract
        "resources:\n  r1: {contract: arm, params: {}}\n",  # missing hal
        "resources:\n  r1: {contract: laser, hal: x, params: {}}\n",  # bad contract
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


# ── resolve_roles ───────────────────────────────────────────────────────────


def test_resolve_roles_explicit_binding_wins(tmp_path):
    text = textwrap.dedent(
        """
        resources:
          r1: {contract: arm, hal: arm_sim, params: {}}
          r2: {contract: arm, hal: arm_sim, params: {}}
          cam0: {contract: camera2d, hal: camera2d_sim, params: {}}
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
          cam0: {contract: camera2d, hal: camera2d_sim, params: {}}
        """
    )
    cell = load_cell(_write(tmp_path, text))
    assert resolve_roles(cell, _DEMO_SPEC, "demo_inspect") == {
        "arm": "r1",
        "cam": "cam0",
    }


def test_resolve_roles_unresolved_when_no_resource_of_contract(tmp_path):
    text = textwrap.dedent(
        """
        resources:
          r1: {contract: arm, hal: arm_sim, params: {}}
        """
    )
    cell = load_cell(_write(tmp_path, text))
    with pytest.raises(KeyError) as exc:
        resolve_roles(cell, _DEMO_SPEC, "demo_inspect")
    assert exc.value.args[0] == "unresolved_role:cam"


# ── HAL_MODULES coverage ────────────────────────────────────────────────────


def test_hal_modules_cover_all_pairs():
    # camera2d_sim (pyrender) was retired: the sim camera is now the external
    # headless-browser HAL (hal: external), not a supervisor-spawned process.
    assert HAL_MODULES == {
        ("arm", "arm_sim"): "wf.hal.arm_sim",
        ("arm", "aubo_i10"): "wf.hal.aubo_i10",
        ("camera2d", "genicam"): "wf.hal.genicam",
    }
