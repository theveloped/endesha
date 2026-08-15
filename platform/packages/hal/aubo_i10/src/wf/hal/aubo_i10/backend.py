"""AuboBackend: the real Aubo i10 hardware behind the shared ``ArmCore``.

Holds the Aubo SDK seam — two RPC connections (the SDK is not shared across
concurrent threads): ``sdk_cmd`` owned exclusively by the command worker, and
``sdk_state`` owned by the state-poller thread and the out-of-band ``cmd/stop``
path (guarded by a lock). State arrives over a 200 Hz RTDE stream. Motion
(jog speed_joint, move_joint, execute_path_buffer) is serialized onto the
single command worker; the core supplies the contract logic + trajectory.

Extracted verbatim (behaviour-preserving) from the former ``AuboDriver``.
"""

from __future__ import annotations

import bisect
import concurrent.futures
import math
import queue
import threading
import time

from wf.core.log import get_logger
from wf.core.time import CLOCK_HOST, CLOCK_ROBOT, now_ns
from wf.hal.arm_core import ArmBackend
from wf.world_model.trajectory import joints_close

from .rtde import RtdeStream
from .sdk import AuboSession
from .timesync import RobotTimeSync

_log = get_logger("wf.hal.aubo_i10.backend")

_IO_POLL_HZ = 10.0
_STATUS_EVERY_N_TICKS = 10  # -> 1 Hz status at 10 Hz io polling
_CMD_REPLY_TIMEOUT_S = 2.0
_FEEDBACK_EVERY_N_TICKS = 4  # 50 ms ticks -> ~5 Hz feedback


