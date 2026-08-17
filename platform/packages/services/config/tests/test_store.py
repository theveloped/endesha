"""Unit tests for the pure :class:`ConfigStore` (no zenoh)."""

from __future__ import annotations

import json

import pytest

from wf.services.config.store import ConfigStore

FRAME = {
    "parent": "world",
    "xyz": [0.1, 0.2, 0.3],
    "quat": [0.0, 0.0, 0.0, 1.0],
    "source": "manual",
    "meta": {},
}
POSE = {"q": [0.0, -0.5, 2.0, -0.7, 1.5, 0.0], "meta": {}}
TCP = {
    "xyz": [0.0, 0.0, 0.12],
    "quat": [0.0, 0.0, 0.0, 1.0],
    "role": "tool",
    "selectable_as_tcp": True,
}
SCENE = {
    "frame": "table",
    "pose": {"xyz": [0.0, 0.0, -0.025], "quat": [0.0, 0.0, 0.0, 1.0]},
    "geometry": {"type": "box", "size": [0.8, 0.8, 0.05]},
    "meta": {},
}


def test_missing_file_is_empty(tmp_path):
    store = ConfigStore(str(tmp_path))
    assert store.get_matching("config/frames/**") == {}
    assert store.get_matching("config/frames/table") == {}


def test_set_and_get_exact_and_glob(tmp_path):
    store = ConfigStore(str(tmp_path))
    rev = store.set("config/frames/table", dict(FRAME))
    assert rev == 1

    exact = store.get_matching("config/frames/table")
    assert list(exact) == ["config/frames/table"]
    flat = exact["config/frames/table"]
    assert flat["parent"] == "world"
    assert flat["xyz"] == FRAME["xyz"]
    assert flat["revision"] == 1
    assert isinstance(flat["t"], int) and flat["t"] > 0

    glob = store.get_matching("config/frames/**")
    assert list(glob) == ["config/frames/table"]
    assert store.get_matching("config/poses/**") == {}
    # prefix match, not substring: a frames glob never matches poses keys
    store.set("config/poses/home", dict(POSE))
    assert list(store.get_matching("config/frames/**")) == ["config/frames/table"]


def test_revision_increments_on_overwrite(tmp_path):
    store = ConfigStore(str(tmp_path))
    assert store.set("config/poses/home", dict(POSE)) == 1
    assert store.set("config/poses/home", dict(POSE, q=[0.0] * 6)) == 2
    flat = store.get_matching("config/poses/home")["config/poses/home"]
    assert flat["revision"] == 2
    assert flat["q"] == [0.0] * 6


