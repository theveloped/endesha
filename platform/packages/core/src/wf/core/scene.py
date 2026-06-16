"""Scene objects: named geometry attached to a frame (design §4.4/§4.5/§5.10).

A scene object is the ``{frame, pose, geometry}`` of the design's
``config/scene/{name}`` namespace: a primitive (box/cylinder/sphere) or a
shared mesh, posed relative to a named frame in the static frame tree. The
``world_model`` collision preflight (§5.10) resolves these into obstacle
geometry; ``mesh.uri`` is the seam to the single shared glTF/GLB asset.

Pure data, no zenoh — mirrors :class:`wf.core.frametree.FrameDef`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_GEOMETRY_TYPES = ("box", "cylinder", "sphere", "mesh")


def _is_numbers(v, n: int) -> bool:
    return (
        isinstance(v, (list, tuple))
        and len(v) == n
        and all(isinstance(x, (int, float)) for x in v)
    )


def _validate_geometry(geom: dict) -> None:
    """Raise ValueError on a malformed ``geometry`` block."""
    if not isinstance(geom, dict):
        raise ValueError("bad_geometry:geometry must be a dict")
    gtype = geom.get("type")
    if gtype not in _GEOMETRY_TYPES:
        raise ValueError(
            f"bad_geometry:type must be one of {_GEOMETRY_TYPES}"
        )
    if gtype == "box":
        if not _is_numbers(geom.get("size"), 3):
            raise ValueError("bad_geometry:box size must be 3 floats")
    elif gtype == "cylinder":
        if not isinstance(geom.get("radius"), (int, float)):
            raise ValueError("bad_geometry:cylinder radius must be a float")
        if not isinstance(geom.get("length"), (int, float)):
            raise ValueError("bad_geometry:cylinder length must be a float")
    elif gtype == "sphere":
        if not isinstance(geom.get("radius"), (int, float)):
            raise ValueError("bad_geometry:sphere radius must be a float")
    elif gtype == "mesh":
        if not isinstance(geom.get("uri"), str) or not geom.get("uri"):
            raise ValueError("bad_geometry:mesh uri must be a non-empty string")


@dataclass
class SceneObject:
    """One scene object: geometry posed in a named frame.

    ``pose`` is ``{xyz:[3], quat:[qx,qy,qz,qw]}`` of the geometry origin in
    ``frame``. ``geometry`` is a validated primitive/mesh block.
    """

    frame: str
    xyz: list[float]
    quat: list[float]  # [qx, qy, qz, qw]
    geometry: dict
    meta: dict = field(default_factory=dict)
    revision: int = 0
    t: int = 0

    def to_wire(self) -> dict:
        return {
            "frame": self.frame,
            "pose": {
                "xyz": [float(v) for v in self.xyz],
                "quat": [float(v) for v in self.quat],
            },
            "geometry": dict(self.geometry),
            "meta": dict(self.meta),
            "revision": int(self.revision),
            "t": int(self.t),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "SceneObject":
        pose = d.get("pose") or {}
        geometry = d.get("geometry")
        _validate_geometry(geometry)
        return cls(
            frame=d["frame"],
            xyz=list(pose["xyz"]),
            quat=list(pose["quat"]),
            geometry=dict(geometry),
            meta=dict(d.get("meta") or {}),
            revision=int(d.get("revision", 0)),
            t=int(d.get("t", 0)),
        )
