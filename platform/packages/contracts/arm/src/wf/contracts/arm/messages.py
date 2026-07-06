"""Hand-written `arm` contract wire messages (no codegen in phase 1).

Wire field names in ``to_wire``/``from_wire`` are normative. Conventions:
positions in meters, angles in radians, quaternions ``[qx, qy, qz, qw]``
(unit, Hamilton, scalar last), timestamps int nanoseconds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from wf.core.time import CLOCK_HOST

DO_BANKS = ("standard", "tool")

# Loose-goal DOF taxonomy: roll/pitch/yaw are rotations about the x/y/z axis;
# x/y/z are translations along that axis. The int is the axis index (0=x…).
ROTATION_DOF = {"roll": 0, "pitch": 1, "yaw": 2}
TRANSLATION_DOF = {"x": 0, "y": 1, "z": 2}
FREEDOM_FRAMES = ("reference", "tool")
DEFAULT_ROT_STEP = math.radians(5.0)  # rad — sweep resolution for a free rotation


@dataclass
class Pose:
    """Pose payload ``{frame, xyz, quat}``."""

    frame: str
    xyz: list[float]
    quat: list[float]

    def __post_init__(self):
        if len(self.xyz) != 3:
            raise ValueError(f"xyz must have 3 elements, got {len(self.xyz)}")
        if len(self.quat) != 4:
            raise ValueError(f"quat must have 4 elements, got {len(self.quat)}")

    def to_wire(self) -> dict:
        return {
            "frame": self.frame,
            "xyz": [float(v) for v in self.xyz],
            "quat": [float(v) for v in self.quat],
        }

    @classmethod
    def from_wire(cls, d: dict) -> "Pose":
        return cls(frame=d["frame"], xyz=list(d["xyz"]), quat=list(d["quat"]))


@dataclass
class Freedom:
    """One free / ranged goal DOF sampled by the loose-goal solver.

    Sits beside ``pose`` in a waypoint ``target`` (``target: {pose, free}``).
    ``dof`` is one of ``x``/``y``/``z`` (translation along that axis, metres) or
    ``roll``/``pitch``/``yaw`` (rotation about that axis, radians). ``frame``
    selects the axis convention: ``"reference"`` (the pose's own reference
    frame, default) or ``"tool"`` (the TCP-local axes).

    ``[min, max]`` bounds the sweep (``step`` resolution). A rotation may omit
    the bounds for a full ``[-pi, pi)`` sweep and defaults ``step`` to 5 deg; a
    translation MUST give both bounds and a ``step`` (a fully free translation
    is not a valid goal). Bounds/step are normalised to concrete numbers in
    ``__post_init__`` so downstream consumers always see filled values.
    """

    dof: str
    frame: str = "reference"
    min: float | None = None
    max: float | None = None
    step: float | None = None

    def __post_init__(self):
        if self.dof not in ROTATION_DOF and self.dof not in TRANSLATION_DOF:
            raise ValueError(
                f"dof must be one of {sorted(ROTATION_DOF) + sorted(TRANSLATION_DOF)}, "
                f"got {self.dof!r}"
            )
        if self.frame not in FREEDOM_FRAMES:
            raise ValueError(
                f"frame must be one of {FREEDOM_FRAMES}, got {self.frame!r}"
            )
        if self.is_rotation:
            if self.min is None and self.max is None:
                self.min, self.max = -math.pi, math.pi
            elif self.min is None or self.max is None:
                raise ValueError("rotation free dof needs both min and max, or neither")
            if self.step is None:
                self.step = DEFAULT_ROT_STEP
        else:
            if self.min is None or self.max is None:
                raise ValueError("translation free dof requires both min and max")
            if self.step is None:
                raise ValueError("translation free dof requires an explicit step")
        self.min = float(self.min)
        self.max = float(self.max)
        self.step = float(self.step)
        if self.min >= self.max:
            raise ValueError(f"min ({self.min}) must be < max ({self.max})")
        if self.step <= 0:
            raise ValueError(f"step must be > 0, got {self.step}")

    @property
    def is_rotation(self) -> bool:
        return self.dof in ROTATION_DOF

    @property
    def axis(self) -> int:
        """Axis index 0=x/1=y/2=z the DOF acts on."""
        return (ROTATION_DOF if self.is_rotation else TRANSLATION_DOF)[self.dof]

    def to_wire(self) -> dict:
        return {
            "dof": self.dof,
            "frame": self.frame,
            "min": float(self.min),
            "max": float(self.max),
            "step": float(self.step),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "Freedom":
        return cls(
            dof=d["dof"],
            frame=d.get("frame", "reference"),
            min=d.get("min"),
            max=d.get("max"),
            step=d.get("step"),
        )


@dataclass
class JointState:
    """Joint state sample.

    ``tau`` carries the controller's ``R1_actual_current`` (motor current as a
    torque proxy — no real torque field is exposed by RTDE).
    """

    t: int
    q: list[float]
    qd: list[float]
    tau: list[float]
    clock_domain: str = CLOCK_HOST

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "q": [float(v) for v in self.q],
            "qd": [float(v) for v in self.qd],
            "tau": [float(v) for v in self.tau],
            "clock_domain": self.clock_domain,
        }

    @classmethod
    def from_wire(cls, d: dict) -> "JointState":
        return cls(
            t=d["t"],
            q=list(d["q"]),
            qd=list(d["qd"]),
            tau=list(d["tau"]),
            clock_domain=d.get("clock_domain", CLOCK_HOST),
        )


@dataclass
class FlangeState:
    """Flange pose; ``pose.frame`` is ``arm/{rid}/base``."""

    t: int
    pose: Pose

    def to_wire(self) -> dict:
        return {"t": int(self.t), "pose": self.pose.to_wire()}

    @classmethod
    def from_wire(cls, d: dict) -> "FlangeState":
        return cls(t=d["t"], pose=Pose.from_wire(d["pose"]))


@dataclass
class TcpState:
    t: int
    tcp_name: str
    pose: Pose

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "tcp_name": self.tcp_name,
            "pose": self.pose.to_wire(),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "TcpState":
        return cls(t=d["t"], tcp_name=d["tcp_name"], pose=Pose.from_wire(d["pose"]))


@dataclass
class IoState:
    """IO snapshot (the dio-shaped slice of the arm contract).

    ``di``/``do_`` are bit-packed with LSB = pin 0. Python attribute ``do_``
    maps to wire key ``"do"`` (python keyword). Standard bank only in
    phase 1 — the tool bank joins with the dio work.
    """

    t: int
    di: int
    do_: int
    ai: list[float]
    ao: list[float]

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "di": int(self.di),
            "do": int(self.do_),
            "ai": [float(v) for v in self.ai],
            "ao": [float(v) for v in self.ao],
        }

    @classmethod
    def from_wire(cls, d: dict) -> "IoState":
        return cls(
            t=d["t"], di=d["di"], do_=d["do"], ai=list(d["ai"]), ao=list(d["ao"])
        )


@dataclass
class ArmStatus:
    """Arm status keepalive (~1 Hz).

    ``state_rate_hz`` is the measured joints publish rate (design §5.1).
    """

    t: int
    mode: str
    servo_on: bool
    estop: bool
    protective_stop: bool
    speed_scale: float
    active_tcp: str
    error: str | None
    state_rate_hz: float

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "mode": self.mode,
            "servo_on": bool(self.servo_on),
            "estop": bool(self.estop),
            "protective_stop": bool(self.protective_stop),
            "speed_scale": float(self.speed_scale),
            "active_tcp": self.active_tcp,
            "error": self.error,
            "state_rate_hz": float(self.state_rate_hz),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ArmStatus":
        return cls(
            t=d["t"],
            mode=d["mode"],
            servo_on=d["servo_on"],
            estop=d["estop"],
            protective_stop=d["protective_stop"],
            speed_scale=d["speed_scale"],
            active_tcp=d["active_tcp"],
            error=d.get("error"),
            state_rate_hz=d["state_rate_hz"],
        )


@dataclass
class SetDo:
    """``cmd/set_do`` request. ``bank`` is "standard" or "tool"."""

    bank: str
    pin: int
    value: bool

    def __post_init__(self):
        if self.bank not in DO_BANKS:
            raise ValueError(f"bank must be one of {DO_BANKS}, got {self.bank!r}")

    def to_wire(self) -> dict:
        return {"bank": self.bank, "pin": int(self.pin), "value": bool(self.value)}

    @classmethod
    def from_wire(cls, d: dict) -> "SetDo":
        return cls(bank=d["bank"], pin=d["pin"], value=d["value"])


@dataclass
class Ack:
    """Reply payload for cmd queryables."""

    ok: bool
    error: str | None = None

    def to_wire(self) -> dict:
        return {"ok": bool(self.ok), "error": self.error}

    @classmethod
    def from_wire(cls, d: dict) -> "Ack":
        return cls(ok=d["ok"], error=d.get("error"))


@dataclass
class Waypoint:
    """A waypoint of an ``execute_path`` goal.

    ``target`` carries exactly one of two forms:

    - ``{"q": [6 floats]}`` — joint-space target (any waypoint type).
    - ``{"pose": {frame, xyz, quat}}`` — frame-referenced Cartesian target
      for the ACTIVE TCP; allowed on ``type: "movej"`` only (IK + joint
      interpolation). Resolved against the static frame tree at goal
      acceptance: the driver injects the solved ``q`` into the target and
      records the resolution in the execution snapshot.

    A pose target on the LAST waypoint of a ``movej`` may additionally carry a
    ``free`` block (see :class:`Freedom`): ``{"pose": ..., "free": {...}}``.
    One goal DOF is then left free / ranged and the driver samples it,
    prunes by IK + collision, and executes the fastest collision-free option
    rather than a single pinned pose.

    ``speed``/``accel`` are accepted and recorded but unused — per-waypoint
    profiles arrive with movel.
    """

    type: str
    target: dict
    speed: float | None = None
    accel: float | None = None
    blend_radius: float = 0.0

    def to_wire(self) -> dict:
        return {
            "type": self.type,
            "target": self.target,
            "speed": None if self.speed is None else float(self.speed),
            "accel": None if self.accel is None else float(self.accel),
            "blend_radius": float(self.blend_radius),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "Waypoint":
        return cls(
            type=d["type"],
            target=dict(d["target"]),
            speed=d.get("speed"),
            accel=d.get("accel"),
            blend_radius=d.get("blend_radius", 0.0),
        )


@dataclass
class JogCommand:
    """``cmd/jog`` hold-to-jog sample.

    ``frame`` is a reference-frame NAME — reserved ``"base"``/``"tool"`` or
    any config-frame name (ignored for joint mode). ``velocity`` is len 6:
    joint -> rad/s per joint; cartesian -> ``[vx, vy, vz, wx, wy, wz]``
    (m/s, rad/s) expressed in ``frame``'s axes. ``t`` is the client
    ``now_ns`` (diagnostics only).
    """

    client_id: str
    mode: str
    frame: str
    velocity: list[float]
    t: int

    def __post_init__(self):
        if self.mode not in ("joint", "cartesian"):
            raise ValueError(f"mode must be 'joint' or 'cartesian', got {self.mode!r}")
        if not isinstance(self.frame, str) or not self.frame:
            raise ValueError("frame must be a non-empty str")
        if len(self.velocity) != 6:
            raise ValueError(f"velocity must have 6 elements, got {len(self.velocity)}")

    def to_wire(self) -> dict:
        return {
            "client_id": self.client_id,
            "mode": self.mode,
            "frame": self.frame,
            "velocity": [float(v) for v in self.velocity],
            "t": int(self.t),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "JogCommand":
        return cls(
            client_id=d["client_id"],
            mode=d["mode"],
            frame=d["frame"],
            velocity=list(d["velocity"]),
            t=d["t"],
        )


@dataclass
class ControlOwner:
    """Current holder of the control lease (timestamps int ns)."""

    client_id: str
    user: str
    granted_at: int
    expires_at: int

    def to_wire(self) -> dict:
        return {
            "client_id": self.client_id,
            "user": self.user,
            "granted_at": int(self.granted_at),
            "expires_at": int(self.expires_at),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ControlOwner":
        return cls(
            client_id=d["client_id"],
            user=d["user"],
            granted_at=d["granted_at"],
            expires_at=d["expires_at"],
        )


@dataclass
class AcquireControl:
    """``cmd/acquire_control`` request."""

    client_id: str
    user: str

    def to_wire(self) -> dict:
        return {"client_id": self.client_id, "user": self.user}

    @classmethod
    def from_wire(cls, d: dict) -> "AcquireControl":
        return cls(client_id=d["client_id"], user=d["user"])


@dataclass
class ControlAck:
    """Reply payload for the lease queryables."""

    ok: bool
    owner: ControlOwner | None = None
    error: str | None = None

    def to_wire(self) -> dict:
        return {
            "ok": bool(self.ok),
            "owner": None if self.owner is None else self.owner.to_wire(),
            "error": self.error,
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ControlAck":
        owner = d.get("owner")
        return cls(
            ok=d["ok"],
            owner=None if owner is None else ControlOwner.from_wire(owner),
            error=d.get("error"),
        )


@dataclass
class ControlOwnerState:
    """Payload of ``state/control_owner`` (latest-wins)."""

    t: int
    owner: ControlOwner | None = None

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "owner": None if self.owner is None else self.owner.to_wire(),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ControlOwnerState":
        owner = d.get("owner")
        return cls(
            t=d["t"], owner=None if owner is None else ControlOwner.from_wire(owner)
        )


@dataclass
class ExecutePathGoal:
    """``execute_path`` action goal.

    Feedback ``data``: ``{"current_wp": int}``. Result ``data``: ``{}`` on
    success. ``client_id`` (additive) names the lease holder authorizing the
    motion; the driver rejects ``execute_path`` without a valid lease.
    """

    waypoints: list[Waypoint] = field(default_factory=list)
    client_id: str | None = None

    def to_wire(self) -> dict:
        return {
            "waypoints": [wp.to_wire() for wp in self.waypoints],
            "client_id": self.client_id,
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ExecutePathGoal":
        return cls(
            waypoints=[Waypoint.from_wire(w) for w in d["waypoints"]],
            client_id=d.get("client_id"),
        )
