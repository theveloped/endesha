"""pyrender scene-graph renderer for the sim camera (design §5.4).

Builds its scene every frame from the LIVE bus — the ``{realm}/scene/**``
objects and the static/dynamic frame tree, exactly the views the collision
preflight reads — and renders them through the calibrated
``IntrinsicsCamera`` posed at the eye-in-hand flange. It emits ONE color BGR
image (the same single plane the cv2 projector emitted): no depth, no
segmentation, no contract change.

Geometry comes from the SHARED ``asset://`` resolver (``wf.core.assets``), the
same resolver Coal collision uses — "share the asset, not the renderer"
(§5.10). A ``mesh`` scene object loads the shared glTF; box/cylinder/sphere
render as trimesh primitives.

Backend: pyrender over OSMesa (pure-CPU headless, Linux only). The module
imports on every platform — pyrender is imported lazily inside ``__init__`` and
``OffscreenRenderer`` construction failure raises a clear ``RuntimeError`` at
CONSTRUCTION, never at import. The Linux sim Docker container is the supported
render path.

Coordinates: scene poses resolve against ``base_frame`` (``world``). The camera
optical frame uses the OpenCV convention (+Z forward, +X right, +Y down); the
flange->optical mount and ``camera_pose`` math are unchanged from the cv2
renderer. pyrender's camera node uses the OpenGL convention (-Z forward, +Y
up), so the OpenCV optical pose is converted with the fixed ``diag(1, -1, -1)``
rotation before it becomes the camera node pose.
"""

from __future__ import annotations

import os
import threading

import numpy as np
import trimesh

from wf.core.assets import resolve_asset
from wf.core.frames import (
    make_transform,
    quaternion_to_rotation_matrix,
    rpy_deg_to_matrix,
)
from wf.core.frametree import FrameError
from wf.core.log import get_logger

# OSMesa software GL: set BEFORE pyrender/PyOpenGL import its platform module.
os.environ.setdefault("PYOPENGL_PLATFORM", "osmesa")

_log = get_logger("wf.hal.camera2d_sim.render")

# OpenCV optical (+Z fwd, +Y down) -> OpenGL camera (-Z fwd, +Y up): flip Y, Z.
_CV_TO_GL = np.diag([1.0, -1.0, -1.0, 1.0]).astype(np.float64)

# Global "sun": one directional light for scene legibility. A pyrender
# DirectionalLight emits along its local -Z, so this pose tilts -Z to point
# down and toward +X/+Y world, giving differently-oriented faces of a
# textureless mesh distinct brightness (shape cues) without blowing past the
# checkerboard's albedo-clamped black/white. Intensity is modest — the full
# ambient already lights everything; the sun only adds directional gradient.
_SUN_INTENSITY = 3.0
# Rotation taking local -Z to world (-0.4, -0.4, -1) normalized: a high sun
# raking slightly across the scene. Built once; lights are pose-only.
_SUN_POSE = make_transform(
    rpy_deg_to_matrix([-30.0, 20.0, 0.0]), [0.0, 0.0, 0.0]
)

# Scene objects in this frame are end-of-arm tools on the robot's flange. This
# is an eye-in-hand sensor MOUNTED on that same flange, so a flange tool would
# sit on the lens and occlude the view (and the static tree can't resolve the
# dynamic flange frame regardless). The collision engine and the 3D twin attach
# the tool to the flange; the sensor image omits it.
_FLANGE_FRAME = "arm/r1/flange"


