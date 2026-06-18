"""SimArmBackend: the in-process simulated arm behind the shared ``ArmCore``.

A single 200 Hz tick loop drives :class:`SimArm` and publishes state through the
core; jog is integrated per tick (with joint-limit clamp) and a path is played
back sample-by-sample. Optional mirror mode shadows another namespace's
``arm/{rid}/state/joints`` (and rejects motion while mirroring).
"""

from __future__ import annotations

import bisect
import threading
import time

from wf.contracts.arm import keys
from wf.contracts.arm.messages import JointState
from wf.core.codec import decode
from wf.core.log import get_logger
from wf.core.time import CLOCK_HOST, now_ns
from wf.hal.arm_core import ArmBackend

from .sim import SimArm

_log = get_logger("wf.hal.arm_sim.backend")

_IO_EVERY_N_TICKS = 20  # 200 Hz ticks -> 10 Hz io
_STATUS_EVERY_N_TICKS = 200  # -> 1 Hz status
_FEEDBACK_EVERY_N_SAMPLES = 40  # 5 ms samples -> ~5 Hz feedback


class SimArmBackend(ArmBackend):
    def __init__(self, home_q: list[float], mirror_realm: str | None = None):
        self.home_q = list(home_q)
        self.mirror_realm = mirror_realm
        self.lock = threading.Lock()  # guards SimArm
        self.sim: SimArm | None = None
        self.core = None
        self._stop_event = threading.Event()
        self._mirror_sub = None

    # ── lifecycle ─────────────────────────────────────────────────────────

    def start(self, core) -> None:
        self.core = core
        self.sim = SimArm(core.fk, self.home_q)
        if self.mirror_realm:
            self._mirror_sub = core.session.declare_subscriber(
                keys.state_joints(self.mirror_realm, core.rid), self._on_mirror_sample
            )
        threading.Thread(target=self._tick_loop, name="sim-tick", daemon=True).start()
        _log.info(
            "arm_sim backend up: rid=%s mirror=%s",
            core.rid,
            self.mirror_realm or "<off>",
        )

    def shutdown(self) -> None:
        self._stop_event.set()
        if self._mirror_sub is not None:
            try:
                self._mirror_sub.undeclare()
            except Exception:
                pass

    # ── core seam ─────────────────────────────────────────────────────────

    def latest_q(self) -> list[float] | None:
        with self.lock:
            return list(self.sim.q)

    def motion_block_reason(self, *, for_goal: bool) -> str | None:
        return "mirroring" if self.mirror_realm else None

    def apply_jog_velocity(self, qd: list[float]) -> None:
        core = self.core
        dt = core.servo_dt
        with self.lock:
            q = list(self.sim.q)
            new_q = [
                min(max(q[j] + qd[j] * dt, core.jmin[j]), core.jmax[j])
                for j in range(6)
            ]
            self.sim.set_q(new_q, qd)

    def halt_jog(self) -> None:
        with self.lock:
            self.sim.set_q(self.sim.q, [0.0] * 6)

    def set_do(self, bank: str, pin: int, value: int) -> None:
        with self.lock:
            self.sim.set_do(bank, pin, value)

    # ── mirror subscriber (zenoh thread) ─────────────────────────────────

    def _on_mirror_sample(self, sample) -> None:
        try:
            msg = JointState.from_wire(decode(sample.payload))
        except Exception as exc:
            _log.warning("mirror sample decode failed: %r", exc)
            return
        with self.lock:
            self.sim.set_q(msg.q, msg.qd)

    # ── tick loop (the only state thread; 200 Hz) ────────────────────────

    def _tick_loop(self) -> None:
        core = self.core
        dt = core.servo_dt
        tick = 0
        next_t = time.monotonic()
        while not self._stop_event.is_set():
            next_t += dt
            now = time.monotonic()
            if next_t > now:
                time.sleep(next_t - now)
            elif next_t < now - 0.5:
                next_t = now  # fell badly behind; resync instead of bursting

            qd_jog = core.jog_step()
            if qd_jog is not None:
                if any(qd_jog):
                    self.apply_jog_velocity(qd_jog)
                else:
                    self.halt_jog()

            with self.lock:
                q = list(self.sim.q)
                qd = list(self.sim.qd)
                di = self.sim.di_bits
                do = self.sim.do_bits

            core.publish_motion(q, qd, [0.0] * 6, now_ns(), CLOCK_HOST)

            tick += 1
            if tick % _IO_EVERY_N_TICKS == 0:
                core.publish_io(di, do, [0.0, 0.0], [0.0, 0.0])
            if tick % _STATUS_EVERY_N_TICKS == 0:
                mode = (
                    f"Mirroring({self.mirror_realm})"
                    if self.mirror_realm
                    else "Simulated"
                )
                core.publish_status(
                    mode=mode,
                    servo_on=True,
                    estop=False,
                    protective_stop=False,
                    speed_scale=1.0,
                    error=None,
                )
                core.publish_owner()

    # ── path execution ───────────────────────────────────────────────────

    def run_path(self, handle, traj, wp_idx, targets, snapshot) -> None:
        # Playback: the sim IS the trajectory — drive SimArm sample by sample.
        core = self.core
        dt = core.servo_dt
        with self.lock:
            prev = list(self.sim.q)
        next_t = time.monotonic()
        for i, q in enumerate(traj):
            next_t += dt
            delay = next_t - time.monotonic()
            if delay > 0:
                time.sleep(delay)

            if handle.cancel_requested or core.stop_requested():
                with self.lock:
                    self.sim.set_q(self.sim.q, [0.0] * 6)  # freeze at current sample
                if handle.cancel_requested:
                    handle.set_canceled()
                else:
                    core.clear_stop()
                    handle.abort(cause="cmd_stop")
                return

            qd = [(q[j] - prev[j]) / dt for j in range(6)]
            with self.lock:
                self.sim.set_q(q, qd)
            prev = q

            if (i + 1) % _FEEDBACK_EVERY_N_SAMPLES == 0:
                current_wp = min(bisect.bisect_left(wp_idx, i + 1), len(targets) - 1)
                handle.feedback((i + 1) / len(traj), current_wp=current_wp)

        with self.lock:
            self.sim.set_q(traj[-1], [0.0] * 6)
        # No final joints_close check needed — the sim is the trajectory.
        handle.succeed(snapshot=snapshot)
