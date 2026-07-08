"""The vision frame-processor pipeline runtime (design §10.9).

A processor subscribes to one ``.../image`` topic (payload = image bytes,
attachment = CBOR FrameHeader), decodes per ``header.encoding``, applies a pure
pixel transform, re-encodes, and republishes on ``{realm}/vision/{pipeline}/image``
— preserving ``t_capture``/``frame_id``, setting its own ``seq``, updating
``w``/``h``/``encoding`` (the FrameHeader bus convention). Single input,
single output; no detection, no fan-in.
"""

from __future__ import annotations

import argparse
import functools
import os
import threading

import cv2
import zenoh

from wf.contracts.camera2d.messages import ENCODING_JPEG, FrameHeader
from wf.contracts.vision import keys as vision_keys
from wf.core.codec import decode, encode
from wf.core.keys import key, realm_prefix
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import now_ns

from . import detectors, processors
from .frames import decode_frame

_log = get_logger("wf.services.vision.pipeline")


def _decode_head(sample):
    """``(FrameHeader, ndarray)`` from a frame sample, or ``None`` if headerless.

    The shared decode prologue both pipeline runtimes call: attachment ->
    FrameHeader, payload -> decoded ndarray.
    """
    if sample.attachment is None:
        _log.debug("frame without attachment header, skipping")
        return None
    header = FrameHeader.from_wire(decode(sample.attachment))
    img = decode_frame(bytes(sample.payload), header)
    return header, img


