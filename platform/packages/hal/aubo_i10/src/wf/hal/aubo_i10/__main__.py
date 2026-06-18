"""The `aubo_driver` process (design §5.1).

Crash-only: no state to restore; on restart everything is re-declared
(liveliness re-asserts). The registry descriptor (`{realm}/registry/{rid}`)
is deliberately NOT published — it arrives with the supervisor work.

Two RPC connections are held (the SDK is not shared across concurrent
threads): `sdk_cmd` owned exclusively by the command worker, `sdk_state`
owned by the state-poller thread and the out-of-band `cmd/stop` path
(guarded by a lock).
"""

from __future__ import annotations

import argparse
import bisect
import concurrent.futures
import importlib.metadata
import math
import os
import queue
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
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import CLOCK_HOST, CLOCK_ROBOT, now_ns
from wf.world_model.fk import UrdfFk
from wf.world_model.trajectory import (
    generate_ruckig_trajectory,
    joints_close,
    validate_trajectory,
)
from wf.core.frametree import FrameUnknown
from wf.core.lease import ControlLease
from wf.world_model.collision import CollisionModel
from wf.world_model.preflight import preflight
from wf.world_model.jog import jog_joint_velocity
from wf.world_model.frames_live import build_live_tree
from wf.world_model.scene_live import build_live_scene
from wf.world_model.validate import (
    TCP_FLANGE,
    fetch_tcp,
    resolve_goal,
    tcp_transform,
)

from . import BUNDLED_URDF
from .config import load_resource
from .rtde import RtdeStream
from .sdk import AuboSession
from .timesync import RobotTimeSync

_log = get_logger("wf.hal.aubo_i10.driver")

_IO_POLL_HZ = 10.0
_STATUS_EVERY_N_TICKS = 10  # -> 1 Hz status at 10 Hz io polling
_CMD_REPLY_TIMEOUT_S = 2.0
_FEEDBACK_EVERY_N_TICKS = 4  # 50 ms ticks -> ~5 Hz feedback


def _driver_version() -> str:
    try:
        return importlib.metadata.version("wf-hal-aubo-i10")
    except Exception:
        return "unknown"


def _owner_msg(owner_dict: dict | None) -> ControlOwner | None:
    """ControlOwner message from a ControlLease owner dict (or None)."""
    return None if owner_dict is None else ControlOwner.from_wire(owner_dict)


