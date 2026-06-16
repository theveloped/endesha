"""Robot-controller clock <-> host wall clock (robot half of the reference
TimeSynchronizer, converted to int nanoseconds).

The camera half stays in the reference until `hal/genicam` (week 5).
"""

from __future__ import annotations

import math
import time

from wf.core.log import get_logger
from wf.core.time import now_ns

_log = get_logger("wf.hal.aubo_i10.timesync")


class RobotTimeSync:
    """One-shot calibration relating controller uptime to host wall clock."""

    def __init__(self):
        self._epoch_ns: int | None = None  # host wall clock at controller boot

    @property
    def calibrated(self) -> bool:
        return self._epoch_ns is not None

    def calibrate_robot(self, controller_uptime_ns: int) -> None:
        """Pair getControlSystemTime() (ns since controller boot) with host
        wall clock to compute the controller's boot instant."""
        self._epoch_ns = time.time_ns() - int(controller_uptime_ns)
        _log.info(
            "robot epoch: controller uptime=%.3fs, epoch_ns=%d",
            controller_uptime_ns / 1e9,
            self._epoch_ns,
        )

    def robot_time_ns(self, controller_ts_s: float) -> int:
        """RTDE controller timestamp (seconds since boot) -> host-aligned ns.

        Falls back to now_ns() when uncalibrated or when the controller sends
        a non-finite timestamp (observed: this controller build streams
        ``timestamp: null`` over RTDE, which the SDK pops as NaN).
        """
        if self._epoch_ns is None or not math.isfinite(controller_ts_s):
            return now_ns()
        return self._epoch_ns + int(controller_ts_s * 1e9)
