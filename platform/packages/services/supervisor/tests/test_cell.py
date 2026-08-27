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
        config:
          mount_arm: r1
          render: {width: 1280, height: 800, fx: 900.0, fy: 900.0}
        sources:
          live: {kind: genicam, params: {serial: null}}
          sim: {kind: headless_camera, launch: external, params: {}}
          browser_sim: {kind: browser_camera, params: {}}
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
        "provides": {},
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
    assert set(cell["resources"]["cam0"]["sources"]) == {"live", "sim", "browser_sim"}
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
    assert realized["resources"]["cam0"]["params"] == {
        "mount_arm": "r1",
        "render": {"width": 1280, "height": 800, "fx": 900.0, "fy": 900.0},
    }


def test_realize_camera_sources_share_device_optics(tmp_path):
    cell = load_cell(_write(tmp_path, _SOURCES_CELL))
    sim = realize_cell(cell, {"r1": "sim", "cam0": "sim"})
    browser = realize_cell(cell, {"r1": "sim", "cam0": "browser_sim"})
    assert sim["resources"]["cam0"]["params"]["render"] == browser["resources"]["cam0"]["params"]["render"]


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
        ("camera2d", "browser_camera"): "wf.hal.browser_camera",
        ("dio", "sim_dio"): "wf.hal.sim_dio",
        ("tags", "sim_tags"): "wf.hal.sim_tags",
        ("tags", "opcua"): "wf.hal.opcua",
        ("washer", "ecoclean"): "wf.hal.ecoclean",
        ("washer", "ecoclean_sim"): "wf.hal.ecoclean",
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
    assert by_id["r1"]["config"] == {"lease_ttl_s": 30.0}
    assert {s["mode"] for s in by_id["r1"]["sources"]} == {"live", "sim", "replay"}
    assert by_id["cam0"]["active"] == "live"
    assert by_id["cam0"]["config"] == {
        "mount_arm": "r1",
        "render": {"width": 1280, "height": 800, "fx": 900.0, "fy": 900.0},
    }
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


class _FakeEvents:
    def __init__(self):
        self.records = []

    def emit(self, kind, service=None, **detail):
        self.records.append({"kind": kind, "service": service, **detail})


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
    svc._events = _FakeEvents()
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


# ── dio devices ──────────────────────────────────────────────────────────────

_DIO_CELL = textwrap.dedent(
    """
    cell_type: t@0.1
    resources:
      io0:
        contract: dio
        config:
          channels:
            part_present: {kind: di, bank: standard, pin: 3}
            clamp: {kind: do, bank: standard, pin: 0}
        sources:
          sim: {kind: sim_dio, params: {}}
    """
)

_PROVIDES_CELL = textwrap.dedent(
    """
    cell_type: t@0.1
    resources:
      r1:
        contract: arm
        config: {}
        sources:
          live: {kind: aubo_i10, params: {ip: 1.2.3.4}}
          sim: {kind: arm_sim, params: {}}
        provides:
          io0:
            contract: dio
            model: aubo_onboard
            channels:
              part_present: {kind: di, bank: standard, pin: 3}
            layout: {di: 16, do: 16, tool_do: 4}
    """
)


def test_provided_device_realizes_into_host_params_and_inventory(tmp_path):
    cell = load_cell(_write(tmp_path, _PROVIDES_CELL))
    assert list(cell["resources"]["r1"]["provides"]) == ["io0"]
    realized = realize_cell(cell, {"r1": "sim"})
    assert list(realized["resources"]) == ["r1"], "provided devices spawn no process"
    provides = realized["resources"]["r1"]["params"]["provides"]
    assert provides["io0"]["contract"] == "dio"
    assert provides["io0"]["channels"]["part_present"]["pin"] == 3
    assert provides["io0"]["layout"]["tool_do"] == 4
    by_id = {d["id"]: d for d in devices_inventory(cell, {"r1": "sim"})}
    io0 = by_id["io0"]
    assert io0["contract"] == "dio" and io0["provided_by"] == "r1"
    assert io0["active"] == "sim" and io0["sources"] == []
    assert io0["model"] == "aubo_onboard"
    assert "part_present" in io0["config"]["channels"]


