"""The `camera2d_sim` driver process (design §5.4, camera2d contract).

A rendering HAL: every frame — stream or grab — is a CPU pinhole projection
of a known checkerboard target at the eye-in-hand camera pose, derived from
the sim arm's ``state/flange`` (so the view tracks the robot, exactly the
digital-twin camera the design calls for). It serves the IDENTICAL queryables
and ``image``/``state/status`` keys as the genicam HAL, so the UI, recorder,
calibration and vision phases cannot tell it from a real camera.

No camera, no GPU: always "connected". Frames go out on the one ``image``
topic (payload = image bytes, attachment = CBOR FrameHeader, one shared
per-process ``seq``). Grab is REJECTED while streaming.
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
from wf.core.frames import transform_to_xyz_quat
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import CLOCK_HOST, now_ns
from wf.world_model.frames_live import build_live_tree
from wf.world_model.scene_live import build_live_scene

from .config import load_resource
from .processing import process_frame
from .render import Renderer

_log = get_logger("wf.hal.camera2d_sim.driver")

_STREAM_JOIN_TIMEOUT_S = 3.0


class SimCameraDriver:
    """v0: serves the camera2d contract from the cv2 pinhole renderer.

    Produces a SINGLE BGR image on the one ``image`` topic — no depth, no
    segmentation (the contract carries one image topic today). Design §5.4's
    pyrender path (color+depth+segmentation) is roadmap phase 9.
    """

    def __init__(self, session, realm: str, cid: str, params: dict):
        self.session = session
        self.realm = realm
        self.cid = cid
        self.params = params
        self.frame_id = keys.optical_frame(cid)
        self.mount_arm = str(params["mount_arm"])

        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()  # guards the mutable state below
        self._stream_params: StreamParams | None = None
        self._stream_thread: threading.Thread | None = None
        self._stream_stop = threading.Event()
        self._seq = 0
        self._published_count = 0
        self._last_t_capture = 0
        self._error: str | None = None
        self._flange_xyz: list[float] | None = None
        self._flange_quat: list[float] | None = None

        render = params["render"]
        self._exposure_us = float(render["exposure_us"])  # virtual
        self._gain_db = float(render["gain_db"])
        # Live bus views the renderer rebuilds its scene from each frame —
        # {realm}/scene/** objects posed through the static+dynamic frame tree,
        # the same views collision preflight reads. build_live_* declare their
        # subscribers immediately (undeclared in shutdown). Scene objects parent
        # up to "world".
        self._live_scene, self._scene_sub = build_live_scene(session, realm)
        self._live_frames, self._frames_sub = build_live_tree(session, realm)
        self._renderer = Renderer(
            render,
            live_scene=self._live_scene,
            live_frames=self._live_frames,
            base_frame="world",
        )

        # Best-effort stream (design §3): drop under congestion.
        self._pub_image = session.declare_publisher(
            keys.image(realm, cid),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._pub_status = session.declare_publisher(keys.state_status(realm, cid))
        self._queryables: list = []
        self._flange_sub = None

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
        # Eye-in-hand: follow the sim arm's flange so the rendered view tracks
        # the robot. Absent an arm (e.g. conformance), the renderer falls back
        # to a fixed top-down pose.
        self._flange_sub = self.session.declare_subscriber(
            arm_keys.state_flange(self.realm, self.mount_arm), self._on_flange
        )
        threading.Thread(
            target=self._status_loop, name="status-loop", daemon=True
        ).start()
        _log.info(
            "camera2d_sim up: realm=%s cid=%s mount_arm=%s",
            self.realm,
            self.cid,
            self.mount_arm,
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
        for sub in (self._scene_sub, self._frames_sub):
            try:
                sub.undeclare()
            except Exception:
                pass
        for q in self._queryables:
            try:
                q.undeclare()
            except Exception:
                pass
        _log.info("camera2d_sim stopped")

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

    # ── frame publishing (the ONE path for stream and grab frames) ───────
    def _render_frame(self, spec: FrameSpec) -> tuple[bytes, int, int, dict]:
        with self._state_lock:
            xyz, quat = self._flange_xyz, self._flange_quat
        bgr = self._renderer.render(xyz, quat)
        # The world<-optical pose the renderer actually used for THIS frame
        # (eye-in-hand when a flange sample exists, else the fallback top-down
        # pose). Stamped into the header so the UI frustum matches the frame.
        pos, rot = transform_to_xyz_quat(self._renderer.camera_pose(xyz, quat))
        pose = {"frame": "world", "xyz": pos, "quat": rot}
        data, w, h = process_frame(bgr, spec)
        return data, w, h, pose

    def _publish_frame(
        self, data: bytes, w: int, h: int, encoding: str, pose: dict | None = None
    ) -> FrameHeader:
        with self._state_lock:
            exposure = self._exposure_us
            gain = self._gain_db
            # Synthetic exposure midpoint on the host clock.
            t_capture = now_ns() - int(exposure * 500)
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
            clock_domain=CLOCK_HOST,
            pose=pose,
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
        # Already streaming -> stop first, restart with the new params.
        self._stop_stream()
        self._stream_stop.clear()
        with self._state_lock:
            self._stream_params = sp
        thread = threading.Thread(
            target=self._stream_loop, args=(sp,), name="stream-loop", daemon=True
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

    def _stream_loop(self, sp: StreamParams) -> None:
        period = 1.0 / sp.rate_hz
        try:
            next_due = time.monotonic()
            while not (self._stream_stop.is_set() or self._stop_event.is_set()):
                now = time.monotonic()
                if now < next_due:
                    self._stream_stop.wait(min(period, next_due - now))
                    continue
                next_due += period
                if next_due < now:  # fell behind -> resync the cadence
                    next_due = now + period
                data, w, h, pose = self._render_frame(sp)
                self._publish_frame(data, w, h, sp.encoding, pose)
        except Exception as exc:
            with self._state_lock:
                self._error = f"stream failed: {exc!r}"
            _log.error("stream loop failed", exc_info=True)
        finally:
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
        if streaming:
            fail("camera is streaming - stop the stream first")
            return
        try:
            payload = decode(query.payload) if query.payload is not None else {}
            spec = FrameSpec.from_wire({**self.params["grab_defaults"], **payload})
        except Exception as exc:
            fail(str(exc))
            return
        try:
            data, w, h, pose = self._render_frame(spec)
            # Publish on the image topic exactly like a stream frame (grabs are
            # recorded and pipeline-consumable — design §5.5), then duplicate
            # into the synchronous reply.
            header = self._publish_frame(data, w, h, spec.encoding, pose)
            query.reply(
                key, encode(GrabReply(ok=True, header=header, data=data).to_wire())
            )
        except Exception as exc:
            fail(repr(exc))

    # ── configure (virtual exposure/gain) ────────────────────────────────

    def _on_configure(self, query) -> None:
        key = str(query.key_expr)
        try:
            cmd = ConfigureCmd.from_wire(
                decode(query.payload) if query.payload is not None else {}
            )
            with self._state_lock:
                if cmd.exposure_us is not None:
                    self._exposure_us = float(cmd.exposure_us)
                if cmd.gain_db is not None:
                    self._gain_db = float(cmd.gain_db)
            query.reply(key, encode(Ack(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(Ack(ok=False, error=repr(exc)).to_wire()))

    # ── status (1 Hz) ────────────────────────────────────────────────────

    def _status_loop(self) -> None:
        last_count = 0
        last_t = time.monotonic()
        while not self._stop_event.wait(1.0):
            with self._state_lock:
                sp = self._stream_params
                error = self._error
                count = self._published_count
                exposure = self._exposure_us
                gain = self._gain_db
            now = time.monotonic()
            elapsed = now - last_t
            rate = (count - last_count) / elapsed if elapsed > 0 else 0.0
            last_count, last_t = count, now
            status = CameraStatus(
                t=now_ns(),
                connected=True,
                streaming=sp is not None,
                stream=sp,
                exposure_us=exposure,
                gain_db=gain,
                achieved_rate_hz=rate,
                error=error,
            )
            try:
                self._pub_status.put(encode(status.to_wire()))
            except Exception:
                _log.warning("status publish failed", exc_info=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="camera2d_sim", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument("--resource", default="cam0", help="resource id (default cam0)")
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "sim"),
        help="realm (default env WF_REALM or 'sim')",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    params = load_resource(args.cell, args.resource)
    session = open_session(args.zenoh_config)
    token = declare_alive(session, args.realm, "camera2d", args.resource)

    driver = SimCameraDriver(session, args.realm, args.resource, params)
    try:
        driver.start()
        driver.run_forever()
    finally:
        del token
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
