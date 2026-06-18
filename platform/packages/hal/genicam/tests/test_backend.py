"""GenicamBackend imports + constructs + exposes the Camera2dBackend seam
without touching hardware (no Harvester/GenTL connection)."""

from __future__ import annotations

import wf.hal.genicam.__main__  # noqa: F401  (thin entrypoint imports cleanly)
from wf.hal.camera2d_core import Camera2dBackend
from wf.hal.genicam.backend import GenicamBackend

_PARAMS = {
    "cti_path": "x",
    "serial": None,
    "mount_arm": "r1",
    "mount_xyz": [0.0, 0.0, 0.05],
    "mount_rpy_deg": [0.0, 0.0, 0.0],
    "stream_defaults": {"rate_hz": 15.0, "scale": 0.25, "encoding": "jpeg", "quality": 75},
    "grab_defaults": {"scale": 1.0, "encoding": "BayerRG8", "quality": 95},
}


def test_backend_constructs_without_hardware():
    b = GenicamBackend(_PARAMS)
    assert isinstance(b, Camera2dBackend)
    # No connection yet: not streaming, status reports disconnected.
    assert b.active_stream() is None
    st = b.status()
    assert st == {
        "connected": False,
        "exposure_us": None,
        "gain_db": None,
        "error": None,
    }
    for m in ("start", "shutdown", "grab", "start_stream", "stop_stream",
              "active_stream", "configure", "status"):
        assert callable(getattr(b, m)), m
