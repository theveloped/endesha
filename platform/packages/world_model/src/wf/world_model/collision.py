"""Pinocchio + Coal collision engine for execute_path preflight (design §5.10).

One :class:`CollisionModel` is built per driver (URDF parse + mesh load is the
only expensive step) and answers three queries against a resolved trajectory:

- :meth:`CollisionModel.check_collision` — boolean "does this q collide?",
- :meth:`CollisionModel.min_distance` — closest separation + witness points,
- :meth:`CollisionModel.preflight` — dense check over a whole trajectory,
  returning the first violating ``(index, pair)`` for the ``collision:{a}|{b}``
  rejection reason.

The robot is the URDF's fixed-base 6-DoF chain (``model.nq == 6``, matching
:data:`UrdfFk.JOINT_ORDER`). Self-collision pairs are every link pair minus the
adjacent (consecutive :data:`UrdfFk.LINK_ORDER`) neighbours, which touch by
construction; the remaining set is collision-free across the arm's normal
envelope (verified at home/neutral). Scene obstacles from ``config/scene/**``
are inserted per query, posed through the static frame tree exactly as
``resolve_goal`` poses pose targets.
"""

from __future__ import annotations

import copy
from pathlib import Path

import coal
import numpy as np
import pinocchio as pin

from wf.core.assets import resolve_asset
from wf.core.frames import make_transform, quaternion_to_rotation_matrix
from wf.core.frametree import FrameTree, FrameUnknown
from wf.core.log import get_logger
from wf.core.scene import SceneObject

from .fk import UrdfFk

_log = get_logger("wf.world_model.collision")

# universe joint index (fixed base): scene placements are world (== base) poses.
_UNIVERSE_JOINT = 0

# A scene object posed in this frame is an end-of-arm tool rigidly mounted on
# the flange via a tool changer. It attaches to the flange JOINT (so Pinocchio
# FK moves it with the arm) instead of the universe, and is never paired against
# the flange link itself — a rigid mount is not a collision. Every other
# robot-link pair and every tool<->world-obstacle pair IS still checked.
_FLANGE_FRAME = "arm/r1/flange"
# The flange link (last in the kinematic chain) the tool mounts on.
_FLANGE_LINK = UrdfFk.LINK_ORDER[-1]


def _se3(T: np.ndarray) -> pin.SE3:
    """``pin.SE3`` from a 4x4 homogeneous matrix."""
    return pin.SE3(np.asarray(T, dtype=np.float64))


def _scene_geometry(obj: SceneObject) -> coal.CollisionGeometry | None:
    """A Coal collision geometry for a scene object, or ``None`` to skip it.

    Coal primitives take FULL extents (box sides, cylinder length). A ``mesh``
    whose ``uri`` cannot be loaded is skipped (never blocks acceptance on a bad
    asset), mirroring ``fetch_scene``'s skip-malformed policy.
    """
    geom = obj.geometry
    gtype = geom.get("type")
    if gtype == "box":
        sx, sy, sz = (float(v) for v in geom["size"])
        return coal.Box(sx, sy, sz)
    if gtype == "cylinder":
        return coal.Cylinder(float(geom["radius"]), float(geom["length"]))
    if gtype == "sphere":
        return coal.Sphere(float(geom["radius"]))
    if gtype == "mesh":
        uri = geom["uri"]
        try:
            return coal.MeshLoader().load(resolve_asset(uri))
        except Exception as exc:  # noqa: BLE001 — bad asset must not block accept
            _log.debug("scene mesh load failed; skipping uri=%s error=%r", uri, exc)
            return None
    return None


