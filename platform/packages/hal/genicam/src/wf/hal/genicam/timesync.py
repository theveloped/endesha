"""Camera hardware clock <-> host wall clock (camera half of the reference
TimeSynchronizer; mirrors ``hal/aubo_i10/timesync.py:RobotTimeSync``)."""

from __future__ import annotations

from wf.core.log import get_logger
from wf.core.time import CLOCK_CAMERA, CLOCK_HOST, now_ns

_log = get_logger("wf.hal.genicam.timesync")


class CameraTimeSync:
    """One-shot calibration relating camera hardware timestamps to host
    wall clock."""

    def __init__(self):
        self._offset_ns: int | None = None  # host_ns - camera_hw_ns

    @property
    def calibrated(self) -> bool:
        return self._offset_ns is not None

    @property
    def offset_ns(self) -> int:
        """``host_epoch - camera_hw`` offset; 0 when uncalibrated (frames
        then carry the raw hardware stamp — callers must check
        ``calibrated``/``clock_domain``)."""
        return 0 if self._offset_ns is None else self._offset_ns

    @property
    def clock_domain(self) -> str:
        return CLOCK_CAMERA if self.calibrated else CLOCK_HOST

    def calibrate(self, first_hw_ts_ns: int) -> None:
        """Pair a camera hardware timestamp with host wall clock NOW."""
        self._offset_ns = now_ns() - int(first_hw_ts_ns)
        _log.info(
            "camera epoch: hw_ts=%.3fs, offset_ns=%d",
            first_hw_ts_ns / 1e9,
            self._offset_ns,
        )
