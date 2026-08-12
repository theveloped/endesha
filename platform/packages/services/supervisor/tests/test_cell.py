"""Unit tests for cell loading, source realization, and source switching."""

from __future__ import annotations

import os
import tempfile
import textwrap
import threading

import pytest

from wf.services.supervisor.cell import (
    devices_inventory,
    load_cell,
    load_runtime,
    realize_cell,
)
from wf.services.supervisor.procs import PROVIDER_MODULES, provider_module
from wf.services.supervisor.service import SupervisorService

# Legacy single-`hal` cell (still accepted, normalized to one "default" source).
_LEGACY_CELL = textwrap.dedent(
    """
    cell_type: manual-cell-sim@0.1
    platform: 0.1.0
    master_node: main
    resources:
      r1: {contract: arm, hal: arm_sim, node: main, params: {}}
      cam0:
        contract: camera2d
        hal: external
        node: main
        params: {mount: flange, mount_arm: r1}
    """
)

# New-schema cell: shared config + a sources map of selectable provider modes.
_SOURCES_CELL = textwrap.dedent(
    """
    cell_type: manual-cell@0.1
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
    """
)


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


def test_load_cell_defaults_node_and_master(tmp_path):
    text = "resources:\n  r1: {contract: arm, hal: arm_sim, params: {}}\n"
    cell = load_cell(_write(tmp_path, text))
    assert cell["resources"]["r1"]["node"] == "main"
    assert cell["master_node"] is None


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
    ],
)
def test_load_cell_rejects(tmp_path, text):
    with pytest.raises(ValueError) as exc:
        load_cell(_write(tmp_path, text))
    assert str(exc.value).startswith("bad_cell:")


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
        "kind": "arm_sim",
        "launch": "module",
        "node": "main",
        "params": {},
    }
    # legacy external -> external launch preserved.
    assert realized["resources"]["cam0"]["kind"] == "external"
    assert realized["resources"]["cam0"]["launch"] == "external"


def test_realize_overlay_selects_mode_and_merges_config(tmp_path):
    cell = load_cell(_write(tmp_path, _SOURCES_CELL))
    realized = realize_cell(cell, {"r1": "live", "cam0": "sim"})
    # config merged under params; live params win on overlap.
    assert realized["resources"]["r1"] == {
        "contract": "arm",
        "kind": "aubo_i10",
        "launch": "module",
        "node": "main",
        "params": {"lease_ttl_s": 30.0, "ip": "1.2.3.4"},
    }
    # external launch carried through (headless camera served outside supervisor).
    assert realized["resources"]["cam0"]["kind"] == "headless_camera"
    assert realized["resources"]["cam0"]["launch"] == "external"
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


# ── PROVIDER_MODULES coverage ────────────────────────────────────────────────


def test_provider_modules_cover_module_launched_kinds():
    # Module-launched providers only. External-launched kinds (headless_camera)
    # are served outside the supervisor and need no module entry.
    assert PROVIDER_MODULES == {
        ("arm", "arm_sim"): "wf.hal.arm_sim",
        ("arm", "aubo_i10"): "wf.hal.aubo_i10",
        ("arm", "replay_arm"): "wf.hal.replay.arm",
        ("camera2d", "genicam"): "wf.hal.genicam",
        ("camera2d", "replay_camera"): "wf.hal.replay.camera",
    }


def test_provider_module_resolves_and_rejects_unknown():
    assert provider_module("arm", "replay_arm") == "wf.hal.replay.arm"
    with pytest.raises(ValueError) as exc:
        provider_module("arm", "no_such_kind")
    assert str(exc.value) == "bad_cell:unknown_provider:arm:no_such_kind"


# ── devices inventory ────────────────────────────────────────────────────────


def test_devices_inventory(tmp_path):
    cell = load_cell(_write(tmp_path, _SOURCES_CELL))
    by_id = {d["id"]: d for d in devices_inventory(cell, {"r1": "sim", "cam0": "live"})}
    assert by_id["r1"]["contract"] == "arm"
    assert by_id["r1"]["model"] == "aubo_i10"
    assert by_id["r1"]["active"] == "sim"
    assert {s["mode"] for s in by_id["r1"]["sources"]} == {"live", "sim", "replay"}
    assert by_id["cam0"]["active"] == "live"
    cam_sim = next(s for s in by_id["cam0"]["sources"] if s["mode"] == "sim")
    assert cam_sim["launch"] == "external"  # headless camera


# ── runtime source switching (cold switch) ───────────────────────────────────


class _FakeProcs:
    def __init__(self):
        self.calls: list = []

    def stop(self, name, **k):
        self.calls.append(("stop", name))
        return True

    def spawn(self, name, argv, **k):
        self.calls.append(("spawn", name, argv))

    def names(self):
        return []


class _FakePub:
    def put(self, *a, **k):
        pass


def _switchable_service(tmp_path) -> SupervisorService:
    cell = load_cell(_write(tmp_path, _SOURCES_CELL))
    svc = object.__new__(SupervisorService)
    svc.cell = cell
    svc.active_sources = {"r1": "sim", "cam0": "live"}
    svc.realized = realize_cell(cell, svc.active_sources)
    fd, path = tempfile.mkstemp(suffix=".yaml")
    os.close(fd)
    svc.cell_path = path
    svc.realm, svc.node, svc.zenoh_config = "cell", "main", None
    svc._started_at = 0
    svc._lock = threading.Lock()
    svc._procs = _FakeProcs()
    svc._devices_pub = _FakePub()
    svc._descriptor_pub = _FakePub()
    return svc


def test_set_source_cold_switch_restarts_provider(tmp_path):
    svc = _switchable_service(tmp_path)
    r = svc._set_source_reply("r1", "replay")
    assert r["ok"] and svc.active_sources["r1"] == "replay"
    assert ("stop", "hal:r1") in svc._procs.calls
    spawn = next(
        call for call in svc._procs.calls if call[0] == "spawn" and call[1] == "hal:r1"
    )
    assert "wf.hal.replay.arm" in spawn[2]
    os.unlink(svc.cell_path)


def test_set_source_off_stops_without_spawn(tmp_path):
    svc = _switchable_service(tmp_path)
    r = svc._set_source_reply("cam0", "off")
    assert r["ok"] and svc.active_sources["cam0"] == "off"
    assert ("stop", "hal:cam0") in svc._procs.calls
    assert not any(
        call[0] == "spawn" and call[1] == "hal:cam0" for call in svc._procs.calls
    )
    os.unlink(svc.cell_path)


def test_set_source_external_stops_without_spawn(tmp_path):
    svc = _switchable_service(tmp_path)
    r = svc._set_source_reply("cam0", "sim")
    assert r["ok"] and svc.active_sources["cam0"] == "sim"
    assert not any(
        call[0] == "spawn" and call[1] == "hal:cam0" for call in svc._procs.calls
    )
    os.unlink(svc.cell_path)


def test_set_source_rejects_unknown_device_and_mode(tmp_path):
    svc = _switchable_service(tmp_path)
    assert svc._set_source_reply("rX", "sim")["ok"] is False
    assert svc._set_source_reply("r1", "bogus")["ok"] is False
    os.unlink(svc.cell_path)
