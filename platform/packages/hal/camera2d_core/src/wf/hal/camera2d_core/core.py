"""Shared camera2d contract core (RFC step 5).

``Camera2dCore`` serves the entire ``camera2d`` contract for one logical device
against a pluggable :class:`~wf.hal.camera2d_core.backend.Camera2dBackend`. It
owns the zenoh endpoints (image + status publishers, the four cmd queryables,
the arm-flange subscriber), the eye-in-hand pose, the single image-publish path
(FrameHeader with monotonic seq/t_capture + stamped pose), the 1 Hz status
loop, and the grab-while-streaming rejection. The backend produces frames; the
core stamps + emits identically for any source.

Extracted verbatim (behaviour-preserving) from the former ``GenicamDriver`` so
genicam and a future replay-camera stop duplicating contract logic. The wire
shapes must stay byte-identical to the TS headless-browser provider.
"""

from __future__ import annotations

import threading
import time

import zenoh

from wf.contracts.arm import keys as arm_keys
from wf.contracts.arm.messages import FlangeState
from wf.contracts.camera2d import keys
from wf.contracts.camera2d.messages import (
    CameraStatus,
    ConfigureCmd,
    FrameHeader,
    FrameSpec,
    GrabReply,
    StreamParams,
)
from wf.core.codec import decode, encode
from wf.core.envelope import RecentReplies, Request, fail, ok_value, serve_query
from wf.core.frames import (
    make_transform,
    quaternion_to_rotation_matrix,
    rpy_deg_to_matrix,
    transform_to_xyz_quat,
)
from wf.core.log import get_logger
from wf.core.time import now_ns

from .backend import Camera2dBackend, CapturedFrame
from .processing import t_capture_ns
from .timesync import CameraTimeSync

_log = get_logger("wf.hal.camera2d_core")


