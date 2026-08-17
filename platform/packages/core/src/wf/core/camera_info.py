"""Camera intrinsics in the ROS ``sensor_msgs/CameraInfo`` layout (RFC §5).

Wire (``config/intrinsics/{cid}``)::

    width: 1280
    height: 800
    distortion_model: plumb_bob            # or rational_polynomial
    D: [k1, k2, p1, p2, k3]                # [] -> ideal pinhole
    K: [fx, 0, cx, 0, fy, cy, 0, 0, 1]     # row-major 3x3
    R: [1,0,0, 0,1,0, 0,0,1]               # optional, identity default
    P: [fx, 0, cx, 0, 0, fy, cy, 0, 0, 0, 1, 0]   # optional, derived from K

The legacy flat shape ``{fx, fy, cx, cy, w, h}`` is still *accepted* by
:meth:`CameraInfo.from_wire` (and normalized by the config store) so old
stores and callers keep working; new writers emit the CameraInfo layout so
OpenCV / ROS / calibration tooling can consume the store directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DISTORTION_MODELS = ("plumb_bob", "rational_polynomial", "equidistant")
_IDENTITY_R = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]


def _floats(values, n: int, label: str) -> list[float]:
    if not isinstance(values, (list, tuple)) or len(values) != n:
        raise ValueError(f"bad_intrinsics:{label} must have {n} numbers")
    out = []
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"bad_intrinsics:{label} must be numeric")
        out.append(float(v))
    return out


@dataclass
class CameraInfo:
    width: int
    height: int
    K: list[float]  # 3x3 row-major
    D: list[float] = field(default_factory=list)
    distortion_model: str = "plumb_bob"
    R: list[float] = field(default_factory=lambda: list(_IDENTITY_R))
    P: list[float] | None = None

    def __post_init__(self):
        if isinstance(self.width, bool) or not isinstance(self.width, int) or self.width <= 0:
            raise ValueError("bad_intrinsics:width must be a positive int")
        if isinstance(self.height, bool) or not isinstance(self.height, int) or self.height <= 0:
            raise ValueError("bad_intrinsics:height must be a positive int")
        self.K = _floats(self.K, 9, "K")
        if self.K[0] <= 0 or self.K[4] <= 0:
            raise ValueError("bad_intrinsics:fx/fy (K[0], K[4]) must be > 0")
        if self.distortion_model not in DISTORTION_MODELS:
            raise ValueError(f"bad_intrinsics:distortion_model must be one of {DISTORTION_MODELS}")
        if not isinstance(self.D, (list, tuple)):
            raise ValueError("bad_intrinsics:D must be a list")
        self.D = _floats(self.D, len(self.D), "D")
        self.R = _floats(self.R, 9, "R")
        if self.P is not None:
            self.P = _floats(self.P, 12, "P")

    # ── convenience (pinhole view) ───────────────────────────────────────

    @property
    def fx(self) -> float:
        return self.K[0]

    @property
    def fy(self) -> float:
        return self.K[4]

    @property
    def cx(self) -> float:
        return self.K[2]

    @property
    def cy(self) -> float:
        return self.K[5]

    @property
    def is_ideal(self) -> bool:
        return not any(self.D)

    def projection(self) -> list[float]:
        """``P`` when set, else derived from ``K`` (no rectification)."""
        if self.P is not None:
            return list(self.P)
        fx, cx, fy, cy = self.K[0], self.K[2], self.K[4], self.K[5]
        return [fx, 0.0, cx, 0.0, 0.0, fy, cy, 0.0, 0.0, 0.0, 1.0, 0.0]

    @classmethod
    def pinhole(cls, *, width: int, height: int, fx: float, fy: float,
                cx: float | None = None, cy: float | None = None) -> "CameraInfo":
        """An ideal pinhole; principal point defaults to the image centre."""
        cx = (width - 1) / 2 if cx is None else cx
        cy = (height - 1) / 2 if cy is None else cy
        return cls(width=int(width), height=int(height),
                   K=[float(fx), 0.0, float(cx), 0.0, float(fy), float(cy), 0.0, 0.0, 1.0])

    # ── wire ─────────────────────────────────────────────────────────────

    def to_wire(self) -> dict:
        d = {
            "width": int(self.width),
            "height": int(self.height),
            "distortion_model": self.distortion_model,
            "D": list(self.D),
            "K": list(self.K),
            "R": list(self.R),
        }
        if self.P is not None:
            d["P"] = list(self.P)
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "CameraInfo":
        if not isinstance(d, dict):
            raise ValueError("bad_intrinsics:must be a mapping")
        if "K" in d:
            return cls(
                width=d.get("width"),
                height=d.get("height"),
                K=d.get("K"),
                D=d.get("D") or [],
                distortion_model=d.get("distortion_model", "plumb_bob"),
                R=d.get("R") or list(_IDENTITY_R),
                P=d.get("P"),
            )
        # Legacy flat pinhole shape.
        try:
            fx, fy, cx, cy = (d[k] for k in ("fx", "fy", "cx", "cy"))
            w, h = d["w"], d["h"]
        except KeyError as exc:
            raise ValueError(f"bad_intrinsics:missing {exc.args[0]}") from None
        for k, v in (("fx", fx), ("fy", fy), ("cx", cx), ("cy", cy)):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise ValueError(f"bad_intrinsics:{k} must be a positive number")
        return cls(width=w, height=h,
                   K=[float(fx), 0.0, float(cx), 0.0, float(fy), float(cy), 0.0, 0.0, 1.0])

    @staticmethod
    def is_legacy(d: dict) -> bool:
        return isinstance(d, dict) and "K" not in d and "fx" in d
