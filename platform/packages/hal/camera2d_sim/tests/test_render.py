"""Unit tests for the pyrender scene-graph renderer (design §5.4).

These REQUIRE the OSMesa render backend (Linux/Docker only), so they
``importorskip`` pyrender and skip when ``OffscreenRenderer`` cannot construct
(Windows/osx dev hosts). The load-bearing check is preserved from the cv2 era:
a top-down render of the shared ``calib_board.glb`` is a geometrically correct
projection through the calibrated intrinsics — ``cv2.findChessboardCorners``
recovers the inner-corner grid, exactly what the calibration phases rely on.
Also covers eye-in-hand pose composition and the empty-scene background.
"""

import cv2
import numpy as np
import pytest

from wf.core.frametree import FrameTree
from wf.core.scene import SceneObject

# pyrender's package import pulls OpenGL.GL, which fails on a host without a GL
# backend (Windows/osx) — and not always with ImportError (PyOpenGL raises
# TypeError when no platform plugin loads). importorskip only catches
# ImportError, so guard the whole import and skip the module on ANY failure.
# The renderer itself imports pyrender lazily; this is only the test's gate.
try:
    import pyrender  # noqa: F401
except BaseException as _exc:  # noqa: BLE001 — any backend-absent failure skips
    pytest.skip(
        f"pyrender render backend unavailable: {_exc!r}",
        allow_module_level=True,
    )

from wf.hal.camera2d_sim.render import Renderer  # noqa: E402

# Inner-corner grid for findChessboardCorners is (squares_x-1, squares_y-1).
# calib_board.glb is a 7x5-square board -> 6x4 inner corners.
_NX, _NY = 7, 5
_PATTERN = (_NX - 1, _NY - 1)
_BOARD_URI = "asset://wf/calib_board.glb"


def _cfg(**over) -> dict:
    cfg = {
        "width": 1280,
        "height": 800,
        "fx": 900.0,
        "fy": 900.0,
        "cx": None,
        "cy": None,
        "background_gray": 90,
        "mount_xyz": [0.0, 0.0, 0.05],
        "mount_rpy_deg": [0.0, 0.0, 0.0],
        # Fallback look-at target: the board lies at the origin; camera 0.5 m up.
        "board_xyz": [0.0, 0.0, 0.0],
        "fallback_height_m": 0.5,
    }
    cfg.update(over)
    return cfg


class _Scene:
    """In-memory LiveSceneList stand-in: a fixed object list."""

    def __init__(self, objs):
        self._objs = list(objs)

    def snapshot(self):
        return list(self._objs)


class _Frames:
    """In-memory LiveFrameTree stand-in returning an empty (identity) tree."""

    def snapshot(self):
        return FrameTree({})


def _board_obj(frame="world", xyz=(0.0, 0.0, 0.0)) -> SceneObject:
    return SceneObject(
        frame=frame,
        xyz=list(xyz),
        quat=[0.0, 0.0, 0.0, 1.0],
        geometry={"type": "mesh", "uri": _BOARD_URI},
    )


def _make(**over) -> Renderer:
    """Build a Renderer, skipping the test if the OSMesa backend is absent."""
    try:
        return Renderer(
            _cfg(**over),
            live_scene=_Scene([_board_obj()]),
            live_frames=_Frames(),
            base_frame="world",
        )
    except RuntimeError as exc:
        pytest.skip(f"render backend unavailable: {exc}")


def _find_corners(bgr: np.ndarray):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCorners(
        gray,
        _PATTERN,
        flags=cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE,
    )
    return found, corners


def test_render_shape_and_dtype():
    img = _make().render()
    assert img.shape == (800, 1280, 3)
    assert img.dtype == np.uint8


def test_fallback_render_shows_board():
    # No flange -> fixed top-down pose over the board. The board must be
    # visible (not an all-background frame).
    img = _make().render()
    assert img.max() > img.min(), "rendered frame is uniform background"


def test_fallback_render_detects_checkerboard():
    # Projection must be correct enough for cv2 to recover all inner corners
    # from the shared glb's checkerboard top face.
    img = _make().render()
    found, corners = _find_corners(img)
    assert found, "checkerboard not detected in the top-down render"
    assert corners.shape[0] == _PATTERN[0] * _PATTERN[1]


