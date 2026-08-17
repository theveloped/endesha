"""Static frame tree v0 (design §4.4/§4.5; roadmap week-6 milestone).

The full time-aware frame resolver is a later roadmap phase; this module
resolves a STATIC tree of named frames (``config/frames/*``) rooted at
``world``. TCP offsets are NOT tree nodes — a TCP definition's xyz/quat is
the one-hop ``T_flange<-tcp`` transform, composed separately by the caller.

Error taxonomy per design §4.5: :class:`FrameStale` and
:class:`FrameLowConfidence` are stubs, unused until dynamic frames arrive.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .frames import invert_transform, make_transform, quaternion_to_rotation_matrix

ROOT = "world"


class FrameError(Exception):
    """Base frame-resolution error; carries the offending frame name."""

    def __init__(self, frame: str, message: str):
        super().__init__(message)
        self.frame = frame


class FrameUnknown(FrameError):
    pass


class FrameCycle(FrameError):
    pass


class NoPathToRoot(FrameError):
    pass


class FrameStale(FrameError):
    """Stub per design §4.5 — unused until dynamic frames."""


class FrameLowConfidence(FrameError):
    """Stub per design §4.5 — unused until dynamic frames."""


SOURCE_MANUAL = "manual"
SOURCE_CALIBRATION = "calibration"


@dataclass
class FrameDef:
    """One static frame: pose of this frame in its parent.

    ``xyz``/``quat`` are the EFFECTIVE pose (what the tree resolves — backwards
    compatible everywhere). ``nominal`` (``{xyz, quat}``) is the design value:
    a manual write sets both; a calibration write updates the effective pose,
    keeps ``nominal`` and records ``calibration`` (``{t, method, residual,
    by}``), so drift stays visible and "reset to nominal" is possible
    (RFC §4). The config store enforces that rule for every writer.
    """

    parent: str
    xyz: list[float]
    quat: list[float]  # [qx, qy, qz, qw]
    source: str = SOURCE_MANUAL
    meta: dict = field(default_factory=dict)
    revision: int = 0
    t: int = 0
    nominal: dict | None = None
    calibration: dict | None = None

    @property
    def is_calibrated(self) -> bool:
        return self.calibration is not None

    def nominal_pose(self) -> tuple[list[float], list[float]]:
        """``(xyz, quat)`` of the design value; the effective pose when no
        nominal was ever recorded."""
        if self.nominal is None:
            return list(self.xyz), list(self.quat)
        return list(self.nominal["xyz"]), list(self.nominal["quat"])

    def drift(self) -> tuple[float, float]:
        """``(translation_m, angle_rad)`` between nominal and effective pose."""
        nx, nq = self.nominal_pose()
        dx = float(np.linalg.norm(np.asarray(self.xyz) - np.asarray(nx)))
        a = np.asarray(nq, dtype=np.float64)
        b = np.asarray(self.quat, dtype=np.float64)
        a /= np.linalg.norm(a)
        b /= np.linalg.norm(b)
        dot = min(1.0, abs(float(np.dot(a, b))))
        return dx, 2.0 * float(np.arccos(dot))

    def to_wire(self) -> dict:
        d = {
            "parent": self.parent,
            "xyz": [float(v) for v in self.xyz],
            "quat": [float(v) for v in self.quat],
            "source": self.source,
            "meta": dict(self.meta),
            "revision": int(self.revision),
            "t": int(self.t),
        }
        if self.nominal is not None:
            d["nominal"] = {
                "xyz": [float(v) for v in self.nominal["xyz"]],
                "quat": [float(v) for v in self.nominal["quat"]],
            }
        if self.calibration is not None:
            d["calibration"] = dict(self.calibration)
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "FrameDef":
        nominal = d.get("nominal")
        return cls(
            parent=d["parent"],
            xyz=list(d["xyz"]),
            quat=list(d["quat"]),
            source=d.get("source", SOURCE_MANUAL),
            meta=dict(d.get("meta") or {}),
            revision=int(d.get("revision", 0)),
            t=int(d.get("t", 0)),
            nominal=None if nominal is None else {"xyz": list(nominal["xyz"]), "quat": list(nominal["quat"])},
            calibration=None if d.get("calibration") is None else dict(d["calibration"]),
        )


@dataclass
class DynamicFrameSample:
    """One latest-wins dynamic-frame sample (design §4.5).

    Published to ``{realm}/frames/{name}`` by a producer (vision pipeline);
    bridged into a :class:`FrameDef` via :meth:`as_frame_def` so it drops
    straight into the ``dict[str, FrameDef]`` a :class:`FrameTree` consumes —
    no new resolver math.
    """

    t: int  # ns; capture-or-publish time (wf.core.time.now_ns)
    parent: str
    xyz: list[float]
    quat: list[float]  # [qx, qy, qz, qw], scalar-last
    source: str = "vision"
    confidence: float = 1.0

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "parent": self.parent,
            "xyz": [float(v) for v in self.xyz],
            "quat": [float(v) for v in self.quat],
            "source": self.source,
            "confidence": float(self.confidence),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "DynamicFrameSample":
        return cls(
            t=int(d.get("t", 0)),
            parent=d["parent"],
            xyz=list(d["xyz"]),
            quat=list(d["quat"]),
            source=d.get("source", "vision"),
            confidence=float(d.get("confidence", 1.0)),
        )

    def as_frame_def(self) -> "FrameDef":
        """Bridge to a :class:`FrameDef` for merging into a :class:`FrameTree`."""
        return FrameDef(
            parent=self.parent,
            xyz=self.xyz,
            quat=self.quat,
            source=self.source,
            meta={"confidence": self.confidence, "dynamic": True},
            revision=0,
            t=self.t,
        )


class FrameTree:
    """Static frame tree rooted at :data:`ROOT`.

    Validates at construction: every parent chain terminates at ``world``
    within ``len(frames)`` hops.
    """

    def __init__(self, frames: dict[str, FrameDef]):
        self._frames = dict(frames)
        # DFS with tri-state marks: validates unknown parents and cycles.
        done: set[str] = set()
        for start in self._frames:
            if start in done:
                continue
            in_progress: set[str] = set()
            chain: list[str] = []
            name = start
            while name != ROOT:
                if name in done:
                    break
                if name in in_progress:
                    raise FrameCycle(name, f"frame cycle through {name!r}")
                node = self._frames.get(name)
                if node is None:
                    raise FrameUnknown(name, f"unknown parent frame {name!r}")
                in_progress.add(name)
                chain.append(name)
                name = node.parent
            done.update(chain)

    @classmethod
    def from_wire(cls, d: dict[str, dict]) -> "FrameTree":
        return cls({name: FrameDef.from_wire(v) for name, v in d.items()})

    def names(self) -> list[str]:
        return list(self._frames)

    def chain(self, name: str) -> dict[str, FrameDef]:
        """The defs on ``name``'s parent chain to root (``name`` included).

        ``ROOT`` -> {}. Unknown -> :class:`FrameUnknown`.
        """
        out: dict[str, FrameDef] = {}
        while name != ROOT:
            node = self._frames.get(name)
            if node is None:
                raise FrameUnknown(name, f"unknown frame {name!r}")
            out[name] = node
            name = node.parent
        return out

    def transform_to_root(self, name: str) -> np.ndarray:
        """``T_world<-name`` (4x4). ``ROOT`` -> identity."""
        if name == ROOT:
            return np.eye(4, dtype=np.float64)
        node = self._frames.get(name)
        if node is None:
            raise FrameUnknown(name, f"unknown frame {name!r}")
        T_parent = self.transform_to_root(node.parent)
        return T_parent @ make_transform(
            quaternion_to_rotation_matrix(node.quat), node.xyz
        )

    def resolve(self, target: str, source: str) -> np.ndarray:
        """``T_source<-target`` (4x4).

        ``target == source`` -> identity WITHOUT any lookup, so
        base-frame-referenced waypoints work with an empty tree (no config
        service running). The target frame is looked up first so an unknown
        user-supplied frame is reported before the source frame.
        """
        if target == source:
            return np.eye(4, dtype=np.float64)
        T_target = self.transform_to_root(target)
        return invert_transform(self.transform_to_root(source)) @ T_target
