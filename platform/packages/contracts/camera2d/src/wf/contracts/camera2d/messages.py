"""Hand-written `camera2d` contract wire messages (no codegen in phase 1).

Wire field names in ``to_wire``/``from_wire`` are normative. Conventions:
timestamps int nanoseconds, exposure microseconds, gain dB. Frame payloads
travel OUTSIDE these messages: zenoh payload = image bytes, zenoh
attachment = CBOR-encoded :class:`FrameHeader`.
"""

from __future__ import annotations

from dataclasses import dataclass

from wf.core.time import CLOCK_HOST

ENCODING_BAYER_RG8 = "BayerRG8"
ENCODING_JPEG = "jpeg"
ENCODING_MONO8 = "Mono8"
ENCODINGS = (ENCODING_BAYER_RG8, ENCODING_JPEG, ENCODING_MONO8)


@dataclass
class FrameHeader:
    """CBOR attachment on every frame topic; embedded in GrabReply.

    The bus-wide frame convention: producers publish image bytes as the payload
    and this header as the attachment on an ``.../image`` topic. Derived frame
    producers preserve ``t_capture`` and ``frame_id``, assign their own ``seq``,
    and update ``w``/``h``/``encoding``.
    Origin is carried by the topic; there is no ``source`` field.
    """

    t_capture: int  # ns, exposure midpoint
    frame_id: str  # camera2d/{cid}/optical
    w: int
    h: int
    encoding: str  # ENCODINGS member
    exposure_us: float
    gain_db: float
    seq: int  # monotonic per producer process (shared stream+grab counter)
    clock_domain: str = CLOCK_HOST  # CLOCK_CAMERA once timesync calibrated
    # World<-optical camera pose AT CAPTURE, when known: {frame, xyz[3] (m),
    # quat[4] [x,y,z,w] scalar-last}. ``frame`` is the base/world frame the pose
    # is expressed in (== ``frame_id``'s parent, ``arm/{rid}/base`` in v0).
    # ``None`` when the producer has no pose (e.g. an eye-in-hand camera before
    # its arm's flange streams, or the conformance suite). OPTIONAL/additive —
    # older frames decode with ``pose=None``; consumers ignore it freely.
    pose: dict | None = None

    def __post_init__(self):
        if self.encoding not in ENCODINGS:
            raise ValueError(
                f"encoding must be one of {ENCODINGS}, got {self.encoding!r}"
            )

    def to_wire(self) -> dict:
        d = {
            "t_capture": int(self.t_capture),
            "frame_id": self.frame_id,
            "w": int(self.w),
            "h": int(self.h),
            "encoding": self.encoding,
            "exposure_us": float(self.exposure_us),
            "gain_db": float(self.gain_db),
            "seq": int(self.seq),
            "clock_domain": self.clock_domain,
        }
        if self.pose is not None:
            d["pose"] = self.pose
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "FrameHeader":
        return cls(
            t_capture=d["t_capture"],
            frame_id=d["frame_id"],
            w=d["w"],
            h=d["h"],
            encoding=d["encoding"],
            exposure_us=d["exposure_us"],
            gain_db=d["gain_db"],
            seq=d["seq"],
            clock_domain=d.get("clock_domain", CLOCK_HOST),
            pose=d.get("pose"),
        )