def test_eye_in_hand_pose_matches_explicit_top_down():
    # A flange pose whose flange->optical mount reproduces the fallback
    # top-down view must render an equally-detectable board.
    r = _make(mount_xyz=[0.0, 0.0, 0.0], mount_rpy_deg=[180.0, 0.0, 0.0])
    flange_xyz = [0.0, 0.0, 0.5]
    flange_quat = [0.0, 0.0, 0.0, 1.0]  # identity: flange axes == world axes
    img = r.render(flange_xyz, flange_quat)
    found, _ = _find_corners(img)
    assert found, "checkerboard not detected from the eye-in-hand pose"


def test_camera_pose_composes_flange_and_mount():
    r = _make(mount_xyz=[0.1, 0.0, 0.0], mount_rpy_deg=[0.0, 0.0, 0.0])
    pose = r.camera_pose([1.0, 2.0, 3.0], [0.0, 0.0, 0.0, 1.0])
    # Identity flange rotation -> optical origin = flange + mount offset.
    assert np.allclose(pose[:3, 3], [1.1, 2.0, 3.0])


def test_camera_pose_decomposes_to_header_pose():
    # The sim driver stamps transform_to_xyz_quat(renderer.camera_pose(...)) into
    # the FrameHeader; the decomposed xyz must equal the matrix translation.
    from wf.core.frames import transform_to_xyz_quat

    r = _make(mount_xyz=[0.1, 0.0, 0.05], mount_rpy_deg=[0.0, 0.0, 0.0])
    T = r.camera_pose([1.0, 2.0, 3.0], [0.0, 0.0, 0.0, 1.0])
    xyz, quat = transform_to_xyz_quat(T)
    assert np.allclose(xyz, T[:3, 3])
    assert np.allclose(xyz, [1.1, 2.0, 3.05])
    assert len(quat) == 4


def test_board_behind_camera_renders_background():
    # Camera at the board, optical +Z pointing UP (away from the board on the
    # floor) -> nothing in view; only the background remains.
    r = _make(mount_xyz=[0.0, 0.0, 0.0], mount_rpy_deg=[0.0, 0.0, 0.0])
    img = r.render([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])
    found, _ = _find_corners(img)
    assert not found, "board must not be detected when behind the camera"


def test_empty_scene_renders_background():
    try:
        r = Renderer(
            _cfg(),
            live_scene=_Scene([]),
            live_frames=_Frames(),
            base_frame="world",
        )
    except RuntimeError as exc:
        pytest.skip(f"render backend unavailable: {exc}")
    img = r.render()
    bg = 90
    # Uniform background fill (no objects): every pixel ~= background gray.
    assert int(img.min()) >= bg - 2 and int(img.max()) <= bg + 2


def test_mesh_asset_parsed_once_across_frames(monkeypatch):
    """A `mesh` scene object is parsed once and reused across frames, never
    re-loaded per render. The stream loop renders at rate_hz, so a per-frame
    trimesh.load of the shared GLB would re-parse + rebuild buffers 15x/s."""
    import wf.hal.camera2d_sim.render as render_mod

    loads = 0
    real = render_mod._object_mesh

    def counting(geom):
        nonlocal loads
        if geom.get("type") == "mesh":
            loads += 1
        return real(geom)

    monkeypatch.setattr(render_mod, "_object_mesh", counting)
    r = _make()
    r.render()
    r.render()
    r.render()
    assert loads == 1


def test_flange_frame_object_skipped(monkeypatch):
    """A tool mounted on THIS camera's own flange (frame == arm/r1/flange) is
    omitted from the eye-in-hand sensor image. The explicit skip drops it BEFORE
    any mesh load, so a flange-only scene triggers zero asset loads (proving the
    skip, not the unknown-frame fallback, omits it)."""
    import wf.hal.camera2d_sim.render as render_mod

    loads = 0
    real = render_mod._object_mesh

    def counting(geom):
        nonlocal loads
        loads += 1
        return real(geom)

    monkeypatch.setattr(render_mod, "_object_mesh", counting)
    tool = SceneObject(
        frame="arm/r1/flange",
        xyz=[0.0, 0.0, 0.0],
        quat=[0.0, 0.0, 0.0, 1.0],
        geometry={"type": "mesh", "uri": "asset://wf/1723-4811-76.glb"},
        meta={"name": "scene/tool"},
    )
    try:
        r = Renderer(
            _cfg(), live_scene=_Scene([tool]), live_frames=_Frames(),
            base_frame="world",
        )
    except RuntimeError as exc:
        pytest.skip(f"render backend unavailable: {exc}")
    r.render()
    assert loads == 0, "flange tool must be skipped before any mesh load"
