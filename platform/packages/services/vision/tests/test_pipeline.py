"""In-process bus tests: a camera frame drives the gray pipeline, and the gray
output drives the crop pipeline — proving gray->crop chaining over zenoh.
"""

from __future__ import annotations

import functools
import time

import cv2
import numpy as np
import pytest

from wf.contracts.camera2d.messages import ENCODING_JPEG, FrameHeader
from wf.contracts.vision import keys as vision_keys
from wf.core.codec import decode, encode
from wf.core.testing import linked_sessions
from wf.services.vision import processors
from wf.services.vision.service import VisionPipeline

REALM = "sim"
CAM_KEY = "sim/camera2d/cam0/image"


@pytest.fixture
def linked():
    with linked_sessions() as (session_a, session_b):
        yield session_a, session_b


def _wait_until(predicate, timeout_s: float, message: str) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(message)


def _camera_frame() -> tuple[bytes, FrameHeader]:
    bgr = np.zeros((60, 80, 3), np.uint8)
    bgr[:] = (10, 200, 50)
    ok, enc = cv2.imencode(".jpg", bgr)
    assert ok
    header = FrameHeader(
        t_capture=123456789,
        frame_id="camera2d/cam0/optical",
        w=80,
        h=60,
        encoding=ENCODING_JPEG,
        exposure_us=2000.0,
        gain_db=1.5,
        seq=7,
    )
    return enc.tobytes(), header


def test_grayscale_pipeline_over_bus(linked):
    session_a, session_b = linked
    driver = VisionPipeline(
        session_a, REALM, "gray", input_topic=CAM_KEY, transform=processors.grayscale
    )
    driver.start()

    received: list = []
    sub = session_b.declare_subscriber(
        vision_keys.image(REALM, "gray"), lambda s: received.append(s)
    )
    time.sleep(0.5)  # route propagation

    data, header = _camera_frame()
    pub = session_b.declare_publisher(CAM_KEY)
    try:
        pub.put(data, attachment=encode(header.to_wire()))
        _wait_until(lambda: received, 5.0, "no gray frame received")
        sample = received[0]
        out = FrameHeader.from_wire(decode(sample.attachment))
        assert out.encoding == "Mono8"
        assert out.t_capture == header.t_capture
        assert out.frame_id == header.frame_id
        assert out.seq == 0
        assert len(bytes(sample.payload)) == out.w * out.h
    finally:
        pub.undeclare()
        sub.undeclare()
        driver.shutdown()


def test_gray_then_crop_chained_over_bus(linked):
    session_a, session_b = linked
    gray = VisionPipeline(
        session_a, REALM, "gray", input_topic=CAM_KEY, transform=processors.grayscale
    )
    crop = VisionPipeline(
        session_a,
        REALM,
        "crop",
        input_topic=vision_keys.image(REALM, "gray"),
        transform=functools.partial(processors.center_crop, frac=0.5),
    )
    gray.start()
    crop.start()

    received: list = []
    sub = session_b.declare_subscriber(
        vision_keys.image(REALM, "crop"), lambda s: received.append(s)
    )
    time.sleep(0.5)  # route propagation

    data, header = _camera_frame()
    pub = session_b.declare_publisher(CAM_KEY)
    try:
        pub.put(data, attachment=encode(header.to_wire()))
        _wait_until(lambda: received, 5.0, "no crop frame received")
        sample = received[0]
        out = FrameHeader.from_wire(decode(sample.attachment))
        assert out.encoding == "Mono8"
        assert out.t_capture == header.t_capture
        assert (out.w, out.h) == (40, 30)  # half of 80x60
        assert len(bytes(sample.payload)) == out.w * out.h
    finally:
        pub.undeclare()
        sub.undeclare()
        crop.shutdown()
        gray.shutdown()
