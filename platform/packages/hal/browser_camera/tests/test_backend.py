from __future__ import annotations

import pytest

from wf.contracts.camera2d.messages import ENCODING_JPEG, ProducerFrame, StreamParams
from wf.hal.browser_camera.backend import BrowserCameraBackend


class _Publisher:
    def put(self, *_args, **_kwargs):
        pass


class _Session:
    def declare_publisher(self, _key):
        return _Publisher()


@pytest.fixture
def backend():
    params = {
        "render": {"width": 1280, "height": 800},
        "producer_lease_ttl_s": 10.0,
    }
    result = BrowserCameraBackend(_Session(), "cell", "cam0", params)
    grant, error = result._lease.acquire("browser-a", "alice")
    assert error is None
    result._test_grant = grant
    return result


def _frame(backend, **changes):
    grant = backend._test_grant
    values = {
        "client_id": "browser-a",
        "authority_id": grant["authority_id"],
        "epoch": grant["epoch"],
        "captured_at": 1,
        "w": 320,
        "h": 200,
        "encoding": ENCODING_JPEG,
        "exposure_us": 10000.0,
        "gain_db": 0.0,
    }
    values.update(changes)
    return ProducerFrame(**values)


def test_accepts_current_fence_and_matching_dimensions(backend):
    backend._stream = StreamParams(
        rate_hz=15.0, scale=0.25, encoding=ENCODING_JPEG, quality=75
    )
    captured = backend._validated_frame(_frame(backend), b"\xff\xd8ok\xff\xd9")
    assert captured.w == 320
    assert captured.h == 200


def test_rejects_stale_epoch(backend):
    with pytest.raises(ValueError, match="stale producer grant"):
        backend._validated_frame(
            _frame(backend, epoch=backend._test_grant["epoch"] - 1),
            b"\xff\xd8ok\xff\xd9",
        )


def test_rejects_wrong_dimensions_for_stream_demand(backend):
    backend._stream = StreamParams(
        rate_hz=15.0, scale=0.25, encoding=ENCODING_JPEG, quality=75
    )
    with pytest.raises(ValueError, match="dimensions"):
        backend._validated_frame(
            _frame(backend, w=321), b"\xff\xd8ok\xff\xd9"
        )