@dataclass
class ProducerGrant:
    """Current browser producer grant, including restart-safe fencing."""

    client_id: str
    user: str
    authority_id: str
    epoch: int
    granted_at: int
    expires_at: int

    def to_wire(self) -> dict:
        return {
            "client_id": self.client_id,
            "user": self.user,
            "authority_id": self.authority_id,
            "epoch": int(self.epoch),
            "granted_at": int(self.granted_at),
            "expires_at": int(self.expires_at),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ProducerGrant":
        return cls(
            client_id=d["client_id"],
            user=d["user"],
            authority_id=d["authority_id"],
            epoch=d["epoch"],
            granted_at=d["granted_at"],
            expires_at=d["expires_at"],
        )


@dataclass
class ProducerFrame:
    """CBOR attachment on a candidate frame published to producer ingress."""

    client_id: str
    authority_id: str
    epoch: int
    captured_at: int
    w: int
    h: int
    encoding: str
    exposure_us: float
    gain_db: float
    pose: dict | None = None

    def __post_init__(self):
        if self.encoding != ENCODING_JPEG:
            raise ValueError("browser producer frames must use jpeg encoding")
        if self.w <= 0 or self.h <= 0:
            raise ValueError("producer frame dimensions must be positive")

    def to_wire(self) -> dict:
        d = {
            "client_id": self.client_id,
            "authority_id": self.authority_id,
            "epoch": int(self.epoch),
            "captured_at": int(self.captured_at),
            "w": int(self.w),
            "h": int(self.h),
            "encoding": self.encoding,
            "exposure_us": float(self.exposure_us),
            "gain_db": float(self.gain_db),
        }
        if self.pose is not None:
            d["pose"] = self.pose
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "ProducerFrame":
        return cls(
            client_id=d["client_id"],
            authority_id=d["authority_id"],
            epoch=d["epoch"],
            captured_at=d["captured_at"],
            w=d["w"],
            h=d["h"],
            encoding=d["encoding"],
            exposure_us=d["exposure_us"],
            gain_db=d["gain_db"],
            pose=d.get("pose"),
        )



@dataclass
class FrameSpec:
    """``cmd/grab`` payload; the shared frame-processing parameters.

    Grab and stream share this exact parameter surface — a
    :class:`StreamParams` is a FrameSpec plus ``rate_hz``. ``roi`` is a
    software crop ``[x, y, w, h]`` in full-resolution pixel coordinates
    (the driver rounds raw-output ROIs down to even values to preserve the
    Bayer CFA phase).
    """

    scale: float = 1.0  # resize factor after crop; jpeg only; 1.0 = native
    roi: list[int] | None = None  # [x, y, w, h] full-res px; None = full
    encoding: str = ENCODING_BAYER_RG8
    quality: int = 95  # JPEG only; ignored for raw

    def __post_init__(self):
        if not 0 < self.scale <= 1:
            raise ValueError(f"scale must be in (0, 1], got {self.scale}")
        if self.encoding not in ENCODINGS:
            raise ValueError(
                f"encoding must be one of {ENCODINGS}, got {self.encoding!r}"
            )
        if not 1 <= self.quality <= 100:
            raise ValueError(f"quality must be in [1, 100], got {self.quality}")
        if self.roi is not None:
            if len(self.roi) != 4:
                raise ValueError(f"roi must be [x, y, w, h], got {self.roi!r}")
            x, y, w, h = self.roi
            if x < 0 or y < 0:
                raise ValueError(f"roi x/y must be non-negative, got {self.roi!r}")
            if w <= 0 or h <= 0:
                raise ValueError(f"roi w/h must be positive, got {self.roi!r}")
        if self.encoding == ENCODING_BAYER_RG8 and self.scale != 1.0:
            raise ValueError("scale requires jpeg encoding")

    def to_wire(self) -> dict:
        return {
            "scale": float(self.scale),
            "roi": None if self.roi is None else [int(v) for v in self.roi],
            "encoding": self.encoding,
            "quality": int(self.quality),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "FrameSpec":
        roi = d.get("roi")
        return cls(
            scale=d.get("scale", 1.0),
            roi=None if roi is None else list(roi),
            encoding=d.get("encoding", ENCODING_BAYER_RG8),
            quality=d.get("quality", 95),
        )


@dataclass
class StreamParams(FrameSpec):
    """``cmd/stream_start`` payload; echoed in :class:`CameraStatus`.

    ``rate_hz`` above the sensor rate (~24 fps at full res, GigE-saturated)
    just publishes every frame — no error.
    """

    rate_hz: float = 15.0  # publish rate; decimated from sensor rate

    def __post_init__(self):
        super().__post_init__()
        if not 0 < self.rate_hz <= 60:
            raise ValueError(f"rate_hz must be in (0, 60], got {self.rate_hz}")

    def to_wire(self) -> dict:
        # Wire shape is FLAT: {rate_hz, scale, roi, encoding, quality}.
        d = super().to_wire()
        d["rate_hz"] = float(self.rate_hz)
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "StreamParams":
        roi = d.get("roi")
        return cls(
            rate_hz=d.get("rate_hz", 15.0),
            scale=d.get("scale", 1.0),
            roi=None if roi is None else list(roi),
            encoding=d.get("encoding", ENCODING_BAYER_RG8),
            quality=d.get("quality", 95),
        )


@dataclass
class ConfigureCmd:
    """``cmd/configure`` payload; all None = no-op.

    Auto toggles map True -> GenICam ``Continuous``, False -> ``Off``.
    """

    exposure_us: float | None = None
    gain_db: float | None = None
    auto_exposure: bool | None = None  # GenICam ExposureAuto Continuous/Off
    auto_gain: bool | None = None
    auto_wb: bool | None = None
    wb_red: float | None = None
    wb_blue: float | None = None

    def to_wire(self) -> dict:
        return {
            "exposure_us": None
            if self.exposure_us is None
            else float(self.exposure_us),
            "gain_db": None if self.gain_db is None else float(self.gain_db),
            "auto_exposure": self.auto_exposure,
            "auto_gain": self.auto_gain,
            "auto_wb": self.auto_wb,
            "wb_red": None if self.wb_red is None else float(self.wb_red),
            "wb_blue": None if self.wb_blue is None else float(self.wb_blue),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "ConfigureCmd":
        return cls(
            exposure_us=d.get("exposure_us"),
            gain_db=d.get("gain_db"),
            auto_exposure=d.get("auto_exposure"),
            auto_gain=d.get("auto_gain"),
            auto_wb=d.get("auto_wb"),
            wb_red=d.get("wb_red"),
            wb_blue=d.get("wb_blue"),
        )


@dataclass
class GrabReply:
    """``cmd/grab`` envelope ``value``: the captured frame — header + image
    bytes (the same frame is also published on the image topic)."""

    header: FrameHeader
    data: bytes

    def to_wire(self) -> dict:
        return {"header": self.header.to_wire(), "data": self.data}

    @classmethod
    def from_wire(cls, d: dict) -> "GrabReply":
        return cls(header=FrameHeader.from_wire(d["header"]), data=d["data"])


@dataclass
class CameraStatus:
    """Camera status keepalive (~1 Hz)."""

    t: int
    connected: bool
    streaming: bool
    stream: StreamParams | None  # active params, None when idle
    exposure_us: float | None  # last read from nodemap; None when disconnected
    gain_db: float | None
    achieved_rate_hz: float  # measured published-frame rate (0 when idle)
    error: str | None = None

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "connected": bool(self.connected),
            "streaming": bool(self.streaming),
            "stream": None if self.stream is None else self.stream.to_wire(),
            "exposure_us": None
            if self.exposure_us is None
            else float(self.exposure_us),
            "gain_db": None if self.gain_db is None else float(self.gain_db),
            "achieved_rate_hz": float(self.achieved_rate_hz),
            "error": self.error,
        }

    @classmethod
    def from_wire(cls, d: dict) -> "CameraStatus":
        stream = d.get("stream")
        return cls(
            t=d["t"],
            connected=d["connected"],
            streaming=d["streaming"],
            stream=None if stream is None else StreamParams.from_wire(stream),
            exposure_us=d.get("exposure_us"),
            gain_db=d.get("gain_db"),
            achieved_rate_hz=d["achieved_rate_hz"],
            error=d.get("error"),
        )


#: Registered envelope error ``reason`` values (wire-contract RFC §5).
ERROR_REASONS = (
    "bad_request",
    "streaming",
    "unsupported_encoding",
    "grab_failed",
    "stream_failed",
    "configure_failed",
    "held_by",
)