class VisionPipeline:
    """Subscriber-driven processor: input ``image`` topic -> derived ``image`` topic."""

    def __init__(
        self,
        session,
        realm: str,
        pipeline: str,
        *,
        input_topic: str,
        transform,
    ):
        self.session = session
        self.realm = realm
        self.pipeline = pipeline
        self.input_topic = input_topic
        self._transform = transform
        self._pub = session.declare_publisher(
            vision_keys.image(realm, pipeline),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._seq = 0
        self._sub = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._sub = self.session.declare_subscriber(self.input_topic, self._on_frame)
        _log.info(
            "vision pipeline up: realm=%s pipeline=%s input=%s",
            self.realm,
            self.pipeline,
            self.input_topic,
        )

    def _on_frame(self, sample) -> None:
        try:
            decoded = _decode_head(sample)
            if decoded is None:
                return
            header, img = decoded
            out_bytes, w, h, encoding = self._transform(img)
            out_header = FrameHeader(
                t_capture=header.t_capture,
                frame_id=header.frame_id,
                w=w,
                h=h,
                encoding=encoding,
                exposure_us=header.exposure_us,
                gain_db=header.gain_db,
                seq=self._seq,
                clock_domain=header.clock_domain,
            )
            self._seq += 1
            self._pub.put(out_bytes, attachment=encode(out_header.to_wire()))
        except (ValueError, KeyError, TypeError, cv2.error):
            _log.warning("malformed frame, skipping", exc_info=True)
            return

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
        if self._sub is not None:
            try:
                self._sub.undeclare()
            except Exception:
                pass
        _log.info("vision pipeline stopped")


class DetectorPipeline:
    """Subscriber-driven detector: input ``image`` -> ``result`` + overlay ``image``.

    While ``self._enabled`` it decodes every received frame, publishes the
    structured ``detections`` on the ``result`` topic AND an annotated overlay
    on the derived ``image`` topic. A ``cmd/enable`` queryable toggles the
    flag (and optional format) at runtime; a freshly launched pipeline is idle
    (``_enabled=False``) until something turns it on.
    """

    def __init__(
        self,
        session,
        realm: str,
        pipeline: str,
        *,
        input_topic: str,
        fmt: str = "Any",
        enabled: bool = False,
    ):
        self.session = session
        self.realm = realm
        self.pipeline = pipeline
        self.input_topic = input_topic
        self._fmt = fmt
        self._enabled = enabled
        self._image_pub = session.declare_publisher(
            vision_keys.image(realm, pipeline),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._result_pub = session.declare_publisher(
            vision_keys.result(realm, pipeline),
            congestion_control=zenoh.CongestionControl.DROP,
        )
        self._seq = 0
        self._sub = None
        self._enable_q = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._sub = self.session.declare_subscriber(self.input_topic, self._on_frame)
        self._enable_q = self.session.declare_queryable(
            vision_keys.cmd_enable(self.realm, self.pipeline), self._on_enable
        )
        _log.info(
            "detector pipeline up: realm=%s pipeline=%s input=%s fmt=%s",
            self.realm,
            self.pipeline,
            self.input_topic,
            self._fmt,
        )

    def _on_enable(self, query) -> None:
        k = str(query.key_expr)
        try:
            req = decode(query.payload) if query.payload is not None else {}
            self._enabled = bool(req.get("enabled", False))
            fmt = req.get("fmt")
            if isinstance(fmt, str) and fmt:
                self._fmt = fmt
            query.reply(k, encode({"ok": True, "enabled": self._enabled}))
        except Exception as exc:  # noqa: BLE001 — never crash on a bad request
            query.reply(k, encode({"ok": False, "error": repr(exc)}))

    def _on_frame(self, sample) -> None:
        if not self._enabled:
            return
        try:
            decoded = _decode_head(sample)
            if decoded is None:
                return
            header, img = decoded
            detections = detectors.detect_barcodes(img, fmt=self._fmt)
            out_bytes, w, h, encoding = processors.draw_detections(img, detections)
            out_header = FrameHeader(
                t_capture=header.t_capture,
                frame_id=header.frame_id,
                w=w,
                h=h,
                encoding=encoding,
                exposure_us=header.exposure_us,
                gain_db=header.gain_db,
                seq=self._seq,
                clock_domain=header.clock_domain,
            )
            self._image_pub.put(out_bytes, attachment=encode(out_header.to_wire()))
            self._result_pub.put(
                encode(
                    {
                        "t": now_ns(),
                        "frame_id": header.frame_id,
                        "t_capture": header.t_capture,
                        "seq": self._seq,
                        "detections": detections,
                    }
                )
            )
            self._seq += 1
        except (ValueError, KeyError, TypeError, cv2.error):
            _log.warning("malformed frame, skipping", exc_info=True)
            return

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
        for handle in (self._sub, self._enable_q):
            if handle is not None:
                try:
                    handle.undeclare()
                except Exception:
                    pass
        _log.info("detector pipeline stopped")


_OPS = {
    "grayscale": lambda args: processors.grayscale,
    "center_crop": lambda args: functools.partial(
        processors.center_crop, frac=args.crop_frac
    ),
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="wf.services.vision", description=__doc__)
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument(
        "--pipeline", required=True, help="output pipeline name (vision/{pipeline}/image)"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="input topic without realm and /image suffix, e.g. camera2d/cam0 or vision/gray",
    )
    parser.add_argument(
        "--op",
        required=True,
        choices=("grayscale", "center_crop", "detect"),
        help="transform or 'detect' (barcode/DataMatrix detector pipeline)",
    )
    parser.add_argument(
        "--detect-format",
        default="Any",
        choices=("DataMatrix", "QRCode", "Any"),
        help="symbology for --op detect (default Any)",
    )
    parser.add_argument(
        "--crop-frac", type=float, default=0.5, help="center_crop fraction (default 0.5)"
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    input_topic = key(realm_prefix(args.realm), *args.input.split("/"), "image")

    session = open_session(args.zenoh_config)
    token = declare_alive(session, args.realm, "vision", args.pipeline)
    if args.op == "detect":
        driver = DetectorPipeline(
            session,
            args.realm,
            args.pipeline,
            input_topic=input_topic,
            fmt=args.detect_format,
        )
    else:
        driver = VisionPipeline(
            session,
            args.realm,
            args.pipeline,
            input_topic=input_topic,
            transform=_OPS[args.op](args),
        )
    try:
        driver.start()
        driver.run_forever()
    finally:
        del token
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