class AuboBackend(ArmBackend):
    def __init__(self, params: dict):
        self.params = params
        self.core = None
        self.timesync = RobotTimeSync()

        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()  # guards sdk_state RPC calls
        self._latest_lock = threading.Lock()
        self._latest_q: list[float] | None = None
        self._latest_status: dict | None = None
        self._warned_host_clock = False

        self._cmd_queue: queue.Queue = queue.Queue()
        self.sdk_cmd: AuboSession | None = None
        self.sdk_state: AuboSession | None = None
        self.rtde: RtdeStream | None = None

        self._jog_acc = params.get("jog_acc", 2.0)
        self._jog_loop_hz = params.get("jog_loop_hz", 50)
        self._jog_wake = threading.Event()  # wake the runner when a jog arms
        self._jog_stop = threading.Event()  # cmd/stop halts an active jog

    # ── lifecycle ─────────────────────────────────────────────────────────

    def start(self, core) -> None:
        self.core = core
        ip = self.params["ip"]
        rpc_port = self.params["rpc_port"]
        login = self.params.get("login") or {}
        user = login.get("user", "aubo")
        password = str(login.get("pass", "123456"))

        self.sdk_cmd = AuboSession(ip, rpc_port, user, password).__enter__()
        self.sdk_state = AuboSession(ip, rpc_port, user, password).__enter__()

        # Hardware truth overrides the URDF-derived defaults the core set up.
        core.jmin, core.jmax = self.sdk_cmd.joint_limits()
        core.servo_dt = self.sdk_cmd.servo_cycle(self.params["servo_cycle_s"])
        try:
            self.timesync.calibrate_robot(self.sdk_cmd.controller_time_ns())
        except Exception as exc:
            _log.warning(
                "controller time calibration failed (%r); using host clock", exc
            )
        _log.info(
            "limits jmin=%s jmax=%s servo_dt=%.4f", core.jmin, core.jmax, core.servo_dt
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
        _log.info("aubo backend up: rid=%s ip=%s", core.rid, ip)

    def shutdown(self) -> None:
        self._stop_event.set()
        self._jog_wake.set()  # release the jog runner from its wait
        if self.rtde is not None:
            self.rtde.stop()
        for sdk in (self.sdk_cmd, self.sdk_state):
            if sdk is not None:
                sdk.__exit__(None, None, None)

    # ── RTDE thread (200 Hz) → core publish ──────────────────────────────

    def _on_rtde_sample(self, controller_ts_s, q, qd, current) -> None:
        if self.timesync.calibrated and math.isfinite(controller_ts_s):
            t = self.timesync.robot_time_ns(controller_ts_s)
            domain = CLOCK_ROBOT
        else:
            # Observed: some controller builds stream `timestamp: null` over
            # RTDE -> NaN; stamp with the host clock instead.
            t = now_ns()
            domain = CLOCK_HOST
            if not self._warned_host_clock:
                self._warned_host_clock = True
                _log.warning(
                    "RTDE timestamp unusable (ts=%r); stamping with host clock",
                    controller_ts_s,
                )
        with self._latest_lock:
            self._latest_q = list(q)
        # The core builds JointState/FlangeState/TcpState (FK + active TCP),
        # enforces a strictly-increasing stamp, and advances the rate counter.
        self.core.publish_motion(list(q), list(qd), list(current), t, domain)

    # ── core seam ─────────────────────────────────────────────────────────

    def latest_q(self) -> list[float] | None:
        with self._latest_lock:
            return None if self._latest_q is None else list(self._latest_q)

    def motion_block_reason(self, *, for_goal: bool) -> str | None:
        # Jog is not gated on estop here (parity with the prior driver — the
        # controller rejects speed_joint under estop anyway); goals are.
        if not for_goal:
            return None
        with self._latest_lock:
            status = self._latest_status or {}
        if status.get("estop") or status.get("protective_stop"):
            return "safety_stop_active"
        return None

    def set_do(self, bank: str, pin: int, value: int) -> None:
        max_pin = 15 if bank == "standard" else 3
        if not 0 <= pin <= max_pin:
            raise ValueError(f"pin {pin} out of range for bank {bank} (0-{max_pin})")
        self._submit_command(lambda sdk: sdk.write_do(bank, pin, value))

    def stop(self) -> None:
        """Out-of-band stop. The core has already raised its stop flag and
        disarmed the jog command; halt an active jog smoothly via the runner's
        ``halt_speed`` (no protective stop), else hard-stop on sdk_state."""
        self._jog_stop.set()
        if not self.core.jog_active:
            with self._state_lock:
                self.sdk_state.stop()

    def clear_protective_stop(self) -> None:
        with self._state_lock:
            self.sdk_state.clear_protective_stop()

    def on_jog_armed(self) -> None:
        self._jog_wake.set()

    # ── state poller (10 Hz io, 1 Hz status) ─────────────────────────────

    def _state_poller(self) -> None:
        core = self.core
        tick = 0
        period = 1.0 / _IO_POLL_HZ
        slow_warned = False
        while not self._stop_event.is_set():
            t_start = time.monotonic()
            try:
                with self._state_lock:
                    di, do, ai, ao = self.sdk_state.read_standard_io()
                core.publish_io(di, do, ai, ao)
            except Exception as exc:
                _log.warning("io poll failed: %r", exc)

            if tick % _STATUS_EVERY_N_TICKS == 0:
                try:
                    with self._state_lock:
                        snap = self.sdk_state.status_snapshot()
                    with self._latest_lock:
                        self._latest_status = snap
                    core.publish_status(
                        mode=snap["mode"],
                        servo_on=snap["servo_on"],
                        estop=snap["estop"],
                        protective_stop=snap["protective_stop"],
                        speed_scale=snap["speed_scale"],
                        error=snap["error"],
                    )
                except Exception as exc:
                    _log.warning("status poll failed: %r", exc)

            tick += 1
            spent = time.monotonic() - t_start
            if spent > period and not slow_warned:
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

    def _submit_command(self, fn, timeout_s: float | None = _CMD_REPLY_TIMEOUT_S):
        future: concurrent.futures.Future = concurrent.futures.Future()
        self._cmd_queue.put((fn, future))
        return future.result(timeout=timeout_s)

    # ── hold-to-jog runner ───────────────────────────────────────────────

    def _jog_runner(self) -> None:
        """Drive ``speedJoint`` from the core's jog gate. ``core.jog_step``
        owns the lease/goal/watchdog/frame gating and returns the velocity to
        send; this loop applies it and halts via ``halt_speed`` when the step
        disarms (watchdog/lease/goal/frame), cmd/stop fires, or shutdown."""
        period = 1.0 / self._jog_loop_hz
        while not self._stop_event.is_set():
            if not self._jog_wake.wait(timeout=0.5):
                continue
            self._jog_wake.clear()
            self._jog_stop.clear()
            try:
                while not self._stop_event.is_set() and not self._jog_stop.is_set():
                    qd = self.core.jog_step()
                    if qd is None or not any(qd):
                        break  # idle or freeze sentinel -> halt in finally
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

    # ── path execution (the SDK job on the command worker) ───────────────

    def run_path(self, handle, traj, wp_idx, targets, snapshot) -> None:
        # Runs on the ActionServer worker; the actual SDK work is a single
        # blocking job on the command worker so ALL sdk_cmd calls stay on one
        # thread. The core already generated + validated the trajectory.
        try:
            self._submit_command(
                lambda sdk: self._run_path_job(
                    sdk, handle, traj, wp_idx, targets, snapshot
                ),
                timeout_s=None,
            )
        except Exception as exc:
            if not handle.is_terminal:
                handle.fail(error=repr(exc))

    def _run_path_job(self, sdk, handle, traj, wp_idx, targets, snapshot) -> None:
        core = self.core
        start_q = self.latest_q() or sdk.joint_positions()
        ruckig = self.params["ruckig_defaults"]
        vmax, amax = ruckig["vmax"], ruckig["amax"]
        total_s = len(traj) * core.servo_dt

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
                        bisect.bisect_left(wp_idx, elapsed / core.servo_dt),
                        len(targets) - 1,
                    )
                    handle.feedback(progress, current_wp=current_wp)
                return not (handle.cancel_requested or core.stop_requested())

            sdk.execute_path_buffer(traj, vmax, amax, on_tick=tick)
        except Exception as exc:
            handle.fail(error=repr(exc))
            return

        if handle.cancel_requested:
            # Cancel is routine: auto-clear the stop-induced ProtectiveStop so
            # back-to-back goals stay ergonomic. cmd_stop deliberately leaves it.
            try:
                sdk.clear_protective_stop()
            except Exception:
                _log.warning("auto-clear after cancel failed", exc_info=True)
            handle.set_canceled()
        elif core.stop_requested():
            core.clear_stop()
            handle.abort(cause="cmd_stop")
        else:
            # The controller ends the exec id without reporting WHY — a genuine
            # protective stop mid-path also lands here. Only report success when
            # the arm actually reached the trajectory end.
            if joints_close(sdk.joint_positions(), traj[-1], tol=0.02):
                handle.succeed(snapshot=snapshot)
            else:
                handle.fail(
                    error="motion_incomplete: controller halted before the trajectory end"
                )
