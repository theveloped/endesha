"""GenicamBackend: the GenICam/GenTL camera behind the shared Camera2dCore.

Holds the Harvester ``Camera`` hardware seam — a retry-tolerant connect loop
(a missing/powered-off camera must NOT kill the cell), SingleFrame ``grab``,
a Continuous streaming loop decimated to the requested rate, and node-map
``configure``. Frames are produced as raw Bayer, run through the shared
``process_frame``, and handed to ``core.publish_frame``.

Extracted verbatim (behaviour-preserving) from the former ``GenicamDriver``.
"""

from __future__ import annotations

import threading
import time

from wf.core.log import get_logger
from wf.hal.camera2d_core import Camera2dBackend, CapturedFrame, process_frame

from .camera import Camera

_log = get_logger("wf.hal.genicam.backend")

_CONNECT_RETRY_S = 5.0
_STREAM_JOIN_TIMEOUT_S = 3.0


class GenicamBackend(Camera2dBackend):
    def __init__(self, params: dict):
        self.params = params
        self.core = None
        self._cam_lock = threading.Lock()  # serializes camera access
        self._state_lock = threading.Lock()  # guards the mutable state below
        self._camera: Camera | None = None
        self._stream_params = None  # StreamParams | None (single streaming truth)
        self._stream_thread: threading.Thread | None = None
        self._stream_stop = threading.Event()
        self._stop_event = threading.Event()
        self._error: str | None = None
        self._last_exposure: float | None = None
        self._last_gain: float | None = None

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self, core) -> None:
        self.core = core
        threading.Thread(
            target=self._connect_loop, name="connect-loop", daemon=True
        ).start()
        _log.info("genicam backend up: cid=%s cti=%s", core.cid, self.params["cti_path"])

    def shutdown(self) -> None:
        self._stop_event.set()
        self.stop_stream()
        with self._state_lock:
            camera, self._camera = self._camera, None
        if camera is not None:
            with self._cam_lock:
                camera.close()

    # ── connection (retry loop; tolerates an absent camera) ──────────────

    def _connect_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._state_lock:
                connected = self._camera is not None
            if connected:
                self._stop_event.wait(1.0)
                continue
            serial = self.params.get("serial")
            try:
                camera = Camera(
                    self.params["cti_path"],
                    None if serial is None else str(serial),
                )
            except Exception as exc:
                with self._state_lock:
                    self._error = repr(exc)
                self._stop_event.wait(_CONNECT_RETRY_S)
                continue
            # One SingleFrame grab calibrates the hw-clock offset and primes
            # the exposure/gain readback.
            try:
                with self._cam_lock:
                    _raw, hw_ts = camera.grab_single()
                    exposure, gain = camera.read_exposure_gain()
                self.core.calibrate_timesync(hw_ts)
            except Exception as exc:
                _log.warning("timesync calibration grab failed: %r", exc)
                with self._cam_lock:
                    exposure, gain = camera.read_exposure_gain()
            self._last_exposure, self._last_gain = exposure, gain
            with self._state_lock:
                self._camera = camera
                self._error = None
            _log.info("camera connected (cid=%s)", self.core.cid)

    # ── core seam ────────────────────────────────────────────────────────

    def grab(self, spec) -> CapturedFrame:
        with self._state_lock:
            camera = self._camera
        if camera is None:
            raise RuntimeError("camera not connected")
        with self._cam_lock:
            raw, hw_ts = camera.grab_single()
            self._last_exposure, self._last_gain = camera.read_exposure_gain()
        data, w, h = process_frame(raw, spec)
        return CapturedFrame(
            data, w, h, spec.encoding, hw_ts,
            self._last_exposure or 0.0, self._last_gain or 0.0,
        )

    def start_stream(self, sp) -> None:
        with self._state_lock:
            camera = self._camera
        if camera is None:
            raise RuntimeError("camera not connected")
        # Already streaming -> stop first, restart with the new params.
        self.stop_stream()
        self._stream_stop.clear()
        with self._state_lock:
            self._stream_params = sp
        thread = threading.Thread(
            target=self._stream_loop, args=(camera, sp), name="stream-loop", daemon=True
        )
        self._stream_thread = thread
        thread.start()

    def stop_stream(self) -> None:
        self._stream_stop.set()
        thread = self._stream_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=_STREAM_JOIN_TIMEOUT_S)
        self._stream_thread = None
        with self._state_lock:
            self._stream_params = None

    def active_stream(self):
        with self._state_lock:
            return self._stream_params

    def _stream_loop(self, camera: Camera, sp) -> None:
        period = 1.0 / sp.rate_hz
        try:
            with self._cam_lock:
                camera.start_continuous()
            next_due = time.monotonic()
            while not (self._stream_stop.is_set() or self._stop_event.is_set()):
                with self._cam_lock:
                    result = camera.fetch_raw(timeout=1.0)
                if result is None:
                    continue
                now = time.monotonic()
                if now < next_due:
                    continue  # decimate to rate_hz: skip early frames
                next_due += period
                if next_due < now:  # fell behind (sensor slower than rate)
                    next_due = now + period
                raw, hw_ts = result
                data, w, h = process_frame(raw, sp)
                self.core.publish_frame(
                    CapturedFrame(
                        data, w, h, sp.encoding, hw_ts,
                        self._last_exposure or 0.0, self._last_gain or 0.0,
                    )
                )
        except Exception as exc:
            with self._state_lock:
                self._error = f"stream failed: {exc!r}"
            _log.error("stream loop failed", exc_info=True)
        finally:
            try:
                with self._cam_lock:
                    camera.stop_acquisition()
            except Exception:
                pass
            with self._state_lock:
                if self._stream_params is sp:
                    self._stream_params = None

    def configure(self, cmd) -> None:
        with self._state_lock:
            camera = self._camera
        if camera is None:
            raise RuntimeError("camera not connected")
        with self._cam_lock:
            camera.apply_configure(cmd)
            self._last_exposure, self._last_gain = camera.read_exposure_gain()

    def status(self) -> dict:
        with self._state_lock:
            camera = self._camera
            error = self._error
        # Refresh exposure/gain opportunistically: skip on lock contention
        # (mid-grab or mid-fetch) rather than block.
        if camera is not None and self._cam_lock.acquire(blocking=False):
            try:
                self._last_exposure, self._last_gain = camera.read_exposure_gain()
            except Exception:
                pass
            finally:
                self._cam_lock.release()
        return {
            "connected": camera is not None,
            "exposure_us": self._last_exposure if camera is not None else None,
            "gain_db": self._last_gain if camera is not None else None,
            "error": error,
        }
