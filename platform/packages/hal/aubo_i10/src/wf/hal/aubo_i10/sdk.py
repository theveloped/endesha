"""AuboSession: RPC wrapper around pyaubo_sdk (lifted from the proven CLI).

`pyaubo_sdk` is imported lazily inside `__enter__` so this module imports on
machines without the vendor SDK.
"""

from __future__ import annotations

import math
import time
from typing import Callable

from wf.core.log import get_logger

_log = get_logger("wf.hal.aubo_i10.sdk")

# MoveIt fallback joint limits (rad) — see reference get_joint_limits.
_FALLBACK_JMIN = [-2.95, -2.95, -3.14, -2.95, -2.95, -3.14]
_FALLBACK_JMAX = [2.95, 2.95, 3.14, 2.95, 2.95, 3.14]

_PATH_BUFFER_NAME = "hal_traj"
# Chunked append at 50 samples: larger chunks have been observed to fail
# silently on some controllers (reference gotcha).
_APPEND_CHUNK = 50


class AuboSession:
    """Context manager owning one RpcClient connection.

    Never share one instance across concurrent threads — the driver opens two
    (command worker + state poller).
    """

    def __init__(
        self,
        ip: str,
        port: int = 30004,
        user: str = "aubo",
        password: str = "123456",
        request_timeout_ms: int = 5000,
    ):
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        self.request_timeout_ms = request_timeout_ms
        self.rpc = None
        self.robot = None

    def __enter__(self) -> "AuboSession":
        import pyaubo_sdk

        rpc = pyaubo_sdk.RpcClient()
        rpc.setRequestTimeout(self.request_timeout_ms)
        rpc.connect(self.ip, self.port)
        if not rpc.hasConnected():
            raise ConnectionError(f"cannot connect to robot at {self.ip}:{self.port}")
        rpc.login(self.user, self.password)
        if not rpc.hasLogined():
            rpc.disconnect()
            raise ConnectionError(f"login failed at {self.ip}:{self.port}")
        robot_name = rpc.getRobotNames()[0]
        self.rpc = rpc
        self.robot = rpc.getRobotInterface(robot_name)
        _log.info("RPC connected to %s:%s (robot: %s)", self.ip, self.port, robot_name)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.rpc is not None:
            try:
                self.rpc.logout()
            except Exception:
                pass
            try:
                self.rpc.disconnect()
            except Exception:
                pass
        self.rpc = None
        self.robot = None

    # ── config / state reads ─────────────────────────────────────────────

    def joint_limits(self) -> tuple[list[float], list[float]]:
        """(jmin, jmax) in radians; MoveIt fallback when the SDK call fails."""
        cfg = self.robot.getRobotConfig()
        try:
            jmax = list(cfg.getJointMaxPositions())
            jmin = list(cfg.getJointMinPositions())
            if len(jmin) == 6 and len(jmax) == 6:
                return jmin, jmax
        except Exception:
            pass
        return list(_FALLBACK_JMIN), list(_FALLBACK_JMAX)

    def servo_cycle(self, default_dt: float = 0.005) -> float:
        try:
            dt = self.robot.getRobotConfig().getCycletime()
            if dt and dt > 0:
                return dt
        except Exception:
            pass
        return default_dt

    def joint_positions(self) -> list[float]:
        return list(self.robot.getRobotState().getJointPositions())

    def read_standard_io(self) -> tuple[int, int, list[float], list[float]]:
        """(di_bits, do_bits, ai, ao) — standard bank, LSB = pin 0."""
        io = self.robot.getIoControl()
        di = 0
        do = 0
        for i in range(16):
            if io.getStandardDigitalInput(i):
                di |= 1 << i
            if io.getStandardDigitalOutput(i):
                do |= 1 << i
        ai = [float(io.getStandardAnalogInput(i)) for i in range(2)]
        ao = [float(io.getStandardAnalogOutput(i)) for i in range(2)]
        return di, do, ai, ao

    def write_do(self, bank: str, pin: int, value: bool) -> None:
        io = self.robot.getIoControl()
        if bank == "standard":
            io.setStandardDigitalOutput(pin, bool(value))
        elif bank == "tool":
            io.setToolDigitalOutput(pin, bool(value))
        else:
            raise ValueError(f"unknown DO bank {bank!r}")

    def status_snapshot(self) -> dict:
        """Best-effort status read.

        The exact accessors are UNVERIFIED against SDK 0.26.0rc6 — every probe
        is try/except with safe defaults (mode="unknown", booleans False).
        Finalized by introspection during the hardware smoke test (plan Step
        8.5): try dir(getRobotState()) / dir(getRobotManage()) for
        getRobotModeType / getSafetyModeType / isPowerOn.
        """
        snap = {
            "mode": "unknown",
            "servo_on": False,
            "estop": False,
            "protective_stop": False,
            "speed_scale": 1.0,
            "error": None,
        }
        try:
            state = self.robot.getRobotState()
        except Exception:
            return snap
        try:
            snap["mode"] = str(state.getRobotModeType()).rsplit(".", 1)[-1]
        except Exception:
            pass
        try:
            safety = str(state.getSafetyModeType())
            snap["estop"] = "Emergency" in safety
            snap["protective_stop"] = "Protective" in safety or "Safeguard" in safety
        except Exception:
            pass
        try:
            snap["servo_on"] = bool(state.isPowerOn())
        except Exception:
            pass
        try:
            snap["speed_scale"] = float(
                self.robot.getMotionControl().getSpeedFraction()
            )
        except Exception:
            pass
        return snap

    def controller_time_ns(self) -> int:
        """Controller uptime in nanoseconds since boot."""
        return int(self.rpc.getSystemInfo().getControlSystemTime())

    # ── motion stop ──────────────────────────────────────────────────────

    # Max per-joint delta (rad) across a 50 ms poll that still counts as
    # standstill (≈ 2e-4 rad/s).
    _STILL_EPS_RAD = 1e-5

    def _stop_call(self, mc) -> None:
        """Fire the most effective stop this binding/controller offers.

        Probed live against controller SERVER 0.24 (scripts/probe_stop.py):
        the documented stops are accepted (rc=0) but IGNORED for path-buffer
        motion — `stopMove(quick, all_tasks)` is a resumable task-pause,
        and `pathBufferFree` / `RuntimeMachine.abort()` /
        `setSpeedFraction(0)` are all no-ops. The only call that physically
        halts the arm is `stopJoint(acc)` (~0.4 s to standstill), at the
        cost of tripping a ProtectiveStop — cleared in
        `_recover_after_stop`. `moveStop()` (the correct API on newer
        firmware) is preferred when the binding exposes it; the recovery
        step verifies the arm actually decays either way.
        """
        if hasattr(mc, "moveStop"):
            mc.moveStop()
            return
        if hasattr(mc, "stopJoint"):
            mc.stopJoint(3.0)
            return
        raise RuntimeError("MotionControl exposes no effective stop method")

    def _wait_standstill(self, timeout_s: float) -> bool:
        state = self.robot.getRobotState()
        last = list(state.getJointPositions())
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            time.sleep(0.05)
            cur = list(state.getJointPositions())
            if max(abs(a - b) for a, b in zip(cur, last)) < self._STILL_EPS_RAD:
                return True
            last = cur
        return False

    def _recover_after_stop(self, settle_timeout_s: float = 2.0) -> None:
        """Verify the arm actually reached standstill after a stop.

        Raises RuntimeError when the arm keeps moving — callers MUST surface
        that instead of reporting a clean cancel/stop. Does NOT clear the
        stop-induced ProtectiveStop: re-arming is an explicit operator
        action (`clear_protective_stop`), except the cancel path which
        auto-clears for ergonomic back-to-back goals.
        """
        if not self._wait_standstill(settle_timeout_s):
            raise RuntimeError(
                f"stop ineffective: arm still moving {settle_timeout_s:.1f}s after stop"
            )

    def clear_protective_stop(self, timeout_s: float = 3.0) -> None:
        """Unlock a protective stop (stop-induced or external/manual).

        No-op when the robot is not in protective stop. Raises when the
        unlock does not take effect within `timeout_s` (e.g. the physical
        cause is still present).
        """
        state = self.robot.getRobotState()
        if "Protective" not in str(state.getSafetyModeType()):
            return
        self.robot.getRobotManage().setUnlockProtectiveStop()
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if "Protective" not in str(state.getSafetyModeType()):
                return
            time.sleep(0.1)
        raise RuntimeError(
            f"protective stop still active {timeout_s:.1f}s after unlock"
        )

    def stop(self) -> None:
        """Abort the current motion: physical stop + standstill verification.
        Leaves the stop-induced ProtectiveStop in place — clearing it is an
        explicit operator action. Raises if the arm does not stop."""
        self._stop_call(self.robot.getMotionControl())
        self._recover_after_stop()

    def _wait_arrival(self) -> int:
        """Two-stage getExecId poll (intentional — reference wait_arrival)."""
        mc = self.robot.getMotionControl()
        cnt = 0
        while mc.getExecId() == -1:
            cnt += 1
            if cnt > 100:
                return -1
            time.sleep(0.05)
        while mc.getExecId() != -1:
            time.sleep(0.05)
        return 0

    def move_joint(self, q: list[float], speed_frac: float = 0.5) -> int:
        """Blocking moveJoint to `q`; returns 0 on arrival, -1 on timeout."""
        mc = self.robot.getMotionControl()
        mc.setSpeedFraction(speed_frac)
        mc.moveJoint(q, 80 * math.pi / 180, 60 * math.pi / 180, 0.0, 0.0)
        return self._wait_arrival()

    def speed_joint(self, qd: list[float], acc: float) -> int:
        """Command a joint-space velocity (rad/s). Returns the SDK rc (0=ok).

        ``speedJoint``'s ``t`` arg is a blocking-return time, NOT a deadman —
        the arm HOLDS the commanded velocity until the next command. The
        250 ms jog watchdog therefore lives in the driver, which calls
        :meth:`halt_speed` on expiry. Requires robot mode=Running; under a
        protective/safety stop the controller returns AUBO_BAD_STATE (nonzero).
        """
        mc = self.robot.getMotionControl()
        return int(mc.speedJoint([float(v) for v in qd], float(acc), 0.0))

    def halt_speed(self, acc: float) -> int:
        """Decelerate a velocity move to standstill (zero-velocity speedJoint)."""
        return self.speed_joint([0.0] * 6, acc)

    def execute_path_buffer(
        self,
        traj: list[list[float]],
        vmax: list[float],
        amax: list[float],
        on_tick: Callable[[], bool] | None = None,
    ) -> None:
        """Upload `traj` to the controller path buffer and execute it.

        `on_tick` (if given) is called every 50 ms during the wait loop;
        returning False triggers the physical stop (`_stop_call`) — the loop
        keeps waiting for getExecId() == -1, then `_recover_after_stop`
        verifies standstill (raises if the arm did not actually stop). The
        stop-induced ProtectiveStop is NOT cleared here — the caller decides
        (cancel auto-clears; cmd_stop leaves it for the operator).
        """
        mc = self.robot.getMotionControl()
        dt = self.servo_cycle()

        try:
            mc.pathBufferFree(_PATH_BUFFER_NAME)
        except Exception:
            pass

        mc.pathBufferAlloc(_PATH_BUFFER_NAME, 2, len(traj))
        for i in range(0, len(traj), _APPEND_CHUNK):
            mc.pathBufferAppend(_PATH_BUFFER_NAME, traj[i : i + _APPEND_CHUNK])

        # pathBufferEval must finish before movePathBuffer (reference gotcha).
        mc.pathBufferEval(_PATH_BUFFER_NAME, amax, vmax, dt)
        while not mc.pathBufferValid(_PATH_BUFFER_NAME):
            time.sleep(0.01)

        mc.movePathBuffer(_PATH_BUFFER_NAME)

        stopped = False

        def tick() -> None:
            nonlocal stopped
            if on_tick is not None and not stopped and not on_tick():
                self._stop_call(mc)
                stopped = True

        # Two-stage getExecId poll, 50 ms ticks.
        cnt = 0
        while mc.getExecId() == -1:
            cnt += 1
            if cnt > 100:
                return  # never started within 5 s
            tick()
            time.sleep(0.05)
        stop_deadline = None
        while mc.getExecId() != -1:
            tick()
            if stopped and stop_deadline is None:
                stop_deadline = time.monotonic() + 10.0
            if stop_deadline is not None and time.monotonic() > stop_deadline:
                _log.warning("exec id still active 10s after stop; giving up wait")
                break
            time.sleep(0.05)

        if stopped:
            self._recover_after_stop()
