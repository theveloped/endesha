"""Backend that accepts fenced JPEG frames from one elected browser producer."""

from __future__ import annotations

import threading

from wf.contracts.camera2d import keys
from wf.contracts.camera2d.messages import (
    ENCODING_JPEG,
    ProducerAck,
    ProducerFrame,
    ProducerGrant,
)
from wf.core.camera_info import CameraInfo
from wf.core.codec import decode, encode
from wf.core.lease import FencedLease
from wf.core.log import get_logger
from wf.core.time import now_ns
from wf.hal.camera2d_core import CapturedFrame

_log = get_logger("wf.hal.browser_camera")


class BrowserCameraBackend:
    """Camera2d backend whose acquisition device is an elected browser tab."""

    def __init__(self, session, realm: str, cid: str, params: dict):
        self.session = session
        self.realm = realm
        self.cid = cid
        self.params = params
        self._lease = FencedLease(params.get("producer_lease_ttl_s", 10.0))
        self._core = None
        self._stream = None
        self._lock = threading.Lock()
        self._last_frame_at = 0
        self._error = None
        self._queryables = []
        self._ingress_sub = None
        self._owner_pub = session.declare_publisher(keys.producer_state_owner(realm, cid))
        self._demand_pub = session.declare_publisher(keys.producer_state_demand(realm, cid))
        self._max_payload_bytes = int(params.get("producer_max_payload_bytes", 8 * 1024 * 1024))

    def start(self, core) -> None:
        self._core = core
        self._queryables = [
            self.session.declare_queryable(
                keys.producer_cmd_acquire(self.realm, self.cid), self._on_acquire
            ),
            self.session.declare_queryable(
                keys.producer_cmd_release(self.realm, self.cid), self._on_release
            ),
            self.session.declare_queryable(
                keys.producer_state_owner(self.realm, self.cid),
                self._on_owner_query,
            ),
            self.session.declare_queryable(
                keys.producer_state_demand(self.realm, self.cid),
                self._on_demand_query,
            ),
        ]
        self._ingress_sub = self.session.declare_subscriber(
            keys.producer_ingress(self.realm, self.cid), self._on_ingress
        )
        self._publish_owner()
        self._publish_demand()

    def shutdown(self) -> None:
        self._stream = None
        if self._ingress_sub is not None:
            self._ingress_sub.undeclare()
            self._ingress_sub = None
        for queryable in self._queryables:
            queryable.undeclare()
        self._queryables = []

    def grab(self, spec) -> CapturedFrame:
        owner = self._lease.owner()
        if owner is None:
            raise RuntimeError("no browser producer")
        request = {
            "authority_id": owner["authority_id"],
            "epoch": owner["epoch"],
            "spec": spec.to_wire(),
        }
        replies = self.session.get(
            keys.producer_render(self.realm, self.cid, owner["client_id"]),
            payload=encode(request),
            timeout=5.0,
        )
        for reply in replies:
            if reply.ok is None:
                continue
            sample = reply.ok
            attachment = sample.attachment
            if attachment is None:
                continue
            frame = ProducerFrame.from_wire(decode(attachment))
            return self._validated_frame(frame, sample.payload.to_bytes())
        raise RuntimeError("browser producer did not answer grab")

    def start_stream(self, spec) -> None:
        if spec.encoding != ENCODING_JPEG:
            raise ValueError("browser producer supports jpeg only")
        with self._lock:
            self._stream = spec
        self._publish_demand()

    def stop_stream(self) -> None:
        with self._lock:
            self._stream = None
        self._publish_demand()

    def active_stream(self):
        with self._lock:
            return self._stream

    def configure(self, cmd) -> None:
        if cmd.exposure_us is not None:
            self.params["exposure_us"] = cmd.exposure_us
        if cmd.gain_db is not None:
            self.params["gain_db"] = cmd.gain_db
        self._publish_demand()

    def status(self) -> dict:
        owner = self._lease.owner()
        stale = owner is None or now_ns() - self._last_frame_at > 3_000_000_000
        return {
            "connected": owner is not None and (self.active_stream() is None or not stale),
            "exposure_us": float(self.params.get("exposure_us", 10000.0)),
            "gain_db": float(self.params.get("gain_db", 0.0)),
            "error": "no browser producer" if owner is None else self._error,
        }

    def _on_acquire(self, query) -> None:
        key = str(query.key_expr)
        try:
            req = decode(query.payload) if query.payload is not None else {}
            owner, error = self._lease.acquire(req["client_id"], req.get("user", "operator"))
            self._publish_owner()
            current = owner if owner is not None else self._lease.owner()
            ack = ProducerAck(
                ok=error is None,
                owner=None if current is None else ProducerGrant.from_wire(current),
                error=error,
            )
            query.reply(key, encode(ack.to_wire()))
        except Exception as exc:
            query.reply(key, encode(ProducerAck(ok=False, error=repr(exc)).to_wire()))

    def _on_release(self, query) -> None:
        key = str(query.key_expr)
        try:
            req = decode(query.payload) if query.payload is not None else {}
            self._lease.release(req.get("client_id"))
            self._publish_owner()
            query.reply(key, encode(ProducerAck(ok=True).to_wire()))
        except Exception as exc:
            query.reply(key, encode(ProducerAck(ok=False, error=repr(exc)).to_wire()))

    def _on_ingress(self, sample) -> None:
        try:
            attachment = sample.attachment
            if attachment is None:
                raise ValueError("producer frame attachment missing")
            payload = sample.payload.to_bytes()
            frame = ProducerFrame.from_wire(decode(attachment))
            captured = self._validated_frame(frame, payload)
            if self.active_stream() is None:
                return
            self._core.publish_frame(captured)
            self._last_frame_at = now_ns()
            self._error = None
        except Exception as exc:
            self._error = str(exc)
            _log.warning("browser frame rejected: %s", exc)

    def _validated_frame(self, frame: ProducerFrame, payload: bytes) -> CapturedFrame:
        if not self._lease.holds(frame.client_id, frame.authority_id, frame.epoch):
            raise ValueError("stale producer grant")
        if len(payload) > self._max_payload_bytes:
            raise ValueError("producer frame exceeds payload limit")
        if len(payload) < 4 or payload[:2] != b"\xff\xd8" or payload[-2:] != b"\xff\xd9":
            raise ValueError("producer payload is not jpeg")
        stream = self.active_stream()
        if stream is not None:
            render = self.params.get("render", {})
            expected_w = max(1, round(float(render.get("width", frame.w)) * stream.scale))
            expected_h = max(1, round(float(render.get("height", frame.h)) * stream.scale))
            if (frame.w, frame.h) != (expected_w, expected_h):
                raise ValueError("producer frame dimensions do not match demand")
        return CapturedFrame(
            data=payload,
            w=frame.w,
            h=frame.h,
            encoding=frame.encoding,
            hw_ts_ns=0,
            exposure_us=frame.exposure_us,
            gain_db=frame.gain_db,
            pose=frame.pose,
        )

    def _on_owner_query(self, query) -> None:
        query.reply(
            str(query.key_expr),
            encode({"t": now_ns(), "owner": self._lease.owner()}),
        )

    def _on_demand_query(self, query) -> None:
        query.reply(str(query.key_expr), encode(self._demand_payload()))

    def _publish_owner(self) -> None:
        owner = self._lease.owner()
        payload = {
            "t": now_ns(),
            "owner": owner,
        }
        self._owner_pub.put(encode(payload))

    def _optics(self) -> dict:
        """Pinhole optics for the browser producer: ``config/intrinsics/{cid}``
        (CameraInfo layout, the calibrated truth) when the store has it, else
        the cell ``render`` block (design defaults)."""
        render = self.params.get("render", {})
        fallback = {
            "w": int(render.get("width", 1280)),
            "h": int(render.get("height", 800)),
            "fx": float(render.get("fx", 900.0)),
            "fy": float(render.get("fy", 900.0)),
        }
        session = getattr(self, "session", None)
        cid = getattr(self, "cid", None)
        if session is None or cid is None:
            return fallback
        try:
            for reply in session.get(f"config/intrinsics/{cid}", timeout=0.5):
                if reply.ok is not None:
                    info = CameraInfo.from_wire(decode(reply.ok.payload))
                    return {"w": info.width, "h": info.height, "fx": info.fx, "fy": info.fy}
        except Exception:
            _log.debug("intrinsics fetch failed; using render block", exc_info=True)
        return fallback

    def _demand_payload(self) -> dict:
        stream = self.active_stream()
        render = self.params.get("render", {})
        return {
            "t": now_ns(),
            "stream": None if stream is None else stream.to_wire(),
            "intrinsics": self._optics(),
            "mount_xyz": list(
                render.get(
                    "mount_xyz",
                    self.params.get("mount_xyz", [0, 0, 0.05]),
                )
            ),
            "mount_rpy_deg": list(
                render.get(
                    "mount_rpy_deg",
                    self.params.get("mount_rpy_deg", [0, 0, 0]),
                )
            ),
            "exposure_us": float(self.params.get("exposure_us", 10000.0)),
            "gain_db": float(self.params.get("gain_db", 0.0)),
        }

    def _publish_demand(self) -> None:
        self._demand_pub.put(encode(self._demand_payload()))
