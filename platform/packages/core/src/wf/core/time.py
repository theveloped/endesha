"""Time helpers and clock-domain constants (design §6)."""

from __future__ import annotations

import time

CLOCK_HOST = "host"
CLOCK_ROBOT = "robot_controller"
CLOCK_CAMERA = "camera_hw"
CLOCK_REPLAY = "replay"


def now_ns() -> int:
    """Current host wall-clock time in integer nanoseconds."""
    return time.time_ns()
