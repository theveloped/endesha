"""Shared arm contract core (RFC step 4).

``ArmCore`` serves the entire ``arm`` contract for one logical device against a
pluggable :class:`~wf.hal.arm_core.backend.ArmBackend`. It owns the zenoh
endpoints (state publishers, cmd queryables, jog subscriber, execute_path
action), the control lease, the active-TCP cache, and the twin (URDF FK,
collision model, live frame tree + scene). The backend produces robot state and
executes motion; the core does everything else identically for sim and hardware.

Extracted verbatim (behaviour-preserving) from the former ``SimArmDriver`` /
``AuboDriver`` so the two drivers stop duplicating contract logic.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import numpy as np

from wf.contracts.arm import keys
from wf.contracts.arm.messages import (
    Ack,
    AcquireControl,
    ArmStatus,
    ControlAck,
    ControlOwner,
    ControlOwnerState,
    ExecutePathGoal,
    FlangeState,
    IoState,
    JogCommand,
    JointState,
    Pose,
    SetDo,
    TcpState,
)
from wf.core.action import ActionServer, GoalHandle
from wf.core.codec import decode, encode
from wf.core.frames import rotation_matrix_to_quaternion
from wf.core.frametree import FrameUnknown
from wf.core.lease import ControlLease
from wf.core.log import get_logger
from wf.core.time import now_ns
from wf.world_model.collision import CollisionModel
from wf.world_model.fk import UrdfFk
from wf.world_model.frames_live import build_live_tree
from wf.world_model.jog import jog_joint_velocity
from wf.world_model.preflight import preflight
from wf.world_model.scene_live import build_live_scene
from wf.world_model.trajectory import (
    TrajectoryError,
    generate_ruckig_trajectory,
    joints_close,
    validate_trajectory,
)
from wf.world_model.validate import (
    TCP_FLANGE,
    fetch_tcp,
    resolve_goal,
    tcp_transform,
)

from .backend import ArmBackend

_log = get_logger("wf.hal.arm_core")


def pose_from_transform(T: np.ndarray, frame: str) -> Pose:
    """Pose wire payload from a 4x4 transform expressed in ``frame``."""
    return Pose(
        frame=frame,
        xyz=[float(v) for v in T[:3, 3]],
        quat=rotation_matrix_to_quaternion(T[:3, :3]),
    )


def _owner_msg(owner_dict: dict | None) -> ControlOwner | None:
    return None if owner_dict is None else ControlOwner.from_wire(owner_dict)


class ArmCore:
    def __init__(
        self,
        session,
        realm: str,
        rid: str,
        params: dict,
        backend: ArmBackend,
        *,
        driver_version: str = "unknown",
    ):
        self.session = session
        self.realm = realm
        self.rid = rid
        self.params = params
        self.backend = backend
        self.driver_version = driver_version
        self.base_frame = keys.base_frame(rid)

        urdf_path = params["urdf"]  # resolved by the thin __main__ (default URDF)
        self.fk = UrdfFk(urdf_path)
        self.collision = CollisionModel(urdf_path, Path(urdf_path).parent.parent)
        # Static config frames/scene merged with subscribed dynamic layers.
        self._live_frames, self._frames_sub = build_live_tree(session, realm)
        self._live_scene, self._scene_sub = build_live_scene(session, realm)
        # Defaults from the URDF; a hardware backend may override in start().
        all_limits = self.fk.get_joint_limits()
        limits = [all_limits[name] for name in self.fk.JOINT_ORDER]
        self.jmin = [lo for lo, _hi in limits]
        self.jmax = [hi for _lo, hi in limits]
        self.servo_dt: float = params["servo_cycle_s"]

        self._stop_event = threading.Event()
        self._external_stop = threading.Event()  # cmd/stop -> abort
        self._stamp_lock = threading.Lock()
        self._last_t = 0  # strictly-increasing stamp guard

        # Active TCP: driver-local, reset to "flange" on restart (crash-only).
        self._tcp_lock = threading.Lock()
        self._active_tcp: tuple[str, np.ndarray] = (TCP_FLANGE, np.eye(4))

        # measured joints publish rate (state thread writes, status reads)
        self._rate_lock = threading.Lock()
        self._rate_count = 0
        self._rate_t0 = time.monotonic()
        self._rate_hz = 0.0

        self._pub_joints = session.declare_publisher(keys.state_joints(realm, rid))
        self._pub_flange = session.declare_publisher(keys.state_flange(realm, rid))
        self._pub_tcp = session.declare_publisher(keys.state_tcp(realm, rid))
        self._pub_io = session.declare_publisher(keys.state_io(realm, rid))
        self._pub_status = session.declare_publisher(keys.state_status(realm, rid))

        self.action_server = ActionServer(session, keys.action_prefix(realm, rid))
        self._queryables: list = []
        self._jog_sub = None

        # ── control lease ────────────────────────────────────────────────
        self._lease = ControlLease(params.get("lease_ttl_s", 30.0))
        self._pub_owner = session.declare_publisher(
            keys.state_control_owner(realm, rid)
        )

        # ── hold-to-jog (state guarded by _jog_lock) ─────────────────────
        self._jog_vmax = params.get("jog_vmax", 0.5)
        self._jog_watchdog_s = params.get("jog_watchdog_s", 0.25)
        self._jog_damping = params.get("jog_damping", 0.05)
        self._jog_lock = threading.Lock()
        self._jog_cmd: JogCommand | None = None
        self._jog_deadline = 0.0  # time.monotonic() deadline
        self._jog_tree = None  # FrameTree snapshot taken at jog start
        self._jog_active = False

    # ── lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> None:
        self._queryables = [
            self.session.declare_queryable(
                keys.cmd_set_do(self.realm, self.rid), self._on_set_do
            ),
            self.session.declare_queryable(
                keys.cmd_stop(self.realm, self.rid), self._on_stop
            ),
            self.session.declare_queryable(
                keys.cmd_clear_protective_stop(self.realm, self.rid),
                self._on_clear_protective_stop,
            ),
            self.session.declare_queryable(
                keys.cmd_set_tcp(self.realm, self.rid), self._on_set_tcp
            ),
            self.session.declare_queryable(
                keys.cmd_acquire_control(self.realm, self.rid),
                self._on_acquire_control,
            ),
            self.session.declare_queryable(
                keys.cmd_release_control(self.realm, self.rid),
                self._on_release_control,
            ),
        ]
        self._jog_sub = self.session.declare_subscriber(
            keys.cmd_jog(self.realm, self.rid), self._on_jog
        )
        self.action_server.register(
            "execute_path", self._accept_execute_path, self._execute_path
        )
        self.backend.start(self)
        _log.info("arm core up: realm=%s rid=%s", self.realm, self.rid)

    def run_forever(self) -> None:
        try:
            while not self._stop_event.wait(1.0):
                pass
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._stop_event.set()
        try:
            self.backend.shutdown()
        except Exception:
            _log.exception("backend shutdown failed")
        self.action_server.close()
        for sub in (*self._queryables, self._jog_sub, self._frames_sub, self._scene_sub):
            if sub is not None:
                try:
                    sub.undeclare()
                except Exception:
                    pass
        _log.info("arm core stopped")

    # ── stop flag (shared by cmd/stop and path execution) ─────────────────

    def stop_requested(self) -> bool:
        return self._external_stop.is_set()

    def clear_stop(self) -> None:
        self._external_stop.clear()

    # ── state publish helpers (called by the backend's state thread) ──────

    def publish_motion(
        self, q: list[float], qd: list[float], tau: list[float], t: int, clock_domain
    ) -> None:
        """Publish JointState + FlangeState + TcpState for one state sample and
        advance the publish-rate counter. Backend supplies the timestamp +
        clock domain; the core enforces a strictly-increasing stamp."""
        with self._stamp_lock:
            if t <= self._last_t:
                t = self._last_t + 1
            self._last_t = t

        T = self.fk.get_ee_transform(q)
        pose = pose_from_transform(T, self.base_frame)
        with self._tcp_lock:
            tcp_name, tcp_T = self._active_tcp
        tcp_pose = (
            pose
            if tcp_name == TCP_FLANGE
            else pose_from_transform(T @ tcp_T, self.base_frame)
        )

        self._pub_joints.put(
            encode(
                JointState(t=t, q=q, qd=qd, tau=tau, clock_domain=clock_domain).to_wire()
            )
        )
        self._pub_flange.put(encode(FlangeState(t=t, pose=pose).to_wire()))
        self._pub_tcp.put(
            encode(TcpState(t=t, tcp_name=tcp_name, pose=tcp_pose).to_wire())
        )

        with self._rate_lock:
            self._rate_count += 1
            elapsed = time.monotonic() - self._rate_t0
            if elapsed >= 1.0:
                self._rate_hz = self._rate_count / elapsed
                self._rate_count = 0
                self._rate_t0 = time.monotonic()

    def publish_io(self, di: int, do_: int, ai, ao, t: int | None = None) -> None:
        self._pub_io.put(
            encode(
                IoState(t=t or now_ns(), di=di, do_=do_, ai=ai, ao=ao).to_wire()
            )
        )

    def publish_status(
        self,
        *,
        mode: str,
        servo_on: bool,
        estop: bool,
        protective_stop: bool,
        speed_scale: float,
        error: str | None,
        t: int | None = None,
    ) -> None:
        self._pub_status.put(
            encode(
                ArmStatus(
                    t=t or now_ns(),
                    mode=mode,
                    servo_on=servo_on,
                    estop=estop,
                    protective_stop=protective_stop,
                    speed_scale=speed_scale,
                    active_tcp=self._active_tcp[0],
                    error=error,
                    state_rate_hz=self.state_rate_hz,
                ).to_wire()
            )
        )

    @property
    def state_rate_hz(self) -> float:
        with self._rate_lock:
            return self._rate_hz

    # ── cmd queryables ─────────────────────────────────────────────────────

    def _on_set_do(self, query) -> None:
        key = str(query.key_expr)
        try:
            req = SetDo.from_wire(decode(query.payload))
            self.backend.set_do(req.bank, req.pin, req.value)
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=str(exc)).to_wire()))

    def _on_stop(self, query) -> None:
        """Out-of-band stop: abort the active goal and clear an armed jog."""
        key = str(query.key_expr)
        self._external_stop.set()
        with self._jog_lock:
            self._jog_cmd = None  # disarm any active jog
        try:
            self.backend.stop()
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))
            return
        query.reply(key, encode(Ack(ok=True).to_wire()))

    def _on_clear_protective_stop(self, query) -> None:
        key = str(query.key_expr)
        try:
            self.backend.clear_protective_stop()
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    def _on_set_tcp(self, query) -> None:
        """Select the active TCP from the config store (cached at selection
        time — a later store edit does not retroactively change the offset)."""
        key = str(query.key_expr)
        try:
            name = decode(query.payload)["name"]
            try:
                tcp_def = fetch_tcp(self.session, self.rid, name)
            except Exception:
                query.reply(
                    key, encode(Ack(ok=False, error="config_unavailable").to_wire())
                )
                return
            if tcp_def is None:
                query.reply(
                    key, encode(Ack(ok=False, error=f"tcp_unknown:{name}").to_wire())
                )
                return
            if not tcp_def.get("selectable_as_tcp"):
                query.reply(
                    key,
                    encode(Ack(ok=False, error=f"tcp_not_selectable:{name}").to_wire()),
                )
                return
            with self._tcp_lock:
                self._active_tcp = (name, tcp_transform(tcp_def))
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    # ── control lease ──────────────────────────────────────────────────────

    def publish_owner(self) -> None:
        try:
            self._pub_owner.put(
                encode(
                    ControlOwnerState(
                        t=now_ns(), owner=_owner_msg(self._lease.owner())
                    ).to_wire()
                )
            )
        except Exception as exc:
            _log.warning("publish control_owner failed: %r", exc)

    def _on_acquire_control(self, query) -> None:
        key = str(query.key_expr)
        try:
            req = AcquireControl.from_wire(decode(query.payload))
            owner, err = self._lease.acquire(req.client_id, req.user)
            if err is None:
                self.publish_owner()
            owner_dict = owner if owner is not None else self._lease.owner()
            ack = ControlAck(ok=err is None, owner=_owner_msg(owner_dict), error=err)
            query.reply(key, encode(ack.to_wire()))
        except Exception as exc:
            query.reply(key, encode(ControlAck(ok=False, error=repr(exc)).to_wire()))

    def _on_release_control(self, query) -> None:
        key = str(query.key_expr)
        try:
            cid = decode(query.payload).get("client_id")
            self._lease.release(cid)
            self.publish_owner()
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    # ── hold-to-jog ──────────────────────────────────────────────────────

    def _on_jog(self, sample) -> None:
        """Zenoh-thread, fast: arm a jog command. Dropped unless the sender
        holds the lease, no goal is running, and the backend allows motion."""
        try:
            cmd = JogCommand.from_wire(decode(sample.payload))
        except Exception as exc:
            _log.warning("jog decode failed: %r", exc)
            return
        if self.backend.motion_block_reason(for_goal=False) is not None:
            return
        if not self._lease.holds(cmd.client_id):
            return
        if self.action_server.active_goal_id is not None:
            return
        with self._jog_lock:
            if not self._jog_active:
                self._jog_tree = self._live_frames.snapshot()
            self._jog_cmd = cmd
            self._jog_deadline = time.monotonic() + self._jog_watchdog_s

    def _jog_ref_R(self, cmd: JogCommand, q, tree) -> np.ndarray | None:
        """3x3 rotation of the reference frame's axes in the arm base, or None
        when the named frame is unknown."""
        if cmd.frame == "tool":
            with self._tcp_lock:
                tcp_R = self._active_tcp[1][:3, :3]
            R_flange = self.fk.get_ee_transform(q)[:3, :3]
            return R_flange @ tcp_R
        name = self.base_frame if cmd.frame == "base" else cmd.frame
        try:
            return tree.resolve(name, self.base_frame)[:3, :3]
        except FrameUnknown:
            return None

    def jog_step(self) -> list[float] | None:
        """Compute the jog action for one backend step.

        Returns the joint velocity to apply, ``[0.0]*6`` to halt/freeze (a jog
        just disarmed, or its frame is unknown), or ``None`` when there is
        nothing to do (idle). Encapsulates the lease/goal/watchdog/mirror gate
        and the reference-frame resolution; the backend applies the result at
        its own cadence."""
        with self._jog_lock:
            cmd = self._jog_cmd
            deadline = self._jog_deadline
            tree = self._jog_tree
            was_active = self._jog_active

        armed = (
            cmd is not None
            and self.backend.motion_block_reason(for_goal=False) is None
            and self.action_server.active_goal_id is None
            and time.monotonic() < deadline
            and self._lease.holds(cmd.client_id)
        )
        if not armed:
            if was_active:
                with self._jog_lock:
                    self._jog_active = False
                return [0.0] * 6  # freeze: arm holds its last pose
            return None

        q = self.backend.latest_q()
        if q is None:
            return None
        ref_R = self._jog_ref_R(cmd, q, tree)
        if ref_R is None:
            with self._jog_lock:
                self._jog_active = False
            return [0.0] * 6
        with self._tcp_lock:
            tcp_T = self._active_tcp[1]
        qd = jog_joint_velocity(
            self.fk,
            q,
            mode=cmd.mode,
            velocity=cmd.velocity,
            ref_R=ref_R,
            tcp_T=tcp_T,
            jog_vmax=self._jog_vmax,
            damping=self._jog_damping,
        )
        with self._jog_lock:
            self._jog_active = True
        return qd

    @property
    def jog_active(self) -> bool:
        with self._jog_lock:
            return self._jog_active

    # ── execute_path action ──────────────────────────────────────────────

    def _accept_execute_path(self, goal: dict) -> str | None:
        block = self.backend.motion_block_reason(for_goal=True)
        if block:
            return block
        if self.jog_active:
            return "jog_active"
        cid = goal.get("client_id") if isinstance(goal, dict) else None
        if not cid or not self._lease.holds(cid):
            return "no_control"
        q_start = self.backend.latest_q()
        if q_start is None:
            return "no_joint_state"
        # Pick up config frame/scene edits since startup so a UI-added frame or
        # scene change resolves without a driver restart; an empty fetch keeps
        # the last good layer.
        self._live_frames.refresh_static(self.session)
        self._live_scene.refresh_static(self.session)
        tree = self._live_frames.snapshot()
        with self._tcp_lock:
            tcp_name, tcp_T = self._active_tcp
        reason, resolution = resolve_goal(
            goal,
            fk=self.fk,
            rid=self.rid,
            q_start=list(q_start),
            jmin=self.jmin,
            jmax=self.jmax,
            margin=self.params["joint_limit_margin_rad"],
            tree=tree,
            tcp_name=tcp_name,
            tcp_T=tcp_T,
        )
        if reason:
            return reason
        return preflight(
            resolution,
            self._live_scene.snapshot(),
            model=self.collision,
            tree=tree,
            base_frame=self.base_frame,
        )

    def _execute_path(self, handle: GoalHandle) -> None:
        # Runs on the ActionServer worker thread; the server is serial and
        # enforces single-active-goal/busy for free.
        self.clear_stop()
        resolution = handle.goal.pop("_resolution", None) or {}
        snapshot = {
            "t": now_ns(),
            "goal_id": handle.goal_id,
            "rid": self.rid,
            "realm": self.realm,
            "speed_scale": 1.0,
            "versions": {"driver": self.driver_version},
            **resolution,
        }
        self.session.put(
            f"{keys.action_prefix(self.realm, self.rid)}/{handle.goal_id}/snapshot",
            encode(snapshot),
        )

        goal = ExecutePathGoal.from_wire(handle.goal)
        targets = [list(wp.target["q"]) for wp in goal.waypoints]
        start_q = self.backend.latest_q()

        # Zero-motion short-circuit: every target already at the current pose.
        if start_q is not None and all(joints_close(list(start_q), t) for t in targets):
            handle.feedback(1.0, current_wp=len(targets))
            handle.succeed(snapshot=snapshot)
            return

        ruckig = self.params["ruckig_defaults"]
        try:
            traj, wp_idx = generate_ruckig_trajectory(
                [list(start_q)] + targets,
                self.servo_dt,
                vmax=ruckig["vmax"],
                amax=ruckig["amax"],
                jmax=ruckig["jmax"],
            )
        except TrajectoryError as exc:
            handle.fail(error=str(exc))
            return
        violation = validate_trajectory(
            traj, self.jmin, self.jmax, margin=self.params["joint_limit_margin_rad"]
        )
        if violation:
            handle.fail(error=violation)
            return

        _log.info(
            "goal %s: %d samples, %.1fs, %d waypoint(s)",
            handle.goal_id,
            len(traj),
            len(traj) * self.servo_dt,
            len(targets),
        )
        self.backend.run_path(handle, traj, wp_idx, targets, snapshot)