class CollisionModel:
    """Robot collision model with per-query scene insertion (design §5.10)."""

    def __init__(
        self,
        urdf_path: Path,
        package_dir: Path,
        *,
        margin: float = 0.0,
    ) -> None:
        urdf_path = Path(urdf_path)
        self.margin = float(margin)

        self._model = pin.buildModelFromUrdf(str(urdf_path))
        if self._model.nq != 6:
            raise ValueError(
                f"expected a 6-DoF arm (model.nq == 6), got nq={self._model.nq}"
            )
        self._geom = pin.buildGeomFromUrdf(
            self._model,
            str(urdf_path),
            pin.GeometryType.COLLISION,
            package_dirs=[str(package_dir)],
        )
        self._geom.addAllCollisionPairs()
        self._remove_adjacent_pairs()
        # geometry-object index -> robot link name (human-readable reason part)
        self._link_name = {
            i: self._link_for(i)
            for i in range(len(self._geom.geometryObjects))
        }
        self._robot_geom_ids = list(range(len(self._geom.geometryObjects)))
        self._data = self._model.createData()
        # Flange attach point for end-of-arm tools (scene objects in
        # _FLANGE_FRAME): the joint they parent to, the joint->link placement
        # their mount transform composes onto, and the flange link's own geom
        # (excluded from tool pairs — a rigidly mounted tool is not a collision).
        flange_frame = self._model.frames[self._model.getFrameId(_FLANGE_LINK)]
        self._flange_joint = flange_frame.parentJoint
        self._flange_placement = flange_frame.placement
        self._flange_geom_id = next(
            gid for gid in self._robot_geom_ids if self._link_name[gid] == _FLANGE_LINK
        )

    def _link_for(self, geom_id: int) -> str:
        """Robot link name owning geometry object ``geom_id``."""
        return self._model.frames[
            self._geom.geometryObjects[geom_id].parentFrame
        ].name

    def _remove_adjacent_pairs(self) -> None:
        """Drop pairs of consecutive :data:`UrdfFk.LINK_ORDER` links.

        Adjacent links are joined and touch by construction; only non-adjacent
        link contact is a real self-collision.
        """
        order = UrdfFk.LINK_ORDER
        adjacent = {
            frozenset((order[i], order[i + 1])) for i in range(len(order) - 1)
        }
        doomed = [
            pin.CollisionPair(cp.first, cp.second)
            for cp in self._geom.collisionPairs
            if frozenset((self._link_for(cp.first), self._link_for(cp.second)))
            in adjacent
        ]
        for cp in doomed:
            self._geom.removeCollisionPair(cp)

    def _name_of(self, geom_id: int, scene_names: dict[int, str]) -> str:
        """Reason-string body name for a geometry index."""
        if geom_id in scene_names:
            return scene_names[geom_id]
        return self._link_name[geom_id]

    def _build_scene(
        self,
        scene: list[SceneObject],
        tree: FrameTree,
        base_frame: str,
    ) -> tuple[pin.GeometryModel, dict[int, str]]:
        """A working geometry model = robot + posed scene obstacles.

        Returns the model (with scene<->robot pairs added) and a map of the
        inserted scene geometry indices to their reason names.
        """
        geom = copy.deepcopy(self._geom)
        scene_names: dict[int, str] = {}
        tool_ids: list[int] = []
        world_ids: list[int] = []
        for i, obj in enumerate(scene):
            if obj.meta.get("collision") is False:
                # Opt-out (e.g. the robot mount: coincides with base_link by
                # construction). Still rendered; just not a collision obstacle.
                continue
            collision_geom = _scene_geometry(obj)
            if collision_geom is None:
                continue
            name = obj.meta.get("name") or f"scene/{i}"
            mount = make_transform(quaternion_to_rotation_matrix(obj.quat), obj.xyz)
            if obj.frame == _FLANGE_FRAME:
                # End-of-arm tool: attach to the flange joint so FK moves it with
                # the arm. ``mount`` is the tool-changer transform flange<-tool,
                # composed onto the joint->flange placement.
                go = pin.GeometryObject(
                    name,
                    self._flange_joint,
                    self._flange_placement * _se3(mount),
                    collision_geom,
                )
                idx = geom.addGeometryObject(go)
                tool_ids.append(idx)
                scene_names[idx] = name
                continue
            try:
                T_frame = tree.resolve(obj.frame, base_frame)
            except FrameUnknown as exc:
                # A scene obstacle parented to a vanished dynamic frame must not
                # crash preflight; the obstacle is simply absent this tick.
                _log.debug("scene frame unresolved; skipping obstacle frame=%s error=%r", obj.frame, exc)
                continue
            go = pin.GeometryObject(
                name, _UNIVERSE_JOINT, _se3(T_frame @ mount), collision_geom
            )
            idx = geom.addGeometryObject(go)
            world_ids.append(idx)
            scene_names[idx] = name
        # World obstacles: checked against every robot link (today's behaviour).
        for wid in world_ids:
            for link_id in self._robot_geom_ids:
                geom.addCollisionPair(pin.CollisionPair(wid, link_id))
        # Flange tools: checked against every robot link EXCEPT the flange they
        # mount on (rigid attachment is never a real collision), and against
        # every world obstacle (the tool striking the cell IS a real collision).
        for tid in tool_ids:
            for link_id in self._robot_geom_ids:
                if link_id == self._flange_geom_id:
                    continue
                geom.addCollisionPair(pin.CollisionPair(tid, link_id))
            for wid in world_ids:
                geom.addCollisionPair(pin.CollisionPair(tid, wid))
        return geom, scene_names

    def check_collision(
        self,
        q: list[float],
        scene: list[SceneObject],
        tree: FrameTree,
        base_frame: str,
    ) -> dict:
        """``{"hit": bool, "pairs": [(a, b), ...]}`` for one config.

        ``pairs`` lists every colliding body-name pair (robot link names and
        ``scene/{name}`` obstacle names).
        """
        geom, scene_names = self._build_scene(scene, tree, base_frame)
        gd = geom.createData()
        q_arr = np.asarray(q, dtype=np.float64)
        hit = pin.computeCollisions(self._model, self._data, geom, gd, q_arr, False)
        pairs: list[tuple[str, str]] = []
        if hit:
            for k, cp in enumerate(geom.collisionPairs):
                if gd.collisionResults[k].isCollision():
                    pairs.append(
                        (
                            self._name_of(cp.first, scene_names),
                            self._name_of(cp.second, scene_names),
                        )
                    )
        return {"hit": bool(hit), "pairs": pairs}

    def min_distance(
        self,
        q: list[float],
        scene: list[SceneObject],
        tree: FrameTree,
        base_frame: str,
    ) -> dict:
        """``{"d": float, "witness": (p_a, p_b) | None, "pair": (a, b) | None}``.

        ``d`` is the signed minimum separation over all active pairs (negative
        on penetration); ``witness`` are the two closest points in the base
        frame; ``pair`` is the closest body-name pair.
        """
        geom, scene_names = self._build_scene(scene, tree, base_frame)
        gd = geom.createData()
        q_arr = np.asarray(q, dtype=np.float64)
        for req in gd.distanceRequests:
            req.enable_signed_distance = True
        closest = pin.computeDistances(self._model, self._data, geom, gd, q_arr)
        if closest < 0 or len(geom.collisionPairs) == 0:
            return {"d": float("inf"), "witness": None, "pair": None}
        res = gd.distanceResults[closest]
        cp = geom.collisionPairs[closest]
        return {
            "d": float(res.min_distance),
            "witness": (
                np.asarray(res.getNearestPoint1(), dtype=np.float64),
                np.asarray(res.getNearestPoint2(), dtype=np.float64),
            ),
            "pair": (
                self._name_of(cp.first, scene_names),
                self._name_of(cp.second, scene_names),
            ),
        }

    def preflight(
        self,
        trajectory: list[list[float]],
        scene: list[SceneObject],
        tree: FrameTree,
        base_frame: str,
    ) -> dict:
        """Dense collision check over a trajectory.

        ``{"ok": bool, "first_violation": {"index": i, "pair": (a, b)} | None}``.
        Stops at the first colliding waypoint. An empty scene with a
        self-collision-free path returns ``{"ok": True, ...}`` (today's accept
        behaviour); a path that drives the arm into itself returns the
        self-collision violation.
        """
        geom, scene_names = self._build_scene(scene, tree, base_frame)
        gd = geom.createData()
        for i, q in enumerate(trajectory):
            q_arr = np.asarray(q, dtype=np.float64)
            hit = pin.computeCollisions(
                self._model, self._data, geom, gd, q_arr, True
            )
            if hit:
                for k, cp in enumerate(geom.collisionPairs):
                    if gd.collisionResults[k].isCollision():
                        return {
                            "ok": False,
                            "first_violation": {
                                "index": i,
                                "pair": (
                                    self._name_of(cp.first, scene_names),
                                    self._name_of(cp.second, scene_names),
                                ),
                            },
                        }
        return {"ok": True, "first_violation": None}
