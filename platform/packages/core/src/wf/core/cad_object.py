"""Declarative object library: one reusable object type = render mesh +
simplified collision proxies + named child frames + fiducial markers.

An :class:`ObjectDef` is the *type* (authored once as a YAML manifest);
:func:`instantiate` expands it at a pose into the bus's frame/scene namespaces
— a root :class:`~wf.core.frametree.FrameDef`, one child frame per
:class:`ChildFrame`/:class:`Marker`, and one :class:`~wf.core.scene.SceneObject`
per :class:`CollisionPart`. The importer (``wf.tools.scene_import``) writes those
to the config store OR publishes them live; collision consumes them unchanged.

Pure data, no zenoh / yaml — mirrors :mod:`wf.core.scene` and
:mod:`wf.core.frametree`. The CLI does ``yaml.safe_load`` then
:meth:`ObjectDef.from_wire`.

Units are metres, asserted (``units: "m"``): a millimetre manifest fails with
``bad_units:`` rather than silently loading 1000x geometry, because
``coal.MeshLoader().load(uri)`` takes no scale arg.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .frametree import FrameDef
from .keys import key
from .scene import SceneObject, _validate_geometry


def _is_numbers(v, n: int) -> bool:
    return (
        isinstance(v, (list, tuple))
        and len(v) == n
        and all(isinstance(x, (int, float)) for x in v)
    )


def _check_name(name: str) -> str:
    """Validate a bare frame/scene name via :func:`wf.core.keys.key`."""
    try:
        key("x", name)
    except ValueError as exc:
        raise ValueError(f"bad_name:{name!r}: {exc}") from exc
    return name


@dataclass
class ChildFrame:
    """A named frame relative to the object root."""

    name: str
    xyz: list[float]
    quat: list[float]  # [qx, qy, qz, qw]
    meta: dict = field(default_factory=dict)

    def to_wire(self) -> dict:
        return {
            "name": self.name,
            "xyz": [float(v) for v in self.xyz],
            "quat": [float(v) for v in self.quat],
            "meta": dict(self.meta),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ChildFrame":
        _check_name(d["name"])
        if not _is_numbers(d.get("xyz"), 3):
            raise ValueError("bad_object:child frame xyz must be 3 numbers")
        if not _is_numbers(d.get("quat"), 4):
            raise ValueError("bad_object:child frame quat must be 4 numbers")
        return cls(
            name=d["name"],
            xyz=list(d["xyz"]),
            quat=list(d["quat"]),
            meta=dict(d.get("meta") or {}),
        )


@dataclass
class Marker:
    """A fiducial; becomes a child frame + meta on instantiate."""

    name: str
    family: str  # e.g. "aruco_4x4_50", "datamatrix"
    id: int
    size_m: float
    xyz: list[float]
    quat: list[float]

    def to_wire(self) -> dict:
        return {
            "name": self.name,
            "family": self.family,
            "id": int(self.id),
            "size_m": float(self.size_m),
            "xyz": [float(v) for v in self.xyz],
            "quat": [float(v) for v in self.quat],
        }

    @classmethod
    def from_wire(cls, d: dict) -> "Marker":
        _check_name(d["name"])
        if not d.get("family"):
            raise ValueError("bad_object:marker family must be non-empty")
        if not isinstance(d.get("id"), int) or isinstance(d.get("id"), bool):
            raise ValueError("bad_object:marker id must be an int")
        size = d.get("size_m")
        if not isinstance(size, (int, float)) or size <= 0:
            raise ValueError("bad_object:marker size_m must be > 0")
        if not _is_numbers(d.get("xyz"), 3):
            raise ValueError("bad_object:marker xyz must be 3 numbers")
        if not _is_numbers(d.get("quat"), 4):
            raise ValueError("bad_object:marker quat must be 4 numbers")
        return cls(
            name=d["name"],
            family=d["family"],
            id=int(d["id"]),
            size_m=float(size),
            xyz=list(d["xyz"]),
            quat=list(d["quat"]),
        )


@dataclass
class CollisionPart:
    """One simplified proxy, geometry posed on the object."""

    xyz: list[float]
    quat: list[float]  # [qx, qy, qz, qw]
    geometry: dict  # validated by wf.core.scene._validate_geometry

    def to_wire(self) -> dict:
        return {
            "xyz": [float(v) for v in self.xyz],
            "quat": [float(v) for v in self.quat],
            "geometry": dict(self.geometry),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "CollisionPart":
        if not _is_numbers(d.get("xyz"), 3):
            raise ValueError("bad_object:collision part xyz must be 3 numbers")
        if not _is_numbers(d.get("quat"), 4):
            raise ValueError("bad_object:collision part quat must be 4 numbers")
        try:
            _validate_geometry(d.get("geometry"))
        except ValueError as exc:
            raise ValueError(f"bad_object:{exc}") from exc
        return cls(
            xyz=list(d["xyz"]),
            quat=list(d["quat"]),
            geometry=dict(d["geometry"]),
        )


@dataclass
class ObjectDef:
    """A reusable object type: child frames, collision proxies, markers, render."""

    name: str
    units: str = "m"
    frames: list[ChildFrame] = field(default_factory=list)
    collision: list[CollisionPart] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)
    render: dict | None = None  # {"mesh_uri": str}; carried, not consumed here

    def to_wire(self) -> dict:
        d = {
            "name": self.name,
            "units": self.units,
            "frames": [f.to_wire() for f in self.frames],
            "collision": [c.to_wire() for c in self.collision],
            "markers": [m.to_wire() for m in self.markers],
        }
        if self.render is not None:
            d["render"] = dict(self.render)
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "ObjectDef":
        name = d.get("name")
        if not name or not isinstance(name, str):
            raise ValueError("bad_object:name must be a non-empty string")
        _check_name(name)
        units = d.get("units", "m")
        if units != "m":
            raise ValueError(f"bad_units:{units!r} (only metres supported)")
        render = d.get("render")
        if render is not None and not isinstance(render, dict):
            raise ValueError("bad_object:render must be a dict or null")
        return cls(
            name=name,
            units=units,
            frames=[ChildFrame.from_wire(f) for f in d.get("frames") or []],
            collision=[CollisionPart.from_wire(c) for c in d.get("collision") or []],
            markers=[Marker.from_wire(m) for m in d.get("markers") or []],
            render=dict(render) if isinstance(render, dict) else None,
        )


def instantiate(
    obj: ObjectDef,
    *,
    instance: str,
    parent_frame: str,
    xyz: list[float],
    quat: list[float],
) -> tuple[dict[str, FrameDef], dict[str, SceneObject]]:
    """Expand ``obj`` at a pose into frame + scene dicts keyed by bare name.

    No ``config/``/realm prefix — the sink adds those. Returns
    ``(frames, scene)``: a root frame ``{instance}``, child frames
    ``{instance}/{child}``, marker frames ``{instance}/marker/{name}``, and
    scene objects ``{instance}/{i}`` parented to ``{instance}``.
    """
    _check_name(instance)
    meta_obj = {"object": obj.name}
    frames: dict[str, FrameDef] = {
        instance: FrameDef(
            parent=parent_frame,
            xyz=list(xyz),
            quat=list(quat),
            source="cad",
            meta=dict(meta_obj),
        )
    }
    for c in obj.frames:
        name = key(instance, c.name)
        frames[name] = FrameDef(
            parent=instance,
            xyz=list(c.xyz),
            quat=list(c.quat),
            source="cad",
            meta=dict(c.meta),
        )
    for m in obj.markers:
        name = key(instance, "marker", m.name)
        frames[name] = FrameDef(
            parent=instance,
            xyz=list(m.xyz),
            quat=list(m.quat),
            source="cad",
            meta={"marker": {"family": m.family, "id": m.id, "size_m": m.size_m}},
        )
    scene: dict[str, SceneObject] = {}
    for i, p in enumerate(obj.collision):
        name = key(instance, str(i))
        scene[name] = SceneObject(
            frame=instance,
            xyz=list(p.xyz),
            quat=list(p.quat),
            geometry=dict(p.geometry),
            meta={"name": name, "object": obj.name},
        )
    return frames, scene
