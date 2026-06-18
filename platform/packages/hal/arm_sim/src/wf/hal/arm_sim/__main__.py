"""The `arm_sim` driver process (roadmap §10 item 6).

Simulates THIS cell's arm (Aubo i10): reuses the aubo package's ruckig
trajectory generation and URDF FK via a normal dependency. Crash-only like
the aubo driver: no state to restore; on restart everything is re-declared
(liveliness re-asserts).

Mirror mode (``--mirror <realm>``): subscribes that realm's
``arm/{rid}/state/joints``, shadows ``q``/``qd``, and republishes under this
realm with fresh ``t = now_ns()`` — replayed payloads carry old data-time;
reusing it would trip the UI's 3 s staleness rule. While mirroring,
``execute_path`` goals are rejected with reason ``"mirroring"``; ``set_do``
still works (sim-local DO bits).
"""

from __future__ import annotations

import argparse
import bisect
import importlib.metadata
import os
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
    SetDo,
    TcpState,
)
from wf.core.action import ActionServer, GoalHandle
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import CLOCK_HOST, now_ns
from wf.world_model.fk import UrdfFk
from wf.world_model.trajectory import (
    TrajectoryError,
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
from wf.hal.aubo_i10 import BUNDLED_URDF

from .config import load_resource
from .sim import SimArm, pose_from_transform

_log = get_logger("wf.hal.arm_sim.driver")

_IO_EVERY_N_TICKS = 20  # 200 Hz ticks -> 10 Hz io
_STATUS_EVERY_N_TICKS = 200  # -> 1 Hz status
_FEEDBACK_EVERY_N_SAMPLES = 40  # 5 ms samples -> ~5 Hz feedback


def _driver_version() -> str:
    try:
        return importlib.metadata.version("wf-hal-arm-sim")
    except Exception:
        return "unknown"


def _owner_msg(owner_dict: dict | None) -> ControlOwner | None:
    """ControlOwner message from a ControlLease owner dict (or None)."""
    return None if owner_dict is None else ControlOwner.from_wire(owner_dict)


class SimArmDriver:
    def __init__(
        self,
        session,
        realm: str,
        rid: str,
        params: dict,
        mirror_realm: str | None = None,
    ):
        self.session = session
        self.realm = realm
        self.rid = rid
        self.params = params
        self.mirror_realm = mirror_realm
        urdf_path = params.get("urdf") or BUNDLED_URDF
        fk = UrdfFk(urdf_path)
        self.sim = SimArm(fk, params["home_q"])
        self.collision = CollisionModel(urdf_path, Path(urdf_path).parent.parent)
        # Static config frames merged with subscribed dynamic {realm}/frames/**.
        self._live_frames, self._frames_sub = build_live_tree(session, realm)
        # Static config scene merged with subscribed runtime {realm}/scene/**.
        self._live_scene, self._scene_sub = build_live_scene(session, realm)
        all_limits = fk.get_joint_limits()
        self._limits = [all_limits[name] for name in fk.JOINT_ORDER]
        self._jmin = [lo for lo, _hi in self._limits]
        self._jmax = [hi for _lo, hi in self._limits]
        self.servo_dt: float = params["servo_cycle_s"]

        self._lock = threading.Lock()  # guards SimArm
        self._stop_event = threading.Event()
        self._external_stop = threading.Event()  # cmd/stop -> abort
        self._last_t = 0  # strictly-increasing stamp guard (tick thread only)

        # Active TCP: driver-local, reset to "flange" on restart (crash-only).
        self._tcp_lock = threading.Lock()
        self._active_tcp: tuple[str, np.ndarray] = (TCP_FLANGE, np.eye(4))

        # measured joints publish rate (tick thread writes, status reads)
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
        self._mirror_sub = None

        # ── control lease + hold-to-jog (mirrors aubo_i10) ───────────────
        self._lease = ControlLease(params.get("lease_ttl_s", 30.0))
        self._pub_owner = session.declare_publisher(
            keys.state_control_owner(realm, rid)
        )
        self._jog_vmax = params.get("jog_vmax", 0.5)
        self._jog_watchdog_s = params.get("jog_watchdog_s", 0.25)
        self._jog_damping = params.get("jog_damping", 0.05)
        # Jog state guarded by self._lock (read+integrated in the tick loop).
        self._jog_cmd: JogCommand | None = None
        self._jog_deadline = 0.0  # time.monotonic() deadline
        self._jog_tree = None  # FrameTree snapshot taken at jog start
        self._jog_active = False  # a jog is currently being applied
        self._jog_sub = None

    # ── startup ──────────────────────────────────────────────────────────

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

        if self.mirror_realm:
            self._mirror_sub = self.session.declare_subscriber(
                keys.state_joints(self.mirror_realm, self.rid),
                self._on_mirror_sample,
            )

        threading.Thread(target=self._tick_loop, name="sim-tick", daemon=True).start()
        _log.info(
            "arm_sim up: realm=%s rid=%s mirror=%s",
            self.realm,
            self.rid,
            self.mirror_realm or "<off>",
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
        self.action_server.close()
        for q in self._queryables:
            try:
                q.undeclare()
            except Exception:
                pass
        if self._jog_sub is not None:
            try:
                self._jog_sub.undeclare()
            except Exception:
                pass
        if self._mirror_sub is not None:
            try:
                self._mirror_sub.undeclare()
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
        _log.info("arm_sim stopped")

    # ── mirror subscriber (zenoh thread) ─────────────────────────────────

    def _on_mirror_sample(self, sample) -> None:
        try:
            msg = JointState.from_wire(decode(sample.payload))
        except Exception as exc:
            _log.warning("mirror sample decode failed: %r", exc)
            return
        with self._lock:
            self.sim.set_q(msg.q, msg.qd)

    # ── tick loop (the only state thread; 200 Hz) ────────────────────────

    def _tick_loop(self) -> None:
        dt = self.servo_dt
        tick = 0
        next_t = time.monotonic()
        while not self._stop_event.is_set():
            next_t += dt
            now = time.monotonic()
            if next_t > now:
                time.sleep(next_t - now)
            elif next_t < now - 0.5:
                next_t = now  # fell badly behind; resync instead of bursting

            with self._lock:
                self._apply_jog(dt)
                q = list(self.sim.q)
                qd = list(self.sim.qd)
                di = self.sim.di_bits
                do = self.sim.do_bits

            T = self.sim.fk.get_ee_transform(q)
            pose = pose_from_transform(T, keys.base_frame(self.rid))
            with self._tcp_lock:
                tcp_name, tcp_T = self._active_tcp
            tcp_pose = (
                pose
                if tcp_name == TCP_FLANGE
                else pose_from_transform(T @ tcp_T, keys.base_frame(self.rid))
            )

            t = now_ns()
            if t <= self._last_t:
                t = self._last_t + 1
            self._last_t = t

            self._pub_joints.put(
                encode(
                    JointState(
                        t=t, q=q, qd=qd, tau=[0.0] * 6, clock_domain=CLOCK_HOST
                    ).to_wire()
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

            tick += 1
            if tick % _IO_EVERY_N_TICKS == 0:
                self._pub_io.put(
                    encode(
                        IoState(
                            t=now_ns(), di=di, do_=do, ai=[0.0, 0.0], ao=[0.0, 0.0]
                        ).to_wire()
                    )
                )
            if tick % _STATUS_EVERY_N_TICKS == 0:
                mode = (
                    f"Mirroring({self.mirror_realm})"
                    if self.mirror_realm
                    else "Simulated"
                )
                status = ArmStatus(
                    t=now_ns(),
                    mode=mode,
                    servo_on=True,
                    estop=False,
                    protective_stop=False,
                    speed_scale=1.0,
                    active_tcp=self._active_tcp[0],
                    error=None,
                    state_rate_hz=self.state_rate_hz,
                )
                self._pub_status.put(encode(status.to_wire()))
                self._publish_owner()

    @property
    def state_rate_hz(self) -> float:
        with self._rate_lock:
            return self._rate_hz

    # ── cmd queryables ───────────────────────────────────────────────────

    def _on_set_do(self, query) -> None:
        key = str(query.key_expr)
        try:
            req = SetDo.from_wire(decode(query.payload))
            with self._lock:
                self.sim.set_do(req.bank, req.pin, req.value)
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=str(exc)).to_wire()))

    def _on_stop(self, query) -> None:
        """Out-of-band stop: aborts the active goal and clears an armed jog."""
        key = str(query.key_expr)
        self._external_stop.set()
        with self._lock:
            self._jog_cmd = None  # disarm any active jog (tick loop freezes qd)
        query.reply(key, encode(Ack(ok=True).to_wire()))

    def _on_clear_protective_stop(self, query) -> None:
        """No fault simulation in v0 — always ok as a no-op."""
        key = str(query.key_expr)
        query.reply(key, encode(Ack(ok=True).to_wire()))

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
        holds the lease, no goal is running, and we are not mirroring."""
        try:
            cmd = JogCommand.from_wire(decode(sample.payload))
        except Exception as exc:
            _log.warning("jog decode failed: %r", exc)
            return
        if self.mirror_realm:
            return
        if not self._lease.holds(cmd.client_id):
            return
        if self.action_server.active_goal_id is not None:
            return
        with self._lock:
            if not self._jog_active:
                self._jog_tree = self._live_frames.snapshot()
            self._jog_cmd = cmd
            self._jog_deadline = time.monotonic() + self._jog_watchdog_s

    def _jog_ref_R(self, cmd: JogCommand, q, tree) -> np.ndarray | None:
        """3x3 rotation of the reference frame's axes in the arm base, or None
        when the named frame is unknown."""
        base = keys.base_frame(self.rid)
        if cmd.frame == "tool":
            with self._tcp_lock:
                tcp_R = self._active_tcp[1][:3, :3]
            R_flange = self.sim.fk.get_ee_transform(q)[:3, :3]
            return R_flange @ tcp_R
        name = base if cmd.frame == "base" else cmd.frame
        try:
            return tree.resolve(name, base)[:3, :3]
        except FrameUnknown:
            return None

    def _apply_jog(self, dt: float) -> None:
        """Integrate one armed jog command into SimArm. Caller holds
        ``self._lock``. Watchdog expiry / lease loss / goal start / mirroring
        freezes the arm (qd=0) — the arm holds its last pose."""
        cmd = self._jog_cmd
        armed = (
            cmd is not None
            and not self.mirror_realm
            and self.action_server.active_goal_id is None
            and time.monotonic() < self._jog_deadline
            and self._lease.holds(cmd.client_id)
        )
        if not armed:
            if self._jog_active:
                self.sim.set_q(self.sim.q, [0.0] * 6)  # freeze: arm holds
            self._jog_active = False
            return
        q = list(self.sim.q)
        ref_R = self._jog_ref_R(cmd, q, self._jog_tree)
        if ref_R is None:
            self.sim.set_q(q, [0.0] * 6)
            self._jog_active = False
            return
        with self._tcp_lock:
            tcp_T = self._active_tcp[1]
        qd = jog_joint_velocity(
            self.sim.fk, q, mode=cmd.mode, velocity=cmd.velocity,
            ref_R=ref_R, tcp_T=tcp_T, jog_vmax=self._jog_vmax,
            damping=self._jog_damping,
        )
        new_q = [
            min(max(q[j] + qd[j] * dt, self._jmin[j]), self._jmax[j])
            for j in range(6)
        ]
        self.sim.set_q(new_q, qd)
        self._jog_active = True

    # ── execute_path action ──────────────────────────────────────────────

    def _accept_execute_path(self, goal: dict) -> str | None:
        if self.mirror_realm:
            return "mirroring"
        # Lease/jog gate before the resolve/preflight preconditions.
        with self._lock:
            jog_active = self._jog_active
        if jog_active:
            return "jog_active"
        cid = goal.get("client_id") if isinstance(goal, dict) else None
        if not cid or not self._lease.holds(cid):
            return "no_control"
        # Scene obstacles may reference any frame regardless of waypoint form,
        # so the tree is always needed for the collision preflight.
        # Pick up config frame/scene edits since startup so a UI-added frame or
        # scene change resolves without a driver restart (uniform with the
        # per-selection TCP fetch); an empty fetch keeps the last good layer.
        self._live_frames.refresh_static(self.session)
        self._live_scene.refresh_static(self.session)
        tree = self._live_frames.snapshot()
        with self._lock:
            q_start = list(self.sim.q)
        with self._tcp_lock:
            tcp_name, tcp_T = self._active_tcp
        reason, resolution = resolve_goal(
            goal,
            fk=self.sim.fk,
            rid=self.rid,
            q_start=q_start,
            jmin=self._jmin,
            jmax=self._jmax,
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
            base_frame=keys.base_frame(self.rid),
        )

    def _execute_path(self, handle: GoalHandle) -> None:
        # Runs on the ActionServer worker thread; it may block — the server
        # is serial and enforces single-active-goal/busy for free.
        self._external_stop.clear()
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

        with self._lock:
            start_q = list(self.sim.q)

        # Zero-motion short-circuit: every target already at the current pose.
        if all(joints_close(start_q, t) for t in targets):
            handle.feedback(1.0, current_wp=len(targets))
            handle.succeed(snapshot=snapshot)
            return

        ruckig = self.params["ruckig_defaults"]
        dt = self.servo_dt
        try:
            traj, wp_idx = generate_ruckig_trajectory(
                [start_q] + targets,
                dt,
                vmax=ruckig["vmax"],
                amax=ruckig["amax"],
                jmax=ruckig["jmax"],
            )
        except TrajectoryError as exc:
            handle.fail(error=str(exc))
            return
        violation = validate_trajectory(
            traj, self._jmin, self._jmax, margin=self.params["joint_limit_margin_rad"]
        )
        if violation:
            handle.fail(error=violation)
            return

        total_s = len(traj) * dt
        _log.info(
            "goal %s: %d samples, %.1fs, %d waypoint(s)",
            handle.goal_id,
            len(traj),
            total_s,
            len(targets),
        )

        # Playback: the sim IS the trajectory — drive SimArm sample by sample.
        prev = start_q
        next_t = time.monotonic()
        for i, q in enumerate(traj):
            next_t += dt
            delay = next_t - time.monotonic()
            if delay > 0:
                time.sleep(delay)

            if handle.cancel_requested or self._external_stop.is_set():
                with self._lock:
                    self.sim.set_q(self.sim.q, [0.0] * 6)  # freeze at current sample
                if handle.cancel_requested:
                    handle.set_canceled()
                else:
                    self._external_stop.clear()
                    handle.abort(cause="cmd_stop")
                return

            qd = [(q[j] - prev[j]) / dt for j in range(6)]
            with self._lock:
                self.sim.set_q(q, qd)
            prev = q

            if (i + 1) % _FEEDBACK_EVERY_N_SAMPLES == 0:
                current_wp = min(bisect.bisect_left(wp_idx, i + 1), len(targets) - 1)
                handle.feedback((i + 1) / len(traj), current_wp=current_wp)

        with self._lock:
            self.sim.set_q(traj[-1], [0.0] * 6)
        # No joints_close final check needed — the sim is the trajectory by
        # construction.
        handle.succeed(snapshot=snapshot)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="arm_sim", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument("--resource", default="r1", help="resource id (default r1)")
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    parser.add_argument(
        "--mirror",
        default=None,
        metavar="REALM",
        help="shadow this realm's state/joints (e.g. 'live', 'replay/demo'); "
        "execute_path goals are rejected while mirroring",
    )
    args = parser.parse_args(argv)

    params = load_resource(args.cell, args.resource)
    session = open_session(args.zenoh_config)
    token = declare_alive(session, args.realm, "arm", args.resource)

    driver = SimArmDriver(session, args.realm, args.resource, params, args.mirror)
    try:
        driver.start()
        driver.run_forever()
    finally:
        del token
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