def test_provided_device_cannot_be_switched(tmp_path):
    cell = load_cell(_write(tmp_path, _PROVIDES_CELL))
    svc = SupervisorService.__new__(SupervisorService)
    svc.cell = cell
    assert svc._set_source_reply("io0", "sim") == {"ok": False, "error": "provided_by:r1"}


@pytest.mark.parametrize(
    "provides, reason",
    [
        ("{io0: {contract: camera2d}}", "contract must be one of"),
        ("{io0: {contract: dio, channels: {Bad: {kind: di}}}}", "must match"),
        ("{r1: {contract: dio}}", "duplicate device id"),
    ],
)
def test_provides_rejects(tmp_path, provides, reason):
    cell = textwrap.dedent(
        f"""
        cell_type: t@0.1
        resources:
          r1:
            contract: arm
            sources:
              sim: {{kind: arm_sim, params: {{}}}}
            provides: {provides}
        """
    )
    with pytest.raises(ValueError, match=reason):
        load_cell(_write(tmp_path, cell))


def test_dio_resource_loads_and_realizes(tmp_path):
    cell = load_cell(_write(tmp_path, _DIO_CELL))
    io0 = cell["resources"]["io0"]
    assert io0["contract"] == "dio"
    assert list(io0["config"]["channels"]) == ["part_present", "clamp"]
    realized = realize_cell(cell, {"io0": "sim"})
    assert realized["resources"]["io0"]["kind"] == "sim_dio"
    assert realized["resources"]["io0"]["params"]["channels"]["clamp"] == {
        "kind": "do", "bank": "standard", "pin": 0,
    }
    assert provider_module("dio", "sim_dio") == "wf.hal.sim_dio"


@pytest.mark.parametrize(
    "channels, reason",
    [
        ("{}", "must declare at least one channel"),
        ("{Bad: {kind: di}}", "must match"),
        ("{x: {kind: relay}}", "kind must be one of"),
    ],
)
def test_dio_resource_rejects_bad_channels(tmp_path, channels, reason):
    cell = textwrap.dedent(
        f"""
        cell_type: t@0.1
        resources:
          io0:
            contract: dio
            config:
              channels: {channels}
            sources:
              sim: {{kind: sim_dio, params: {{}}}}
        """
    )
    with pytest.raises(ValueError, match=reason):
        load_cell(_write(tmp_path, cell))


# ── the shipped Ecoclean cell (washer host + provided tags device) ──────────

_ECOCLEAN_CELL = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "deploy", "ecoclean", "cell.yaml")


def test_ecoclean_cell_loads_and_realizes():
    cell = load_cell(_ECOCLEAN_CELL)
    washer = cell["resources"]["washer0"]
    assert washer["contract"] == "washer"
    assert washer["provides"]["plc0"]["contract"] == "tags"
    for mode in ("sim", "live"):
        realized = realize_cell(cell, {"washer0": mode})
        assert list(realized["resources"]) == ["washer0"], "the tags device is hosted, not spawned"
        res = realized["resources"]["washer0"]
        assert provider_module(res["contract"], res["kind"]) == "wf.hal.ecoclean"
        assert res["params"]["provides"]["plc0"]["tags"]["machine_ready"] == {"tag": "ReadyToLoad"}
        assert res["params"]["door_timeout_s"] == 90
    by_id = {d["id"]: d for d in devices_inventory(cell, {"washer0": "sim"})}
    assert by_id["plc0"]["provided_by"] == "washer0" and by_id["plc0"]["contract"] == "tags"
    assert by_id["washer0"]["active"] == "sim"


def test_provides_tags_validates_names(tmp_path):
    cell = textwrap.dedent(
        """
        cell_type: t@0.1
        resources:
          w:
            contract: washer
            sources:
              sim: {kind: ecoclean_sim, params: {}}
            provides:
              plc0: {contract: tags, tags: {"Bad Name": {tag: X}}}
        """
    )
    with pytest.raises(ValueError, match="provides.plc0"):
        load_cell(_write(tmp_path, cell))
