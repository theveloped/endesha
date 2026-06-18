"""The `genicam_driver` process (design §5.5, camera2d contract).

Deliberate divergence from the aubo driver's crash-only startup: a missing
or powered-off camera must NOT kill the cell stack, so connection runs in a
retry loop (`_connect_loop`, 5 s backoff) and failures surface in
``CameraStatus.error`` instead of a process exit.

No default continuous stream: the camera idles; full-res frames are fetched
via ``cmd/grab`` (SingleFrame trigger) and a parameterized stream is
switched on/off via ``cmd/stream_start``/``cmd/stream_stop`` (Continuous
mode). Grab is REJECTED while streaming. Every frame — stream or grab —
goes out on the one ``image`` topic: payload = image bytes, attachment =
CBOR FrameHeader, with one shared per-process ``seq`` counter.
"""

from __future__ import annotations

import argparse
import os
import threading
import time

import zenoh

from wf.contracts.arm import keys as arm_keys
from wf.contracts.arm.messages import FlangeState
from wf.contracts.camera2d import keys
from wf.contracts.camera2d.messages import (
    Ack,
    CameraStatus,
    ConfigureCmd,
    FrameHeader,
    FrameSpec,
    GrabReply,
    StreamParams,
)
from wf.core.codec import decode, encode
from wf.core.frames import (
    make_transform,
    quaternion_to_rotation_matrix,
    rpy_deg_to_matrix,
    transform_to_xyz_quat,
)
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import now_ns

from .camera import Camera
from .config import load_resource
from .processing import process_frame, t_capture_ns
from .timesync import CameraTimeSync

_log = get_logger("wf.hal.genicam.driver")

_CONNECT_RETRY_S = 5.0
_STREAM_JOIN_TIMEOUT_S = 3.0