class Camera2dCore:
    def __init__(
        self, session, realm: str, cid: str, params: dict, backend: Camera2dBackend
    ):
        self.session = session
        self.realm = realm
        self.cid = cid
        self.params = params
        self.backend = backend
        self.frame_id = keys.optical_frame(cid)

        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()  # guards seq/t_capture/pose cache
        self._seq = 0
        self._published_count = 0
        self._last_t_capture = 0

        self._timesync = CameraTimeSync()

        # Eye-in-hand pose: the rigid flange->optical mount (OpenCV optical,
        # +Z forward) and the latest flange sample from the mount arm. The
        # per-frame world<-optical pose is T_world_flange @ T_flange_optical;
        # None until a flange sample arrives (the UI frustum then hides).
        self.mount_arm = str(params["mount_arm"])
        self._T_flange_optical = make_transform(
            rpy_deg_to_matrix(params["mount_rpy_deg"]), params["mount_xyz"]
        )
        self._flange_xyz: list[float] | None = None
        self._flange_quat: list[float] | None = None
        self._flange_sub = None

        # Best-effort stream (design §3): drop under congestion.
        self._pub_image = session.declare_publisher(
            keys.image(realm, cid), congestion_control=zenoh.CongestionControl.DROP
        )
        self._pub_status = session.declare_publisher(keys.state_status(realm, cid))
        self._queryables: list = []

    # ── lifecycle ────────────────────────────────────────────────────────
        self._recent = RecentReplies()

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
        self.backend.start(self)
        threading.Thread(
            target=self._status_loop, name="status-loop", daemon=True
        ).start()
        _log.info("camera2d core up: realm=%s cid=%s", self.realm, self.cid)

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
        try:
            self.backend.shutdown()
        except Exception:
            _log.exception("backend shutdown failed")
        for q in self._queryables:
            try:
                q.undeclare()
            except Exception:
                pass
        if self._flange_sub is not None:
            try:
                self._flange_sub.undeclare()
            except Exception:
                pass
        _log.info("camera2d core stopped")

    # ── timesync (calibrated by the backend at connect) ──────────────────

    def calibrate_timesync(self, hw_ts_ns: int) -> None:
        self._timesync.calibrate(hw_ts_ns)

    # ── eye-in-hand pose ──────────────────────────────────────────────────

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

    # ── frame publishing (the ONE path for stream and grab frames) ──────

    def publish_frame(self, f: CapturedFrame) -> FrameHeader:
        if self._timesync.calibrated:
            t_capture = t_capture_ns(f.hw_ts_ns, self._timesync.offset_ns, f.exposure_us)
        else:
            t_capture = now_ns() - int(f.exposure_us * 500)
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
            w=f.w,
            h=f.h,
            encoding=f.encoding,
            exposure_us=f.exposure_us,
            gain_db=f.gain_db,
            seq=seq,
            clock_domain=self._timesync.clock_domain,
            # A replay source supplies the recorded pose; live sources leave it
            # None so the core stamps the current eye-in-hand pose.
            pose=f.pose if f.pose is not None else self._camera_pose(),
        )
        self._pub_image.put(f.data, attachment=encode(header.to_wire()))
        return header

    # ── grab ─────────────────────────────────────────────────────────────

    def _on_grab(self, query) -> None:
        serve_query(query, self._do_grab, recent=self._recent)

    def _do_grab(self, req: Request) -> dict:
        if self.backend.active_stream() is not None:
            return fail("conflict", "streaming", "stop the stream first")
        try:
            spec = FrameSpec.from_wire({**self.params["grab_defaults"], **req.args})
        except Exception as exc:  # noqa: BLE001
            return fail("invalid", "bad_request", str(exc))
        try:
            captured = self.backend.grab(spec)
        except Exception as exc:  # noqa: BLE001
            return fail("internal", "grab_failed", repr(exc))
        # Publish on the image topic exactly like a stream frame (grabs are
        # recorded + pipeline-consumable — design §5.5), then duplicate into
        # the synchronous reply.
        header = self.publish_frame(captured)
        return ok_value(GrabReply(header=header, data=captured.data).to_wire())

    # ── streaming ─────────────────────────────────────────────────────────

    def _on_stream_start(self, query) -> None:
        serve_query(query, self._do_stream_start, recent=self._recent)

    def _do_stream_start(self, req: Request) -> dict:
        try:
            sp = StreamParams.from_wire({**self.params["stream_defaults"], **req.args})
        except Exception as exc:  # noqa: BLE001
            return fail("invalid", "bad_request", str(exc))
        try:
            self.backend.start_stream(sp)
        except ValueError as exc:
            return fail("invalid", "unsupported_encoding", str(exc))
        except Exception as exc:  # noqa: BLE001
            return fail("internal", "stream_failed", repr(exc))
        return ok_value()

    def _on_stream_stop(self, query) -> None:
        serve_query(query, self._do_stream_stop, recent=self._recent)

    def _do_stream_stop(self, req: Request) -> dict:
        try:
            self.backend.stop_stream()  # idempotent — ok even when idle
        except Exception as exc:  # noqa: BLE001
            return fail("internal", "stream_failed", repr(exc))
        return ok_value()

    # ── configure ──────────────────────────────────────────────────────

    def _on_configure(self, query) -> None:
        serve_query(query, self._do_configure, recent=self._recent)

    def _do_configure(self, req: Request) -> dict:
        try:
            cmd = ConfigureCmd.from_wire(req.args)
        except Exception as exc:  # noqa: BLE001
            return fail("invalid", "bad_request", str(exc))
        try:
            self.backend.configure(cmd)
        except Exception as exc:  # noqa: BLE001
            return fail("internal", "configure_failed", repr(exc))
        return ok_value()

    # ── status (1 Hz) ────────────────────────────────────────────────────

    def _status_loop(self) -> None:
        last_count = 0
        last_t = time.monotonic()
        while not self._stop_event.wait(1.0):
            st = self.backend.status()
            sp = self.backend.active_stream()
            with self._state_lock:
                count = self._published_count
            now = time.monotonic()
            elapsed = now - last_t
            rate = (count - last_count) / elapsed if elapsed > 0 else 0.0
            last_count, last_t = count, now
            status = CameraStatus(
                t=now_ns(),
                connected=st.get("connected", False),
                streaming=sp is not None,
                stream=sp,
                exposure_us=st.get("exposure_us"),
                gain_db=st.get("gain_db"),
                achieved_rate_hz=rate,
                error=st.get("error"),
            )
            try:
                self._pub_status.put(encode(status.to_wire()))
            except Exception:
                _log.warning("status publish failed", exc_info=True)
