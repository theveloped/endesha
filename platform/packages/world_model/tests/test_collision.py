"""CollisionModel + preflight tests (Pinocchio + Coal engine, design §5.10).

Behaviour assertions only — collision-free home, real self-collision, scene
hit/miss, frame-parented obstacles, min-distance witnesses, and the
``preflight`` -> ``collision:{a}|{b}`` reason mapping. No zenoh.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from wf.core.frametree import FrameDef, FrameTree
from wf.core.scene import SceneObject
from wf.hal.aubo_i10 import BUNDLED_URDF
from wf.world_model.collision import CollisionModel
from wf.world_model.fk import UrdfFk
from wf.world_model.preflight import preflight

HOME_Q = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]
# within ±3.04 limits, but folds the forearm back into the shoulder.
SELF_COLLIDE_Q = [0.0, 0.0, 3.0, 3.0, 0.0, 0.0]
BASE = "arm/r1/base"
_TABLE_XYZ = [0.6, 0.0, 0.0]


@pytest.fixture(scope="module")
def model() -> CollisionModel:
    return CollisionModel(BUNDLED_URDF, BUNDLED_URDF.parent.parent)


@pytest.fixture(scope="module")
def fk() -> UrdfFk:
    return UrdfFk(BUNDLED_URDF)


@pytest.fixture()
def tree() -> FrameTree:
    return FrameTree(
        {
            "arm/r1/base": FrameDef(parent="world", xyz=[0, 0, 0], quat=[0, 0, 0, 1]),
            "table": FrameDef(parent="world", xyz=_TABLE_XYZ, quat=[0, 0, 0, 1]),
        }
    )


def _box(frame, xyz, size=(0.3, 0.3, 0.3), name=None, collision=True):
    meta = {}
    if name:
        meta["name"] = name
    if not collision:
        meta["collision"] = False
    return SceneObject(
        frame=frame,
        xyz=list(xyz),
        quat=[0, 0, 0, 1],
        geometry={"type": "box", "size": list(size)},
        meta=meta,
    )


# ── robot self-collision ──────────────────────────────────────────────────


def test_home_is_collision_free(model, tree):
    result = model.check_collision(HOME_Q, [], tree, BASE)
    assert result["hit"] is False
    assert result["pairs"] == []


def test_self_collision_detected(model, tree):
    result = model.check_collision(SELF_COLLIDE_Q, [], tree, BASE)
    assert result["hit"] is True
    # the colliding pair is two non-adjacent robot links (no scene names).
    a, b = result["pairs"][0]
    assert not a.startswith("scene/")
    assert not b.startswith("scene/")
    links = set(UrdfFk.LINK_ORDER)
    assert a in links and b in links


# ── scene obstacles ───────────────────────────────────────────────────────


def test_scene_box_hit(model, fk, tree):
    flange = fk.get_ee_transform(HOME_Q)[:3, 3]
    box = _box(BASE, flange, name="scene/blocker")
    result = model.check_collision(HOME_Q, [box], tree, BASE)
    assert result["hit"] is True
    # at least one pair is (robot link, scene/blocker) in some order.
    assert any("scene/blocker" in pair for pair in result["pairs"])
    link, obs = next(
        p if p[1] == "scene/blocker" else (p[1], p[0])
        for p in result["pairs"]
        if "scene/blocker" in p
    )
    assert link in set(UrdfFk.LINK_ORDER)
    assert obs == "scene/blocker"


def test_declared_exception_disables_pair(model, fk, tree):
    """SRDF-style disable_collisions: a whitelisted (link, obstacle) pair no
    longer reports, other pairs still do."""
    flange = fk.get_ee_transform(HOME_Q)[:3, 3]
    box = _box(BASE, flange, name="scene/blocker")
    hit = model.check_collision(HOME_Q, [box], tree, BASE)
    assert hit["hit"] is True
    links = {p[0] if p[1] == "scene/blocker" else p[1] for p in hit["pairs"] if "scene/blocker" in p}
    model.set_disabled_pairs([(link, "scene/blocker") for link in links])
    assert model.disabled_pairs == sorted(tuple(sorted((l, "scene/blocker"))) for l in links)
    cleared = model.check_collision(HOME_Q, [box], tree, BASE)
    assert not any("scene/blocker" in p for p in cleared["pairs"])
    # self-collision pairs are unaffected until declared
    assert model.check_collision(SELF_COLLIDE_Q, [], tree, BASE)["hit"] is True
    a, b = model.check_collision(SELF_COLLIDE_Q, [], tree, BASE)["pairs"][0]
    model.set_disabled_pairs([(a, b)])
    still = model.check_collision(SELF_COLLIDE_Q, [], tree, BASE)
    assert (a, b) not in still["pairs"] and (b, a) not in still["pairs"]
    model.set_disabled_pairs([])
    assert model.disabled_pairs == []


def test_scene_box_miss(model, fk, tree):
    flange = fk.get_ee_transform(HOME_Q)[:3, 3]
    box = _box(BASE, [flange[0] + 5.0, flange[1], flange[2]])
    result = model.check_collision(HOME_Q, [box], tree, BASE)
    assert result["hit"] is False


def test_scene_object_collision_opt_out(model, fk, tree):
    """A scene object with ``meta.collision == False`` renders everywhere but is
    excluded from collision — the robot mount sits on ``base_link`` by
    construction, so it must never report a permanent contact."""
    flange = fk.get_ee_transform(HOME_Q)[:3, 3]
    on = _box(BASE, flange, name="scene/mount")
    assert model.check_collision(HOME_Q, [on], tree, BASE)["hit"] is True
    off = _box(BASE, flange, name="scene/mount", collision=False)
    assert model.check_collision(HOME_Q, [off], tree, BASE)["hit"] is False


def test_frame_parented_obstacle_resolved_through_tree(model, fk, tree):
    """A box parented to ``table`` collides only once the table offset places
    it on the arm — proving the tree-transform path, not just base objects."""
    flange = fk.get_ee_transform(HOME_Q)[:3, 3]
    # table frame is at +0.6 x; offset the box back by 0.6 so it lands on the
    # flange in world/base — collides.
    on_arm = _box(
        "table", [flange[0] - _TABLE_XYZ[0], flange[1], flange[2]], name="scene/onTable"
    )
    assert model.check_collision(HOME_Q, [on_arm], tree, BASE)["hit"] is True
    # same local offset but NOT compensating for the table frame -> 0.6 m away,
    # clear of the arm.
    off_arm = _box("table", [flange[0], flange[1], flange[2]], name="scene/onTable")
    assert model.check_collision(HOME_Q, [off_arm], tree, BASE)["hit"] is False


def test_scene_box_on_dynamic_frame_collides_then_skipped(model, fk):
    """A box parented to a DYNAMIC frame collides only when the live sample
    places the frame on the arm, and is skipped (no hit, no raise) once the
    dynamic frame is removed — proving dynamic obstacles flow through the live
    tree and the ``_build_scene`` FrameUnknown-skip."""
    from wf.core.frametree import DynamicFrameSample, FrameDef
    from wf.world_model.frames_live import LiveFrameTree

    flange = fk.get_ee_transform(HOME_Q)[:3, 3]
    live = LiveFrameTree(
        {"arm/r1/base": FrameDef(parent="world", xyz=[0, 0, 0], quat=[0, 0, 0, 1])}
    )
    # detected frame sits on the flange (world == base here) -> box at frame
    # origin lands on the arm.
    live.update(
        "det_1",
        DynamicFrameSample(
            t=1, parent="world", xyz=list(flange), quat=[0, 0, 0, 1]
        ),
    )
    box = _box("det_1", [0.0, 0.0, 0.0], name="scene/det")
    assert model.check_collision(HOME_Q, [box], live.snapshot(), BASE)["hit"] is True

    # detection gone: the obstacle's frame is unknown -> object skipped, no hit.
    live.update("det_1", None)
    result = model.check_collision(HOME_Q, [box], live.snapshot(), BASE)
    assert result["hit"] is False


def test_imported_object_drives_collision_then_cleared(model, fk):
    """An object instantiated by the importer, viewed through the live frame +
    scene layers, is a real obstacle: preflight returns ``collision:`` while it
    is present and clears once the live scene object is tombstoned — proving the
    imported scene drives the live collision authority."""
    from wf.core.cad_object import ObjectDef, instantiate
    from wf.world_model.frames_live import LiveFrameTree
    from wf.world_model.scene_live import LiveSceneList

    flange = fk.get_ee_transform(HOME_Q)[:3, 3]
    obj = ObjectDef.from_wire(
        {
            "name": "blocker_obj",
            "units": "m",
            "collision": [
                {
                    "xyz": [0.0, 0.0, 0.0],
                    "quat": [0, 0, 0, 1],
                    "geometry": {"type": "box", "size": [0.3, 0.3, 0.3]},
                }
            ],
        }
    )
    # place the instance root on the flange (world == base here).
    frames, scene = instantiate(
        obj, instance="b1", parent_frame="world",
        xyz=list(flange), quat=[0, 0, 0, 1],
    )
    live_frames = LiveFrameTree(
        {"arm/r1/base": FrameDef(parent="world", xyz=[0, 0, 0], quat=[0, 0, 0, 1])}
    )
    for name, fd in frames.items():
        from wf.core.frametree import DynamicFrameSample

        live_frames.update(
            name,
            DynamicFrameSample(
                t=1, parent=fd.parent, xyz=fd.xyz, quat=fd.quat, source=fd.source
            ),
        )
    live_scene = LiveSceneList({})
    for name, so in scene.items():
        live_scene.update(name, so)

    resolution = {"waypoints": [{"resolved_q": HOME_Q}]}
    reason = preflight(
        resolution, live_scene.snapshot(),
        model=model, tree=live_frames.snapshot(), base_frame=BASE,
    )
    assert reason is not None and reason.startswith("collision:")

    # tombstone the imported scene object -> obstacle gone -> clear.
    live_scene.update("b1/0", None)
    reason = preflight(
        resolution, live_scene.snapshot(),
        model=model, tree=live_frames.snapshot(), base_frame=BASE,
    )
    assert reason is None


# ── min_distance ──────────────────────────────────────────────────────────


def test_min_distance_returns_finite_with_witness(model, tree):
    result = model.min_distance(HOME_Q, [], tree, BASE)
    assert np.isfinite(result["d"])
    assert result["pair"] is not None
    p_a, p_b = result["witness"]
    assert p_a.shape == (3,)
    assert p_b.shape == (3,)


def test_min_distance_to_nearby_box(model, fk, tree):
    flange = fk.get_ee_transform(HOME_Q)[:3, 3]
    # a small box ~0.2 m beyond the flange along +x: near but not touching.
    gap_box = _box(
        BASE, [flange[0] + 0.4, flange[1], flange[2]], size=(0.1, 0.1, 0.1),
        name="scene/near",
    )
    result = model.min_distance(HOME_Q, [gap_box], tree, BASE)
    assert result["d"] > 0
    assert result["pair"] is not None
    p_a, p_b = result["witness"]
    assert p_a.shape == (3,) and p_b.shape == (3,)


# ── preflight reason mapping ──────────────────────────────────────────────


def test_preflight_maps_hit_to_collision_reason(model, fk, tree):
    flange = fk.get_ee_transform(HOME_Q)[:3, 3]
    box = _box(BASE, flange, name="scene/blocker")
    reason = preflight(
        {"waypoints": [{"resolved_q": HOME_Q}]},
        [box],
        model=model,
        tree=tree,
        base_frame=BASE,
    )
    assert reason is not None
    assert reason.startswith("collision:")
    assert "|" in reason


def test_preflight_clear_returns_none(model, tree):
    reason = preflight(
        {"waypoints": [{"resolved_q": HOME_Q}]},
        [],
        model=model,
        tree=tree,
        base_frame=BASE,
    )
    assert reason is None


def test_preflight_reports_first_violation_index(model, fk, tree):
    flange = fk.get_ee_transform(HOME_Q)[:3, 3]
    box = _box(BASE, flange, name="scene/blocker")
    # waypoint 0 clear (arm folded away), waypoint 1 home -> into the box.
    result = model.preflight([SELF_COLLIDE_Q, HOME_Q], [], tree, BASE)
    # the folded pose self-collides first.
    assert result["ok"] is False
    assert result["first_violation"]["index"] == 0


# ── shared asset:// mesh loading ───────────────────────────────────────────


def _mesh(uri: str) -> SceneObject:
    return SceneObject(
        frame="world", xyz=[0, 0, 0], quat=[0, 0, 0, 1],
        geometry={"type": "mesh", "uri": uri},
    )


def test_scene_mesh_loads_shared_glb():
    """A `mesh` object with an `asset://wf/...` uri resolves + loads via Coal."""
    from wf.world_model.collision import _scene_geometry

    geom = _scene_geometry(_mesh("asset://wf/calib_board.glb"))
    assert geom is not None


def test_scene_mesh_missing_asset_skipped():
    """A missing/unloadable asset returns None (skipped), never raises."""
    from wf.world_model.collision import _scene_geometry

    assert _scene_geometry(_mesh("asset://wf/missing.glb")) is None


# ── imported CAD cell scene (scripts/import_cell_stl.py) ───────────────────


_STORE = Path(__file__).resolve().parents[3] / "deploy" / "config" / "store.yaml"


def _scene_objects(prefix: str = "config/scene/") -> list[SceneObject]:
    """``config/scene/**`` objects from the deploy store (prefix-filtered)."""
    entries = yaml.safe_load(_STORE.read_text())
    return [
        SceneObject.from_wire(v["value"])
        for k, v in entries.items()
        if k.startswith(prefix)
    ]


def _cell_frames() -> FrameTree:
    """The frame tree from the deploy store, incl. the imported robot base
    (``arm/r1/base`` = T_R), so world-frame scene poses resolve to the robot."""
    entries = yaml.safe_load(_STORE.read_text())
    defs = {
        k[len("config/frames/") :]: v["value"]
        for k, v in entries.items()
        if k.startswith("config/frames/")
    }
    return FrameTree.from_wire(defs)


def test_cell_scene_loads(model):
    """The CAD-imported cell GLBs resolve + load through Coal and pose into a
    real collision query. Scene objects are in WORLD coords and the robot base
    (``arm/r1/base`` = T_R) is a SEPARATE frame, so collision resolves each
    object relative to the robot via the tree (design §5.10 shared asset)."""
    from wf.world_model.collision import _scene_geometry

    cell = _scene_objects("config/scene/cell/")
    assert len(cell) == 7  # 5 meshes; the 1590 bracket is placed x3
    for obj in cell:
        assert _scene_geometry(obj) is not None, (
            f"cell mesh failed to load: {obj.geometry['uri']}"
        )

    # Exactly what preflight checks: the FULL config/scene/** posed against the
    # robot base. The mount (pedestal at base_link) is collision-excluded, so
    # the home config is clear of the whole cell — no permanent false-positive.
    tree = _cell_frames()
    result = model.check_collision(HOME_Q, _scene_objects(), tree, "arm/r1/base")
    assert isinstance(result, dict)
    assert result["hit"] is False, f"unexpected collision: {result['pairs']}"

# ── flange-mounted end-of-arm tool (frame == arm/r1/flange) ────────────────


_TOOL_URI = "asset://wf/1723-4811-76.glb"


def _flange_tool(name="scene/tool", xyz=(0, 0, 0), quat=(0, 0, 0, 1)):
    """A mesh tool posed in the dynamic flange frame (tool-changer mount)."""
    return SceneObject(
        frame="arm/r1/flange",
        xyz=list(xyz),
        quat=list(quat),
        geometry={"type": "mesh", "uri": _TOOL_URI},
        meta={"name": name},
    )


def test_flange_tool_no_false_positive_with_flange(model, tree):
    """A tool rigidly mounted on the flange must NOT report a permanent
    self-collision against the flange it is attached to. Home stays collision-
    free with the tool present (the rigid mount is excluded from the pairs)."""
    result = model.check_collision(HOME_Q, [_flange_tool()], tree, BASE)
    assert result["hit"] is False, f"unexpected collision: {result['pairs']}"


def test_flange_tool_moves_with_arm_and_hits_obstacle(model, fk, tree):
    """The tool is attached to the flange JOINT, so FK carries it: a box placed
    where the tool reaches (10 cm out along the flange Z, beyond every arm link)
    collides with the TOOL, while the bare arm clears the same box."""
    T = fk.get_ee_transform(HOME_Q)
    box_pos = T[:3, 3] + 0.10 * T[:3, 2]
    box = _box(BASE, box_pos, size=(0.04, 0.04, 0.04), name="scene/obstacle")

    with_tool = model.check_collision(HOME_Q, [_flange_tool(), box], tree, BASE)
    assert with_tool["hit"] is True
    assert any(
        "scene/tool" in pair and "scene/obstacle" in pair
        for pair in with_tool["pairs"]
    ), with_tool["pairs"]

    # Without the tool the box is out of the bare arm's reach -> no collision,
    # proving the hit above is the tool (not a robot link).
    assert model.check_collision(HOME_Q, [box], tree, BASE)["hit"] is False


def test_flange_tool_collision_opt_out(model, fk, tree):
    """``meta.collision == False`` excludes even a flange tool from preflight
    (still rendered): the obstacle the tool would hit is ignored when opted
    out, exactly like a world-frame object."""
    T = fk.get_ee_transform(HOME_Q)
    box = _box(
        BASE, T[:3, 3] + 0.10 * T[:3, 2], size=(0.04, 0.04, 0.04),
        name="scene/obstacle",
    )
    off = _flange_tool()
    off.meta["collision"] = False
    assert model.check_collision(HOME_Q, [off, box], tree, BASE)["hit"] is False