class GenicamDriver:
    def __init__(self, session, realm: str, cid: str, params: dict):
        self.session = session
        self.realm = realm
        self.cid = cid
        self.params = params
        self.frame_id = keys.optical_frame(cid)

        self._stop_event = threading.Event()  # process shutdown
        self._cam_lock = threading.Lock()  # serializes camera access
        self._state_lock = threading.Lock()  # guards the mutable state below
        self._camera: Camera | None = None
        self._stream_params: StreamParams | None = None
        self._stream_thread: threading.Thread | None = None
        self._stream_stop = threading.Event()
        self._seq = 0
        self._published_count = 0
        self._last_t_capture = 0
        self._error: str | None = None

        self._timesync = CameraTimeSync()
        self._last_exposure: float | None = None
        self._last_gain: float | None = None

        # Eye-in-hand pose: the rigid flange->optical mount (OpenCV optical,
        # +Z forward) and the latest flange sample from the mount arm. The
        # per-frame world<-optical pose stamped into the FrameHeader is
        # T_world_flange @ T_flange_optical; None until a flange sample arrives
        # (e.g. the arm driver is down) so the UI frustum simply hides.
        self.mount_arm = str(params["mount_arm"])
        self._T_flange_optical = make_transform(
            rpy_deg_to_matrix(params["mount_rpy_deg"]), params["mount_xyz"]
        )
        self._flange_xyz: list[float] | None = None
        self._flange_quat: list[float] | None = None
        self._flange_sub = None

        # Best-effort stream (design §3): drop under congestion.
        self._pub_image = session.declare_publisher(
            keys.image(realm, cid),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._pub_status = session.declare_publisher(keys.state_status(realm, cid))
        self._queryables: list = []

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._queryables = [
            self.session.declare_queryable(
                keys.cmd_grab(self.realm, self.cid), self._on_grab
            ),
            self.session.declare_queryable(
                keys.cmd_configure(self.realm, self.cid), self._on_configure
            ),
            self.session.declare_queryable(
                keys.cmd_stream_start(self.realm, self.cid), self._on_stream_start
            ),
            self.session.declare_queryable(
                keys.cmd_stream_stop(self.realm, self.cid), self._on_stream_stop
            ),
        ]
        # Eye-in-hand: track the mount arm's flange to stamp the per-frame pose.
        self._flange_sub = self.session.declare_subscriber(
            arm_keys.state_flange(self.realm, self.mount_arm), self._on_flange
        )
        threading.Thread(
            target=self._connect_loop, name="connect-loop", daemon=True
        ).start()
        threading.Thread(
            target=self._status_loop, name="status-loop", daemon=True
        ).start()
        _log.info(
            "genicam_driver up: realm=%s cid=%s cti=%s",
            self.realm,
            self.cid,
            self.params["cti_path"],
        )

    def run_forever(self) -> None:
        try:
            while not self._stop_event.wait(1.0):
                pass
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._stop_event.set()
        self._stop_stream()
        if self._flange_sub is not None:
            try:
                self._flange_sub.undeclare()
            except Exception:
                pass
        with self._state_lock:
            camera, self._camera = self._camera, None
        if camera is not None:
            with self._cam_lock:
                camera.close()
        _log.info("genicam_driver stopped")

    # ── eye-in-hand pose ─────────────────────────────────────────────────

    def _on_flange(self, sample) -> None:
        try:
            fs = FlangeState.from_wire(decode(sample.payload))
        except Exception:
            _log.warning("flange decode failed", exc_info=True)
            return
        with self._state_lock:
            self._flange_xyz = list(fs.pose.xyz)
            self._flange_quat = list(fs.pose.quat)

    def _camera_pose(self) -> dict | None:
        """World<-optical pose dict from the latest flange, or None if unknown.

        ``T_world_optical = T_world_flange @ T_flange_optical``. The flange pose
        is taken in the arm base frame (== world in v0), so the stamped pose's
        ``frame`` is ``world``.
        """
        with self._state_lock:
            xyz, quat = self._flange_xyz, self._flange_quat
        if xyz is None or quat is None:
            return None
        t_world_flange = make_transform(quaternion_to_rotation_matrix(quat), xyz)
        pos, rot = transform_to_xyz_quat(t_world_flange @ self._T_flange_optical)
        return {"frame": "world", "xyz": pos, "quat": rot}

    # ── connection (retry loop; tolerates an absent camera) ─────────────

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
                self._timesync.calibrate(hw_ts)
            except Exception as exc:
                _log.warning("timesync calibration grab failed: %r", exc)
                with self._cam_lock:
                    exposure, gain = camera.read_exposure_gain()
            self._last_exposure, self._last_gain = exposure, gain
            with self._state_lock:
                self._camera = camera
                self._error = None
            _log.info("camera connected (cid=%s)", self.cid)

    # ── frame publishing (the ONE path for stream and grab frames) ──────

    def _publish_frame(
        self, data: bytes, w: int, h: int, encoding: str, hw_ts_ns: int
    ) -> FrameHeader:
        exposure = self._last_exposure if self._last_exposure is not None else 0.0
        gain = self._last_gain if self._last_gain is not None else 0.0
        if self._timesync.calibrated:
            t_capture = t_capture_ns(hw_ts_ns, self._timesync.offset_ns, exposure)
        else:
            t_capture = now_ns() - int(exposure * 500)
        with self._state_lock:
            # Contract: t_capture/seq strictly increasing per producer.
            if t_capture <= self._last_t_capture:
                t_capture = self._last_t_capture + 1
            self._last_t_capture = t_capture
            seq = self._seq
            self._seq += 1
            self._published_count += 1
        header = FrameHeader(
            t_capture=t_capture,
            frame_id=self.frame_id,
            w=w,
            h=h,
            encoding=encoding,
            exposure_us=exposure,
            gain_db=gain,
            seq=seq,
            clock_domain=self._timesync.clock_domain,
            pose=self._camera_pose(),
        )
        self._pub_image.put(data, attachment=encode(header.to_wire()))
        return header

    # ── streaming ────────────────────────────────────────────────────────

    def _on_stream_start(self, query) -> None:
        key = str(query.key_expr)
        try:
            payload = decode(query.payload) if query.payload is not None else {}
            sp = StreamParams.from_wire({**self.params["stream_defaults"], **payload})
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=str(exc)).to_wire()))
            return
        with self._state_lock:
            camera = self._camera
        if camera is None:
            query.reply(
                key, encode(Ack(ok=False, error="camera not connected").to_wire())
            )
            return
        # Already streaming -> stop first, restart with the new params.
        self._stop_stream()
        self._stream_stop.clear()
        with self._state_lock:
            self._stream_params = sp
        thread = threading.Thread(
            target=self._stream_loop, args=(camera, sp), name="stream-loop", daemon=True
        )
        self._stream_thread = thread
        thread.start()
        query.reply(key, encode(Ack(ok=True).to_wire()))

    def _on_stream_stop(self, query) -> None:
        key = str(query.key_expr)
        try:
            self._stop_stream()  # idempotent — ok even when idle
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    def _stop_stream(self) -> None:
        self._stream_stop.set()
        thread = self._stream_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=_STREAM_JOIN_TIMEOUT_S)
        self._stream_thread = None
        with self._state_lock:
            self._stream_params = None

    def _stream_loop(self, camera: Camera, sp: StreamParams) -> None:
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
                self._publish_frame(data, w, h, sp.encoding, hw_ts)
        except Exception as exc:
            # Mirror the replayer's playback-loop hardening: surface the
            # error, never leave a zombie `streaming: true`.
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

    # ── grab ─────────────────────────────────────────────────────────────

    def _on_grab(self, query) -> None:
        key = str(query.key_expr)

        def fail(error: str) -> None:
            query.reply(key, encode(GrabReply(ok=False, error=error).to_wire()))

        with self._state_lock:
            streaming = self._stream_params is not None
            camera = self._camera
        if streaming:
            fail("camera is streaming - stop the stream first")
            return
        if camera is None:
            fail("camera not connected")
            return
        try:
            payload = decode(query.payload) if query.payload is not None else {}
            spec = FrameSpec.from_wire({**self.params["grab_defaults"], **payload})
        except Exception as exc:
            fail(str(exc))
            return
        try:
            with self._cam_lock:
                raw, hw_ts = camera.grab_single()
                self._last_exposure, self._last_gain = camera.read_exposure_gain()
            data, w, h = process_frame(raw, spec)
            # Publish on the image topic exactly like a stream frame (grabs
            # are recorded and pipeline-consumable — design §5.5), then
            # duplicate into the synchronous reply.
            header = self._publish_frame(data, w, h, spec.encoding, hw_ts)
            query.reply(
                key, encode(GrabReply(ok=True, header=header, data=data).to_wire())
            )
        except Exception as exc:
            fail(repr(exc))

    # ── configure ────────────────────────────────────────────────────────

    def _on_configure(self, query) -> None:
        key = str(query.key_expr)
        try:
            cmd = ConfigureCmd.from_wire(
                decode(query.payload) if query.payload is not None else {}
            )
            with self._state_lock:
                camera = self._camera
            if camera is None:
                raise RuntimeError("camera not connected")
            with self._cam_lock:
                camera.apply_configure(cmd)
                self._last_exposure, self._last_gain = camera.read_exposure_gain()
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    # ── status (1 Hz) ────────────────────────────────────────────────────

    def _status_loop(self) -> None:
        last_count = 0
        last_t = time.monotonic()
        while not self._stop_event.wait(1.0):
            with self._state_lock:
                camera = self._camera
                sp = self._stream_params
                error = self._error
                count = self._published_count
            # Refresh exposure/gain opportunistically: skip on lock
            # contention (mid-grab or mid-fetch) rather than block.
            if camera is not None and self._cam_lock.acquire(blocking=False):
                try:
                    self._last_exposure, self._last_gain = (
                        camera.read_exposure_gain()
                    )
                except Exception:
                    pass
                finally:
                    self._cam_lock.release()
            now = time.monotonic()
            elapsed = now - last_t
            rate = (count - last_count) / elapsed if elapsed > 0 else 0.0
            last_count, last_t = count, now
            status = CameraStatus(
                t=now_ns(),
                connected=camera is not None,
                streaming=sp is not None,
                stream=sp,
                exposure_us=self._last_exposure if camera is not None else None,
                gain_db=self._last_gain if camera is not None else None,
                achieved_rate_hz=rate,
                error=error,
            )
            try:
                self._pub_status.put(encode(status.to_wire()))
            except Exception:
                _log.warning("status publish failed", exc_info=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="genicam_driver", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument("--resource", default="cam0", help="resource id (default cam0)")
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    params = load_resource(args.cell, args.resource)
    session = open_session(args.zenoh_config)
    token = declare_alive(session, args.realm, "camera2d", args.resource)

    driver = GenicamDriver(session, args.realm, args.resource, params)
    try:
        driver.start()
        driver.run_forever()
    finally:
        del token
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
