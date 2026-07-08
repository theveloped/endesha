"""WF platform L2 `camera2d_core`: the shared camera2d-contract core + backend
seam + frame-processing utilities.

``Camera2dCore`` serves the whole ``camera2d`` contract against a pluggable
:class:`Camera2dBackend` (GenicamBackend / a future ReplayCameraBackend; the
headless-browser TS service is a separate, parallel provider of the same
contract).
"""

from .backend import Camera2dBackend, CapturedFrame
from .core import Camera2dCore
from .processing import (
    _bgr_to_bayer_rg8,
    process_bgr_frame,
    process_frame,
    t_capture_ns,
)
from .timesync import CameraTimeSync

__all__ = [
    "Camera2dBackend",
    "Camera2dCore",
    "CapturedFrame",
    "CameraTimeSync",
    "process_frame",
    "process_bgr_frame",
    "_bgr_to_bayer_rg8",
    "t_capture_ns",
]