def _object_mesh(geom: dict):
    """A ``trimesh`` for a scene-object geometry block, or ``None`` to skip it.

    Mirrors collision's primitive mapping; ``mesh`` loads via the SHARED
    ``asset://`` resolver. A bad/unloadable asset returns ``None`` (the frame is
    never crashed by one object), mirroring collision's skip policy.
    """
    gtype = geom.get("type")
    try:
        if gtype == "box":
            sx, sy, sz = (float(v) for v in geom["size"])
            return trimesh.creation.box(extents=(sx, sy, sz))
        if gtype == "cylinder":
            return trimesh.creation.cylinder(
                radius=float(geom["radius"]), height=float(geom["length"])
            )
        if gtype == "sphere":
            return trimesh.creation.icosphere(radius=float(geom["radius"]))
        if gtype == "mesh":
            return trimesh.load(resolve_asset(geom["uri"]))
    except Exception as exc:  # noqa: BLE001 — a bad object must not crash a frame
        _log.debug("scene mesh build failed; skipping type=%s error=%r", gtype, exc)
        return None
    return None


class Renderer:
    """pyrender scene-graph renderer: live bus scene -> BGR image at a flange pose."""

    def __init__(self, render: dict, *, live_scene, live_frames, base_frame: str):
        """``render``: merged ``params['render']`` (intrinsics + mount).

        ``live_scene``: a ``LiveSceneList`` (``.snapshot() -> list[SceneObject]``).
        ``live_frames``: a ``LiveFrameTree`` (``.snapshot() -> FrameTree``).
        ``base_frame``: world/base frame scene poses resolve against.
        """
        self.w = int(render["width"])
        self.h = int(render["height"])
        self.fx = float(render["fx"])
        self.fy = float(render["fy"])
        cx = render["cx"]
        cy = render["cy"]
        self.cx = (self.w - 1) / 2.0 if cx is None else float(cx)
        self.cy = (self.h - 1) / 2.0 if cy is None else float(cy)
        self.bg = int(render["background_gray"]) / 255.0
        self.T_flange_optical = make_transform(
            rpy_deg_to_matrix(render["mount_rpy_deg"]), render["mount_xyz"]
        )
        self._live_scene = live_scene
        self._live_frames = live_frames
        self._base_frame = base_frame
        # Shared scene meshes are immutable assets (authored once, shipped in
        # the wheel); cache the parsed trimesh per uri so the stream loop never
        # re-parses the GLB and rebuilds buffers every frame (15 Hz x N meshes).
        self._mesh_cache: dict[str, object] = {}

        # Fallback: look straight down at a point in front of the base until a
        # flange sample arrives (and for the arm-less conformance suite).
        center = np.asarray(render["board_xyz"], dtype=np.float64) + np.array(
            [0.0, 0.0, float(render["fallback_height_m"])]
        )
        R_wo = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], dtype=np.float64)
        self._fallback_T_wo = make_transform(R_wo, center)

        # The OSMesa GL context inside OffscreenRenderer is NOT thread-safe and
        # MUST be driven by one thread at a time. render() is called from both
        # the camera's stream-loop thread and the zenoh queryable thread (grab,
        # and stream start/stop restarts). Concurrent entry corrupts the VAO
        # state mid-draw -> GLError(1282, invalid operation) at
        # glVertexAttribPointer. This lock serializes every GL touch.
        self._gl_lock = threading.Lock()

        # Lazy pyrender import + offscreen renderer: keeps the module importable
        # on Windows/osx (no OSMesa). Failure here is a clear construction error.
        try:
            import pyrender  # noqa: PLC0415 — lazy: OSMesa is Linux-only

            self._pyrender = pyrender
            self._camera = pyrender.IntrinsicsCamera(
                fx=self.fx, fy=self.fy, cx=self.cx, cy=self.cy,
                znear=0.01, zfar=100.0,
            )
            self._offscreen = pyrender.OffscreenRenderer(self.w, self.h)
        except Exception as exc:  # noqa: BLE001 — surface a clear backend error
            raise RuntimeError(
                f"pyrender render backend unavailable: {exc!r}"
            ) from exc

    def camera_pose(self, flange_xyz, flange_quat) -> np.ndarray:
        """World<-optical (OpenCV) transform for a flange pose; fallback when None."""
        if flange_xyz is None or flange_quat is None:
            return self._fallback_T_wo
        T_wf = make_transform(quaternion_to_rotation_matrix(flange_quat), flange_xyz)
        return T_wf @ self.T_flange_optical

    def _mesh_for(self, geom: dict):
        """Trimesh for a geometry block, caching shared ``mesh`` asset loads.

        Primitives are cheap and rebuilt each call; a ``mesh`` uri is loaded
        once and reused across frames (the asset is static). A bad asset caches
        ``None`` so it stays skipped without re-loading every frame.
        """
        if geom.get("type") != "mesh":
            return _object_mesh(geom)
        uri = geom.get("uri")
        if not isinstance(uri, str) or not uri:
            return None
        if uri not in self._mesh_cache:
            self._mesh_cache[uri] = _object_mesh(geom)
        return self._mesh_cache[uri]

    def _build_scene(self):
        """A fresh pyrender scene from the live bus views (skips bad objects)."""
        pr = self._pyrender
        # Lighting: full white ambient keeps every surface lit at its own albedo
        # — the checkerboard's black squares (albedo 0) stay black and white
        # (albedo 1) clips to white regardless of any added light, so corner
        # detection on the calib board is unaffected. ON TOP of that ambient we
        # add one global directional "sun": colored/textureless meshes have
        # albedo < 1, leaving headroom for the sun's N·L gradient to reveal
        # their 3D form (a flat-shaded box otherwise reads as a single
        # silhouette). Ambient is the floor, the sun is shape on top.
        scene = pr.Scene(
            bg_color=[self.bg, self.bg, self.bg, 1.0],
            ambient_light=[1.0, 1.0, 1.0],
        )
        scene.add(
            pr.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=_SUN_INTENSITY),
            pose=_SUN_POSE,
        )
        try:
            frames = self._live_frames.snapshot()
        except Exception as exc:  # noqa: BLE001 — never crash a frame on the tree
            _log.debug("frame tree snapshot failed: %r", exc)
            frames = None
        for obj in self._live_scene.snapshot():
            if obj.frame == _FLANGE_FRAME:
                continue
            tm = self._mesh_for(obj.geometry)
            if tm is None:
                continue
            if frames is not None:
                try:
                    T_base_frame = frames.resolve(obj.frame, self._base_frame)
                except FrameError as exc:
                    _log.debug(
                        "scene frame unresolved; skipping frame=%s error=%r",
                        obj.frame, exc,
                    )
                    continue
            else:
                T_base_frame = np.eye(4, dtype=np.float64)
            T_world_obj = T_base_frame @ make_transform(
                quaternion_to_rotation_matrix(obj.quat), obj.xyz
            )
            self._add_trimesh(scene, tm, T_world_obj)
        return scene

    def _add_trimesh(self, scene, tm, pose: np.ndarray) -> None:
        """Add a Trimesh OR a multi-geometry Scene as posed pyrender mesh node(s)."""
        pr = self._pyrender
        if isinstance(tm, trimesh.Scene):
            for name, geom in tm.geometry.items():
                node_T = tm.graph.get(name)[0] if name in tm.graph.nodes else np.eye(4)
                scene.add(pr.Mesh.from_trimesh(geom), pose=pose @ node_T)
        else:
            scene.add(pr.Mesh.from_trimesh(tm), pose=pose)

    def render(self, flange_xyz=None, flange_quat=None) -> np.ndarray:
        """Render the live scene from the camera pose -> (h, w, 3) BGR uint8."""
        scene = self._build_scene()
        # OpenCV optical pose -> OpenGL camera node pose.
        cam_pose = self.camera_pose(flange_xyz, flange_quat) @ _CV_TO_GL
        scene.add(self._camera, pose=cam_pose)
        # Lit render (NOT flat): the directional sun added in _build_scene gives
        # textureless meshes visible shape, while full ambient preserves the
        # checkerboard's crisp black/white for corner detection. Serialized on
        # the GL lock — the OSMesa context is single-threaded (see __init__).
        with self._gl_lock:
            color, _depth = self._offscreen.render(scene)
        # pyrender returns RGB uint8; the contract downstream is BGR.
        return np.ascontiguousarray(color[..., ::-1])
