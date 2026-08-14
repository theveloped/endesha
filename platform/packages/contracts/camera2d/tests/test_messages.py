"""Wire roundtrip tests for every camera2d contract message."""

import pytest

from wf.contracts.camera2d.messages import (
    Ack,
    CameraStatus,
    ConfigureCmd,
    ENCODING_BAYER_RG8,
    ENCODING_JPEG,
    FrameHeader,
    FrameSpec,
    GrabReply,
    ProducerAck,
    ProducerFrame,
    ProducerGrant,
    StreamParams,
)
from wf.core.codec import decode, encode

HEADER = FrameHeader(
    t_capture=1_700_000_000_000_000_000,
    frame_id="camera2d/cam0/optical",
    w=2448,
    h=2048,
    encoding=ENCODING_JPEG,
    exposure_us=5000.0,
    gain_db=2.5,
    seq=42,
    clock_domain="camera_hw",
)

HEADER_POSED = FrameHeader(
    t_capture=1_700_000_000_000_000_000,
    frame_id="camera2d/cam0/optical",
    w=1280,
    h=800,
    encoding=ENCODING_JPEG,
    exposure_us=10000.0,
    gain_db=0.0,
    seq=7,
    pose={
        "frame": "arm/r1/base",
        "xyz": [0.1, 0.2, 0.5],
        "quat": [0.0, 0.0, 0.0, 1.0],
    },
)

GRANT = ProducerGrant(
    client_id="browser-1",
    user="operator",
    authority_id="backend-1",
    epoch=3,
    granted_at=100,
    expires_at=200,
)


@pytest.mark.parametrize(
    "msg",
    [
        Ack(ok=False, error="nope"),
        HEADER,
        HEADER_POSED,
        FrameSpec(scale=0.5, roi=[10, 20, 640, 480], encoding=ENCODING_JPEG, quality=80),
        FrameSpec(),
        StreamParams(rate_hz=30.0, scale=0.25, encoding=ENCODING_JPEG, quality=75),
        ConfigureCmd(exposure_us=4000.0, auto_gain=True, wb_red=1.2),
        ConfigureCmd(),
        GrabReply(ok=True, header=HEADER, data=b"\xff\xd8spam"),
        GrabReply(ok=False, error="camera is streaming - stop the stream first"),
        GRANT,
        ProducerAck(ok=True, owner=GRANT),
        ProducerFrame(
            client_id="browser-1",
            authority_id="backend-1",
            epoch=3,
            captured_at=150,
            w=320,
            h=200,
            encoding=ENCODING_JPEG,
            exposure_us=10000.0,
            gain_db=0.0,
        ),
        CameraStatus(
            t=1,
            connected=True,
            streaming=True,
            stream=StreamParams(rate_hz=15.0, scale=0.25, encoding=ENCODING_JPEG),
            exposure_us=5000.0,
            gain_db=0.0,
            achieved_rate_hz=14.9,
            error=None,
        ),
        CameraStatus(
            t=2,
            connected=False,
            streaming=False,
            stream=None,
            exposure_us=None,
            gain_db=None,
            achieved_rate_hz=0.0,
            error="no camera",
        ),
    ],
    ids=lambda m: type(m).__name__,
)
def test_wire_roundtrip(msg):
    assert type(msg).from_wire(msg.to_wire()) == msg


def test_streamparams_wire_shape_is_flat():
    wire = StreamParams(rate_hz=10.0, scale=0.5, encoding=ENCODING_JPEG).to_wire()
    assert set(wire) == {"rate_hz", "scale", "roi", "encoding", "quality"}


def test_framespec_rejects_bad_encoding():
    with pytest.raises(ValueError):
        FrameSpec(encoding="png")


def test_framespec_rejects_zero_scale():
    with pytest.raises(ValueError):
        FrameSpec(scale=0.0, encoding=ENCODING_JPEG)


def test_framespec_rejects_short_roi():
    with pytest.raises(ValueError):
        FrameSpec(roi=[0, 0, 640], encoding=ENCODING_JPEG)


def test_framespec_rejects_zero_size_roi():
    with pytest.raises(ValueError):
        FrameSpec(roi=[0, 0, 0, 480], encoding=ENCODING_JPEG)


def test_framespec_rejects_raw_with_scale():
    with pytest.raises(ValueError, match="scale requires jpeg"):
        FrameSpec(encoding=ENCODING_BAYER_RG8, scale=0.5)


def test_streamparams_rejects_bad_rate():
    with pytest.raises(ValueError):
        StreamParams(rate_hz=0.0)
    with pytest.raises(ValueError):
        StreamParams(rate_hz=61.0)


def test_frameheader_rejects_bad_encoding():
    with pytest.raises(ValueError):
        FrameHeader(
            t_capture=1,
            frame_id="camera2d/cam0/optical",
            w=1,
            h=1,
            encoding="png",
            exposure_us=1.0,
            gain_db=0.0,
            seq=0,
        )


def test_grabreply_data_survives_cbor():
    reply = GrabReply(ok=True, header=HEADER, data=b"\xff\xd8\x00\x01\x02jpegbytes")
    wire = decode(encode(reply.to_wire()))
    parsed = GrabReply.from_wire(wire)
    assert parsed == reply
    assert isinstance(parsed.data, bytes)
    assert parsed.data[:2] == b"\xff\xd8"


def test_frameheader_omits_pose_when_absent():
    # Additive/back-compat: a header without a pose carries no `pose` key, so
    # older consumers/recorded frames are unaffected.
    assert "pose" not in HEADER.to_wire()
    assert FrameHeader.from_wire(HEADER.to_wire()).pose is None


def test_frameheader_carries_pose_when_present():
    wire = HEADER_POSED.to_wire()
    assert wire["pose"] == HEADER_POSED.pose
    assert FrameHeader.from_wire(wire).pose == HEADER_POSED.pose