class AuboDriver:
    def __init__(self, session, realm: str, rid: str, params: dict):
        self.session = session
        self.realm = realm
        self.rid = rid
        self.params = params
        self.base_frame = keys.base_frame(rid)

        urdf_path = params.get("urdf") or BUNDLED_URDF
        self.fk = UrdfFk(urdf_path)
        self.collision = CollisionModel(urdf_path, Path(urdf_path).parent.parent)
        # Static config frames merged with subscribed dynamic {realm}/frames/**.
        self._live_frames, self._frames_sub = build_live_tree(session, realm)
        # Static config scene merged with subscribed runtime {realm}/scene/**.
        self._live_scene, self._scene_sub = build_live_scene(session, realm)
        self.timesync = RobotTimeSync()

        self._stop_event = threading.Event()
        self._external_stop = threading.Event()
        self._state_lock = threading.Lock()  # guards sdk_state RPC calls
        self._latest_lock = threading.Lock()
        self._latest_q: list[float] | None = None
        self._latest_status: dict | None = None
        self._warned_host_clock = False
        self._last_t = 0  # strictly-increasing stamp guard (coarse host clock)

        # Active TCP: driver-local, reset to "flange" on restart (crash-only).
        self._tcp_lock = threading.Lock()
        self._active_tcp: tuple[str, np.ndarray] = (TCP_FLANGE, np.eye(4))

        # RTDE rate counter
        self._rate_lock = threading.Lock()
        self._rate_count = 0
        self._rate_t0 = time.monotonic()
        self._rate_hz = 0.0

        self._cmd_queue: queue.Queue = queue.Queue()

        self.sdk_cmd: AuboSession | None = None
        self.sdk_state: AuboSession | None = None
        self.rtde: RtdeStream | None = None
        self.jmin: list[float] = []
        self.jmax: list[float] = []
        self.servo_dt: float = params["servo_cycle_s"]

        self._pub_joints = session.declare_publisher(keys.state_joints(realm, rid))
        self._pub_flange = session.declare_publisher(keys.state_flange(realm, rid))
        self._pub_tcp = session.declare_publisher(keys.state_tcp(realm, rid))
        self._pub_io = session.declare_publisher(keys.state_io(realm, rid))
        self._pub_status = session.declare_publisher(keys.state_status(realm, rid))

        self.action_server = ActionServer(session, keys.action_prefix(realm, rid))

        # ── control lease + hold-to-jog ──────────────────────────────────
        self._lease = ControlLease(params.get("lease_ttl_s", 30.0))
        self._pub_owner = session.declare_publisher(
            keys.state_control_owner(realm, rid)
        )
        self._jog_vmax = params.get("jog_vmax", 0.5)
        self._jog_acc = params.get("jog_acc", 2.0)
        self._jog_watchdog_s = params.get("jog_watchdog_s", 0.25)
        self._jog_loop_hz = params.get("jog_loop_hz", 50)
        self._jog_damping = params.get("jog_damping", 0.05)
        self._jog_lock = threading.Lock()
        self._jog_cmd: JogCommand | None = None
        self._jog_deadline = 0.0  # time.monotonic() deadline
        self._jog_tree = None  # FrameTree snapshot taken at jog start
        self._jog_active = threading.Event()  # a jog is currently being applied
        self._jog_wake = threading.Event()  # wake the runner
        self._jog_stop = threading.Event()  # cmd/stop halts an active jog
        self._jog_sub = None

    # ── startup ──────────────────────────────────────────────────────────

    def start(self) -> None:
        ip = self.params["ip"]
        rpc_port = self.params["rpc_port"]
        login = self.params.get("login") or {}
        user = login.get("user", "aubo")
        password = str(login.get("pass", "123456"))

        self.sdk_cmd = AuboSession(ip, rpc_port, user, password).__enter__()
        self.sdk_state = AuboSession(ip, rpc_port, user, password).__enter__()

        self.jmin, self.jmax = self.sdk_cmd.joint_limits()
        self.servo_dt = self.sdk_cmd.servo_cycle(self.params["servo_cycle_s"])
        try:
            self.timesync.calibrate_robot(self.sdk_cmd.controller_time_ns())
        except Exception as exc:
            _log.warning("controller time calibration failed (%r); using host clock", exc)
        _log.info(
            "limits jmin=%s jmax=%s servo_dt=%.4f", self.jmin, self.jmax, self.servo_dt
        )

        self.rtde = RtdeStream(
            ip,
            port=self.params["rtde_port"],
            hz=200,
            user=user,
            password=password,
            on_sample=self._on_rtde_sample,
        )
        self.rtde.start()

        threading.Thread(
            target=self._state_poller, name="state-poller", daemon=True
        ).start()
        threading.Thread(
            target=self._command_worker, name="command-worker", daemon=True
        ).start()
        threading.Thread(
            target=self._jog_runner, name="jog-runner", daemon=True
        ).start()

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
        _log.info(
            "aubo_driver up: realm=%s rid=%s ip=%s", self.realm, self.rid, ip
        )

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
        self._jog_wake.set()  # release the jog runner from its wait
        if self.rtde is not None:
            self.rtde.stop()
        self.action_server.close()
        if self._jog_sub is not None:
            try:
                self._jog_sub.undeclare()
            except Exception:
                pass
        if self._frames_sub is not None:
            try:
                self._frames_sub.undeclare()
            except Exception:
                pass
        if self._scene_sub is not None:
            try:
                self._scene_sub.undeclare()
            except Exception:
                pass
        for sdk in (self.sdk_cmd, self.sdk_state):
            if sdk is not None:
                sdk.__exit__(None, None, None)
        _log.info("aubo_driver stopped")

    # ── RTDE thread (200 Hz) ─────────────────────────────────────────────

    def _on_rtde_sample(self, controller_ts_s, q, qd, current) -> None:
        if self.timesync.calibrated and math.isfinite(controller_ts_s):
            t = self.timesync.robot_time_ns(controller_ts_s)
            domain = CLOCK_ROBOT
        else:
            # Observed: this controller build streams `timestamp: null` over
            # RTDE -> NaN; stamp with the host clock instead.
            t = now_ns()
            domain = CLOCK_HOST
            if not self._warned_host_clock:
                self._warned_host_clock = True
                _log.warning(
                    "RTDE timestamp unusable (ts=%r); stamping with host clock",
                    controller_ts_s,
                )

        # Contract: t strictly increasing. The Windows wall clock is coarse
        # (~1-15 ms) and RTDE delivery is bursty, so nudge duplicates by 1 ns.
        if t <= self._last_t:
            t = self._last_t + 1
        self._last_t = t

        joints = JointState(t=t, q=q, qd=qd, tau=current, clock_domain=domain)
        self._pub_joints.put(encode(joints.to_wire()))

        T = self.fk.get_ee_transform(q)
        pose = Pose(
            frame=self.base_frame,
            xyz=[float(v) for v in T[:3, 3]],
            quat=rotation_matrix_to_quaternion(T[:3, :3]),
        )
        self._pub_flange.put(encode(FlangeState(t=t, pose=pose).to_wire()))
        with self._tcp_lock:
            tcp_name, tcp_T = self._active_tcp
        if tcp_name == TCP_FLANGE:
            tcp_pose = pose
        else:
            T_tcp = T @ tcp_T
            tcp_pose = Pose(
                frame=self.base_frame,
                xyz=[float(v) for v in T_tcp[:3, 3]],
                quat=rotation_matrix_to_quaternion(T_tcp[:3, :3]),
            )
        self._pub_tcp.put(
            encode(TcpState(t=t, tcp_name=tcp_name, pose=tcp_pose).to_wire())
        )

        with self._latest_lock:
            self._latest_q = list(q)
        with self._rate_lock:
            self._rate_count += 1
            elapsed = time.monotonic() - self._rate_t0
            if elapsed >= 1.0:
                self._rate_hz = self._rate_count / elapsed
                self._rate_count = 0
                self._rate_t0 = time.monotonic()

    @property
    def latest_q(self) -> list[float] | None:
        with self._latest_lock:
            return None if self._latest_q is None else list(self._latest_q)

    @property
    def state_rate_hz(self) -> float:
        with self._rate_lock:
            return self._rate_hz

    # ── state poller (10 Hz io, 1 Hz status) ─────────────────────────────

    def _state_poller(self) -> None:
        tick = 0
        period = 1.0 / _IO_POLL_HZ
        slow_warned = False
        while not self._stop_event.is_set():
            t_start = time.monotonic()
            try:
                with self._state_lock:
                    di, do, ai, ao = self.sdk_state.read_standard_io()
                self._pub_io.put(
                    encode(IoState(t=now_ns(), di=di, do_=do, ai=ai, ao=ao).to_wire())
                )
            except Exception as exc:
                _log.warning("io poll failed: %r", exc)

            if tick % _STATUS_EVERY_N_TICKS == 0:
                try:
                    with self._state_lock:
                        snap = self.sdk_state.status_snapshot()
                    with self._latest_lock:
                        self._latest_status = snap
                    status = ArmStatus(
                        t=now_ns(),
                        mode=snap["mode"],
                        servo_on=snap["servo_on"],
                        estop=snap["estop"],
                        protective_stop=snap["protective_stop"],
                        speed_scale=snap["speed_scale"],
                        active_tcp=self._active_tcp[0],
                        error=snap["error"],
                        state_rate_hz=self.state_rate_hz,
                    )
                    self._pub_status.put(encode(status.to_wire()))
                except Exception as exc:
                    _log.warning("status poll failed: %r", exc)
                self._publish_owner()

            tick += 1
            spent = time.monotonic() - t_start
            if spent > period and not slow_warned:
                # If RPC latency makes 10 Hz unattainable, halve the rate.
                slow_warned = True
                period = 2.0 / _IO_POLL_HZ
                _log.warning(
                    "io poll tick took %.0f ms; halving poll rate to %.1f Hz",
                    spent * 1e3,
                    1.0 / period,
                )
            time.sleep(max(0.0, period - spent))

    # ── command worker (single thread owns sdk_cmd) ──────────────────────

    def _command_worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._cmd_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            fn, future = item
            if not future.set_running_or_notify_cancel():
                continue
            try:
                future.set_result(fn(self.sdk_cmd))
            except Exception as exc:
                future.set_exception(exc)

    def _submit_command(self, fn, timeout_s: float = _CMD_REPLY_TIMEOUT_S):
        future: concurrent.futures.Future = concurrent.futures.Future()
        self._cmd_queue.put((fn, future))
        return future.result(timeout=timeout_s)

    # ── cmd queryables ───────────────────────────────────────────────────

    def _on_set_do(self, query) -> None:
        key = str(query.key_expr)
        try:
            req = SetDo.from_wire(decode(query.payload))
            max_pin = 15 if req.bank == "standard" else 3
            if not 0 <= req.pin <= max_pin:
                raise ValueError(
                    f"pin {req.pin} out of range for bank {req.bank} (0-{max_pin})"
                )
            self._submit_command(
                lambda sdk: sdk.write_do(req.bank, req.pin, req.value)
            )
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    def _on_stop(self, query) -> None:
        """Out-of-band stop: NOT enqueued (the worker may be blocked executing
        a path). Uses sdk_state under its lock.

        The flag is raised BEFORE the (blocking) physical stop so the
        executing path job attributes the halt to cmd_stop (-> aborted)
        instead of mistaking it for a controller fault. An active jog is
        halted smoothly via the runner's ``halt_speed`` (no protective stop),
        so the hard stop is skipped while jogging.
        """
        key = str(query.key_expr)
        try:
            self._jog_stop.set()
            if self.action_server.active_goal_id is not None:
                self._external_stop.set()
            if not self._jog_active.is_set():
                with self._state_lock:
                    self.sdk_state.stop()
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    def _on_clear_protective_stop(self, query) -> None:
        """Operator re-arm: unlock a protective stop (stop-induced or
        external/manual). Out-of-band on the state session, like _on_stop."""
        key = str(query.key_expr)
        try:
            with self._state_lock:
                self.sdk_state.clear_protective_stop()
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    def _on_set_tcp(self, query) -> None:
        """Select the active TCP from the config store (cached at selection
        time — a later store edit does not retroactively change the offset
        until re-selected)."""
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
                    encode(
                        Ack(ok=False, error=f"tcp_not_selectable:{name}").to_wire()
                    ),
                )
                return
            with self._tcp_lock:
                self._active_tcp = (name, tcp_transform(tcp_def))
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    # ── control lease ────────────────────────────────────────────────────

    def _publish_owner(self) -> None:
        try:
            self._pub_owner.put(
                encode(
                    ControlOwnerState(t=now_ns(), owner=_owner_msg(self._lease.owner()))
                    .to_wire()
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
                self._publish_owner()
            owner_dict = owner if owner is not None else self._lease.owner()
            ack = ControlAck(
                ok=err is None, owner=_owner_msg(owner_dict), error=err
            )
            query.reply(key, encode(ack.to_wire()))
        except Exception as exc:
            query.reply(
                key, encode(ControlAck(ok=False, error=repr(exc)).to_wire())
            )

    def _on_release_control(self, query) -> None:
        key = str(query.key_expr)
        try:
            cid = decode(query.payload).get("client_id")
            self._lease.release(cid)
            self._publish_owner()
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    # ── hold-to-jog ──────────────────────────────────────────────────────

    def _on_jog(self, sample) -> None:
        """Zenoh-thread, fast: arm a jog command. Dropped unless the sender
        holds the lease and no goal is running."""
        try:
            cmd = JogCommand.from_wire(decode(sample.payload))
        except Exception as exc:
            _log.warning("jog decode failed: %r", exc)
            return
        if not self._lease.holds(cmd.client_id):
            return
        if self.action_server.active_goal_id is not None:
            return
        with self._jog_lock:
            if not self._jog_active.is_set():
                self._jog_tree = self._live_frames.snapshot()
            self._jog_cmd = cmd
            self._jog_deadline = time.monotonic() + self._jog_watchdog_s
        self._jog_wake.set()

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

    def _jog_runner(self) -> None:
        """Drive ``speedJoint`` from armed jog commands; the in-driver 250 ms
        watchdog halts via ``halt_speed`` when commands stop arriving, the
        lease lapses, a goal starts, or cmd/stop fires."""
        period = 1.0 / self._jog_loop_hz
        while not self._stop_event.is_set():
            if not self._jog_wake.wait(timeout=0.5):
                continue
            self._jog_wake.clear()
            self._jog_stop.clear()
            self._jog_active.set()
            try:
                while not self._stop_event.is_set() and not self._jog_stop.is_set():
                    with self._jog_lock:
                        cmd = self._jog_cmd
                        deadline = self._jog_deadline
                        tree = self._jog_tree
                    if cmd is None or time.monotonic() >= deadline:
                        break  # watchdog
                    if not self._lease.holds(cmd.client_id):
                        break
                    if self.action_server.active_goal_id is not None:
                        break
                    q = self.latest_q
                    if q is None:
                        break
                    ref_R = self._jog_ref_R(cmd, q, tree)
                    if ref_R is None:
                        _log.warning("jog frame %r unresolved; halting", cmd.frame)
                        break
                    with self._tcp_lock:
                        tcp_T = self._active_tcp[1]
                    qd = jog_joint_velocity(
                        self.fk, q, mode=cmd.mode, velocity=cmd.velocity,
                        ref_R=ref_R, tcp_T=tcp_T, jog_vmax=self._jog_vmax,
                        damping=self._jog_damping,
                    )
                    try:
                        rc = self._submit_command(
                            lambda sdk: sdk.speed_joint(qd, self._jog_acc),
                            timeout_s=1.0,
                        )
                    except Exception as exc:
                        _log.warning("jog speed_joint failed: %r", exc)
                        break
                    if rc != 0:
                        _log.warning("jog speed_joint rc=%s; halting", rc)
                        break
                    time.sleep(period)
            finally:
                try:
                    self._submit_command(
                        lambda sdk: sdk.halt_speed(self._jog_acc), timeout_s=1.0
                    )
                except Exception as exc:
                    _log.warning("jog halt failed: %r", exc)
                self._jog_active.clear()
                self._jog_stop.clear()

    # ── execute_path action ──────────────────────────────────────────────

    def _accept_execute_path(self, goal: dict) -> str | None:
        # Lease/jog gate runs BEFORE preconditions (design Appendix A):
        # a jog in flight or a missing/lapsed lease is rejected up front.
        if self._jog_active.is_set():
            return "jog_active"
        cid = goal.get("client_id") if isinstance(goal, dict) else None
        if not cid or not self._lease.holds(cid):
            return "no_control"
        needs_frames = isinstance(goal, dict) and any(
            "pose" in (wp.get("target") or {})
            for wp in (goal.get("waypoints") or [])
            if isinstance(wp, dict)
        )
        # Scene obstacles may reference any frame regardless of waypoint form,
        # so the tree is always needed for the collision preflight.
        # Pick up config frame/scene edits since startup so a UI-added frame or
        # scene change resolves without a driver restart (uniform with the
        # per-selection TCP fetch); an empty fetch keeps the last good layer.
        self._live_frames.refresh_static(self.session)
        self._live_scene.refresh_static(self.session)
        tree = self._live_frames.snapshot()
        q_start = self.latest_q
        if q_start is None and needs_frames:
            return "no_joint_state"
        with self._tcp_lock:
            tcp_name, tcp_T = self._active_tcp
        reason, resolution = resolve_goal(
            goal,
            fk=self.fk,
            rid=self.rid,
            q_start=q_start or [0.0] * 6,
            jmin=self.jmin,
            jmax=self.jmax,
            margin=self.params["joint_limit_margin_rad"],
            tree=tree,
            tcp_name=tcp_name,
            tcp_T=tcp_T,
        )
        if reason:
            return reason
        collision = preflight(
            resolution,
            self._live_scene.snapshot(),
            model=self.collision,
            tree=tree,
            base_frame=self.base_frame,
        )
        if collision:
            return collision
        status = self._latest_status or {}
        if status.get("estop") or status.get("protective_stop"):
            return "safety_stop_active"
        return None

    def _execute_path(self, handle: GoalHandle) -> None:
        # Runs on the ActionServer worker; the actual SDK work is a single
        # blocking job on the command worker so ALL sdk_cmd calls stay on one
        # thread.
        self._external_stop.clear()
        try:
            self._submit_command(
                lambda sdk: self._run_path_job(sdk, handle), timeout_s=None
            )
        except Exception as exc:
            if not handle.is_terminal:
                handle.fail(error=repr(exc))
            return
        # _run_path_job terminates the goal itself.

    def _run_path_job(self, sdk: AuboSession, handle: GoalHandle) -> None:
        resolution = handle.goal.pop("_resolution", None)
        snapshot = {
            "t": now_ns(),
            "goal_id": handle.goal_id,
            "rid": self.rid,
            "realm": self.realm,
            "speed_scale": 1.0,
            "versions": {"driver": _driver_version()},
            **resolution,
        }
        self.session.put(
            f"{keys.action_prefix(self.realm, self.rid)}/{handle.goal_id}/snapshot",
            encode(snapshot),
        )

        goal = ExecutePathGoal.from_wire(handle.goal)
        targets = [list(wp.target["q"]) for wp in goal.waypoints]

        start_q = self.latest_q
        if start_q is None:
            start_q = sdk.joint_positions()

        # Zero-motion short-circuit: every target already at the current pose.
        if all(joints_close(start_q, t) for t in targets):
            handle.feedback(1.0, current_wp=len(targets))
            handle.succeed(snapshot=snapshot)
            return

        ruckig = self.params["ruckig_defaults"]
        vmax, amax, jmax = ruckig["vmax"], ruckig["amax"], ruckig["jmax"]

        traj, wp_idx = generate_ruckig_trajectory(
            [start_q] + targets, self.servo_dt, vmax=vmax, amax=amax, jmax=jmax
        )
        violation = validate_trajectory(
            traj, self.jmin, self.jmax, margin=self.params["joint_limit_margin_rad"]
        )
        if violation:
            handle.fail(error=violation)
            return

        total_s = len(traj) * self.servo_dt
        _log.info(
            "goal %s: %d samples, %.1fs, %d waypoint(s)",
            handle.goal_id,
            len(traj),
            total_s,
            len(targets),
        )

        try:
            if not joints_close(start_q, traj[0]):
                sdk.move_joint(traj[0])

            t0: list[float] = []
            tick_count = [0]

            def tick() -> bool:
                if not t0:
                    t0.append(time.monotonic())
                tick_count[0] += 1
                if tick_count[0] % _FEEDBACK_EVERY_N_TICKS == 0:
                    elapsed = time.monotonic() - t0[0]
                    progress = min(1.0, elapsed / total_s) if total_s > 0 else 1.0
                    current_wp = min(
                        bisect.bisect_left(wp_idx, elapsed / self.servo_dt),
                        len(targets) - 1,
                    )
                    handle.feedback(progress, current_wp=current_wp)
                return not (handle.cancel_requested or self._external_stop.is_set())

            sdk.execute_path_buffer(traj, vmax, amax, on_tick=tick)
        except Exception as exc:
            handle.fail(error=repr(exc))
            return

        if handle.cancel_requested:
            # Cancel is a routine operation: auto-clear the stop-induced
            # ProtectiveStop so back-to-back goals stay ergonomic. cmd_stop
            # (below) deliberately leaves it for the operator to clear.
            try:
                sdk.clear_protective_stop()
            except Exception:
                _log.warning("auto-clear after cancel failed", exc_info=True)
            handle.set_canceled()
        elif self._external_stop.is_set():
            self._external_stop.clear()
            handle.abort(cause="cmd_stop")
        else:
            # The controller ends the exec id without reporting WHY — a
            # genuine protective stop mid-path also lands here. Only report
            # success when the arm actually reached the trajectory end
            # (observed live: a safety halt otherwise yields a false
            # `succeeded` mid-path).
            if joints_close(sdk.joint_positions(), traj[-1], tol=0.02):
                handle.succeed(snapshot=snapshot)
            else:
                handle.fail(
                    error="motion_incomplete: controller halted before the trajectory end"
                )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="aubo_driver", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument("--resource", default="r1", help="resource id (default r1)")
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    params = load_resource(args.cell, args.resource)
    session = open_session(args.zenoh_config)
    token = declare_alive(session, args.realm, "arm", args.resource)

    driver = AuboDriver(session, args.realm, args.resource, params)
    try:
        driver.start()
        driver.run_forever()
    finally:
        del token
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