def test_history_jsonl_one_line_per_set(tmp_path):
    store = ConfigStore(str(tmp_path))
    store.set("config/poses/home", dict(POSE))
    store.set("config/poses/home", dict(POSE, q=[0.0] * 6))

    lines = [
        json.loads(line)
        for line in (tmp_path / "history.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(lines) == 2
    assert lines[0]["key"] == "config/poses/home"
    assert lines[0]["old"] is None
    assert lines[0]["new"]["q"] == POSE["q"]
    assert lines[0]["revision"] == 1
    assert lines[1]["old"]["q"] == POSE["q"]
    assert lines[1]["new"]["q"] == [0.0] * 6
    assert lines[1]["revision"] == 2


def test_rejects_invalid_key(tmp_path):
    store = ConfigStore(str(tmp_path))
    with pytest.raises(ValueError, match="^invalid_key:"):
        store.set("config/other/thing", {"a": 1})


def test_rejects_unknown_parent(tmp_path):
    store = ConfigStore(str(tmp_path))
    with pytest.raises(ValueError, match="^unknown_parent:nope"):
        store.set("config/frames/x", dict(FRAME, parent="nope"))


def test_rejects_frame_cycle(tmp_path):
    store = ConfigStore(str(tmp_path))
    store.set("config/frames/x", dict(FRAME))
    store.set("config/frames/y", dict(FRAME, parent="x"))
    with pytest.raises(ValueError, match="^cycle:"):
        store.set("config/frames/x", dict(FRAME, parent="y"))


def test_rejects_bad_pose(tmp_path):
    store = ConfigStore(str(tmp_path))
    with pytest.raises(ValueError, match="^bad_pose:"):
        store.set("config/poses/p", {"q": [0.0, 1.0]})


def test_rejects_reserved_tcp_name(tmp_path):
    store = ConfigStore(str(tmp_path))
    with pytest.raises(ValueError, match="^reserved_name:flange"):
        store.set("config/arm/r1/tcp/flange", dict(TCP))


def test_scene_set_and_get(tmp_path):
    store = ConfigStore(str(tmp_path))
    assert store.set("config/scene/table", dict(SCENE)) == 1
    flat = store.get_matching("config/scene/table")["config/scene/table"]
    assert flat["frame"] == "table"
    assert flat["geometry"]["type"] == "box"
    assert flat["revision"] == 1


def test_scene_empty_glob_is_empty(tmp_path):
    store = ConfigStore(str(tmp_path))
    assert store.get_matching("config/scene/**") == {}


def test_rejects_bad_scene_geometry(tmp_path):
    store = ConfigStore(str(tmp_path))
    bad = dict(SCENE, geometry={"type": "torus"})
    with pytest.raises(ValueError, match="^bad_geometry:type"):
        store.set("config/scene/x", bad)


def test_persistence_round_trip(tmp_path):
    store = ConfigStore(str(tmp_path))
    store.set("config/frames/table", dict(FRAME))
    store.set("config/arm/r1/tcp/tool0", dict(TCP))
    store.set("config/arm/r1/tcp/tool0", dict(TCP, xyz=[0.0, 0.0, 0.2]))

    reloaded = ConfigStore(str(tmp_path))
    tcp = reloaded.get_matching("config/arm/r1/tcp/**")["config/arm/r1/tcp/tool0"]
    assert tcp["revision"] == 2
    assert tcp["xyz"] == [0.0, 0.0, 0.2]
    frame = reloaded.get_matching("config/frames/table")["config/frames/table"]
    assert frame["revision"] == 1
    assert frame["parent"] == "world"
    # revisions keep counting after reload
    assert reloaded.set("config/arm/r1/tcp/tool0", dict(TCP)) == 3


def test_delete_removes_entry(tmp_path):
    store = ConfigStore(str(tmp_path))
    store.set("config/poses/home", dict(POSE))
    assert store.get_matching("config/poses/home") != {}
    store.delete("config/poses/home")
    assert store.get_matching("config/poses/home") == {}


def test_delete_unknown_key(tmp_path):
    store = ConfigStore(str(tmp_path))
    with pytest.raises(ValueError, match="^not_found:"):
        store.delete("config/poses/missing")


def test_delete_invalid_key(tmp_path):
    store = ConfigStore(str(tmp_path))
    with pytest.raises(ValueError, match="^invalid_key:"):
        store.delete("config/other/thing")


def test_delete_frame_in_use(tmp_path):
    store = ConfigStore(str(tmp_path))
    store.set("config/frames/a", dict(FRAME, parent="world"))
    store.set("config/frames/b", dict(FRAME, parent="a"))
    with pytest.raises(ValueError, match="^in_use:"):
        store.delete("config/frames/a")
    store.delete("config/frames/b")
    store.delete("config/frames/a")
    assert store.get_matching("config/frames/**") == {}


def test_delete_history_line(tmp_path):
    store = ConfigStore(str(tmp_path))
    store.set("config/poses/home", dict(POSE))
    store.delete("config/poses/home")

    lines = [
        json.loads(line)
        for line in (tmp_path / "history.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    last = lines[-1]
    assert last["key"] == "config/poses/home"
    assert last["new"] is None


def test_delete_persists(tmp_path):
    store = ConfigStore(str(tmp_path))
    store.set("config/poses/home", dict(POSE))
    store.delete("config/poses/home")

    reloaded = ConfigStore(str(tmp_path))
    assert reloaded.get_matching("config/poses/home") == {}


_INTRINSICS = {"fx": 900.0, "fy": 900.0, "cx": 639.5, "cy": 399.5, "w": 1280, "h": 800}


_CAMERA_INFO = {
    "width": 1280, "height": 800, "distortion_model": "plumb_bob",
    "D": [0.1, -0.2, 0.0, 0.0, 0.0],
    "K": [900.0, 0.0, 639.5, 0.0, 900.0, 399.5, 0.0, 0.0, 1.0],
}


def test_intrinsics_legacy_shape_is_normalized_to_camera_info(tmp_path):
    store = ConfigStore(str(tmp_path))
    assert store.set("config/intrinsics/cam0", dict(_INTRINSICS)) == 1
    flat = store.get_matching("config/intrinsics/cam0")["config/intrinsics/cam0"]
    assert flat["width"] == 1280 and flat["height"] == 800
    assert flat["K"][0] == 900.0 and flat["K"][2] == 639.5 and flat["K"][5] == 399.5
    assert flat["D"] == [] and flat["distortion_model"] == "plumb_bob"
    assert "fx" not in flat
    assert flat["revision"] == 1


def test_intrinsics_camera_info_round_trip_and_migration(tmp_path):
    store = ConfigStore(str(tmp_path))
    assert store.set("config/intrinsics/cam0", dict(_CAMERA_INFO)) == 1
    flat = store.get_matching("config/intrinsics/cam0")["config/intrinsics/cam0"]
    assert flat["D"] == [0.1, -0.2, 0.0, 0.0, 0.0]
    assert flat["R"] == [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    # a legacy entry already on disk is migrated once at load
    import yaml
    path = tmp_path / "store.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["config/intrinsics/old"] = {"value": dict(_INTRINSICS), "revision": 3, "t": 5}
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    reloaded = ConfigStore(str(tmp_path))
    old = reloaded.get_matching("config/intrinsics/old")["config/intrinsics/old"]
    assert old["K"][4] == 900.0 and old["revision"] == 3
    with pytest.raises(ValueError, match="^bad_intrinsics:distortion_model"):
        store.set("config/intrinsics/cam0", dict(_CAMERA_INFO, distortion_model="fisheye_v9"))
    with pytest.raises(ValueError, match="^bad_intrinsics:K"):
        store.set("config/intrinsics/cam0", dict(_CAMERA_INFO, K=[1, 2, 3]))


def test_intrinsics_empty_glob_is_empty(tmp_path):
    store = ConfigStore(str(tmp_path))
    assert store.get_matching("config/intrinsics/**") == {}


def test_intrinsics_rejects_nonpositive_fx(tmp_path):
    store = ConfigStore(str(tmp_path))
    bad = dict(_INTRINSICS, fx=0.0)
    with pytest.raises(ValueError, match="^bad_intrinsics:fx"):
        store.set("config/intrinsics/cam0", bad)


def test_intrinsics_rejects_float_w(tmp_path):
    store = ConfigStore(str(tmp_path))
    bad = dict(_INTRINSICS, w=1280.5)
    with pytest.raises(ValueError, match="^bad_intrinsics:width"):
        store.set("config/intrinsics/cam0", bad)


# ── frames: nominal vs calibrated ─────────────────────────────────────────


def test_manual_frame_write_sets_nominal_and_drops_calibration(tmp_path):
    store = ConfigStore(str(tmp_path))
    store.set("config/frames/tray", {"parent": "world", "xyz": [1.0, 0.0, 0.0], "quat": [0, 0, 0, 1]})
    flat = store.get_matching("config/frames/tray")["config/frames/tray"]
    assert flat["source"] == "manual"
    assert flat["nominal"] == {"xyz": [1.0, 0.0, 0.0], "quat": [0.0, 0.0, 0.0, 1.0]}
    assert "calibration" not in flat


def test_calibration_write_keeps_nominal_and_stamps_calibration(tmp_path):
    store = ConfigStore(str(tmp_path))
    store.set("config/frames/tray", {"parent": "world", "xyz": [1.0, 0.0, 0.0], "quat": [0, 0, 0, 1]})
    store.set(
        "config/frames/tray",
        {"parent": "world", "xyz": [1.002, 0.001, 0.0], "quat": [0, 0, 0, 1],
         "source": "calibration", "calibration": {"method": "board", "residual": 0.0004}},
    )
    flat = store.get_matching("config/frames/tray")["config/frames/tray"]
    assert flat["xyz"] == [1.002, 0.001, 0.0]                      # effective = calibrated
    assert flat["nominal"]["xyz"] == [1.0, 0.0, 0.0]                # design value kept
    assert flat["calibration"]["method"] == "board" and flat["calibration"]["t"] > 0
    from wf.core.frametree import FrameDef
    fd = FrameDef.from_wire(flat)
    dx, da = fd.drift()
    assert abs(dx - (0.002**2 + 0.001**2) ** 0.5) < 1e-9 and da < 1e-9
    # a later manual re-teach becomes the new nominal and clears the calibration
    store.set("config/frames/tray", {"parent": "world", "xyz": [1.1, 0.0, 0.0], "quat": [0, 0, 0, 1]})
    flat = store.get_matching("config/frames/tray")["config/frames/tray"]
    assert flat["nominal"]["xyz"] == [1.1, 0.0, 0.0] and "calibration" not in flat


def test_calibration_write_of_new_frame_uses_itself_as_nominal(tmp_path):
    store = ConfigStore(str(tmp_path))
    store.set("config/frames/new", {"parent": "world", "xyz": [0.5, 0, 0], "quat": [0, 0, 0, 1], "source": "calibration"})
    flat = store.get_matching("config/frames/new")["config/frames/new"]
    assert flat["nominal"]["xyz"] == [0.5, 0.0, 0.0] and "calibration" in flat


def test_frame_rejects_bad_nominal(tmp_path):
    store = ConfigStore(str(tmp_path))
    with pytest.raises(ValueError, match="^bad_frame:nominal"):
        store.set("config/frames/x", {"parent": "world", "xyz": [0, 0, 0], "quat": [0, 0, 0, 1], "nominal": {"xyz": [1]}})


# ── collision exceptions ──────────────────────────────────────────────────


def test_collision_disabled_pairs_family(tmp_path):
    store = ConfigStore(str(tmp_path))
    key = "config/arm/r1/collision/disabled_pairs"
    assert store.set(key, {"pairs": [{"a": "wrist3_Link", "b": "gripper", "reason": "rigid mount"}]}) == 1
    flat = store.get_matching("config/arm/**")[key]
    assert flat["pairs"][0]["a"] == "wrist3_Link"
    with pytest.raises(ValueError, match="^bad_collision:pairs must be a list"):
        store.set(key, {"pairs": "x"})
    with pytest.raises(ValueError, match="must differ"):
        store.set(key, {"pairs": [{"a": "x", "b": "x"}]})
    with pytest.raises(ValueError, match="^invalid_key"):
        store.set("config/arm/r1/collision/other", {"pairs": []})
