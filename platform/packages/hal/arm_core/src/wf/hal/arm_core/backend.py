"""The ``ArmBackend`` seam (RFC step 4).

:class:`~wf.hal.arm_core.core.ArmCore` serves the whole arm contract (lease,
hold-to-jog gating, TCP selection, goal resolution + collision preflight,
ruckig trajectory generation, state/status publishing, twin construction). The
~30% that differs between a simulator and real hardware lives behind this
interface: how robot state is produced, how a path is executed, how a jog
velocity is applied, DO/stop, and any backend-specific motion gate.

Call directions:
- the backend owns its state thread(s) and calls ``core.publish_*`` to emit
  contract state (so each backend keeps its native acquisition model);
- the core calls the methods below to command the backend and to read the
  pieces it needs (``latest_q``, the jog/goal gate).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ArmBackend(ABC):
    """The hardware/sim-specific half of an arm driver."""

    @abstractmethod
    def start(self, core) -> None:
        """Connect + start the backend's own state thread(s).

        Receives the :class:`ArmCore` so the backend can call publish helpers
        and read gating state. A hardware backend may also override the core's
        ``jmin``/``jmax``/``servo_dt`` here from the controller's own config.
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Stop threads and release backend resources."""

    @abstractmethod
    def latest_q(self) -> list[float] | None:
        """Current joint positions (goal-accept start pose + jog), or None if
        no joint state has been observed yet."""

    def motion_block_reason(self, *, for_goal: bool) -> str | None:
        """Reason motion is currently disallowed, or None.

        Consulted at jog-arm time (``for_goal=False``) and goal-accept time
        (``for_goal=True``). Default: never blocks. The sim blocks while
        mirroring; hardware blocks goals under estop/protective-stop.
        """
        return None

    def on_jog_armed(self) -> None:
        """Called by the core after a jog command is armed. Default no-op (the
        sim polls ``core.jog_step`` every tick); a hardware backend wakes its
        dedicated jog-runner thread here. Applying the jog velocity returned by
        ``core.jog_step`` is the backend's own concern."""

    @abstractmethod
    def run_path(self, handle, trajectory, wp_idx, targets, snapshot) -> None:
        """Drive the arm through a core-generated, validated ``trajectory`` and
        terminate ``handle`` (succeed / set_canceled / abort / fail).

        ``wp_idx`` maps trajectory sample index -> waypoint boundary (for
        feedback), ``targets`` is the list of waypoint joint goals, ``snapshot``
        is the acceptance-time provenance to attach to a successful result. The
        loop must honour ``handle.cancel_requested`` and ``core.stop_requested()``.
        """

    @abstractmethod
    def set_do(self, bank: str, pin: int, value: int) -> None:
        """Set a digital output bit."""

    def stop(self) -> None:
        """Out-of-band halt (cmd/stop). Default no-op (the sim freezes via the
        jog/path stop flags); hardware issues an SDK stop / halt_speed."""

    def clear_protective_stop(self) -> None:
        """Clear a protective stop. Default no-op (no fault state in sim)."""
