"""Pure unit tests for the vision decode helper and processors (no bus)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from wf.contracts.camera2d.messages import (
    ENCODING_BAYER_RG8,
    ENCODING_JPEG,
    ENCODING_MONO8,
    FrameHeader,
)
from wf.hal.camera2d_sim.processing import _bgr_to_bayer_rg8
from wf.services.vision.frames import decode_frame
from wf.services.vision.processors import center_crop, grayscale


def _header(w: int, h: int, encoding: str) -> FrameHeader:
    return FrameHeader(
        t_capture=1,
        frame_id="camera2d/cam0/optical",
        w=w,
        h=h,
        encoding=encoding,
        exposure_us=1000.0,
        gain_db=0.0,
        seq=0,
    )


# ── decode_frame per-encoding round-trips ────────────────────────────────


def test_decode_bayer_rg8_roundtrips_to_color():
    bgr = np.empty((32, 32, 3), np.uint8)
    bgr[:] = (40, 130, 200)  # B, G, R
    bayer = _bgr_to_bayer_rg8(bgr)
    out = decode_frame(bayer.tobytes(), _header(32, 32, ENCODING_BAYER_RG8))
    assert out.shape == (32, 32, 3)
    assert np.allclose(out[4:-4, 4:-4].mean(axis=(0, 1)), (40, 130, 200), atol=12)


def test_decode_mono8_exact_plane():
    plane = np.arange(6 * 4, dtype=np.uint8).reshape(4, 6)
    out = decode_frame(plane.tobytes(), _header(6, 4, ENCODING_MONO8))
    assert out.shape == (4, 6)
    assert np.array_equal(out, plane)


def test_decode_jpeg_gray_plane_is_2d():
    plane = np.full((8, 10), 128, np.uint8)
    ok, enc = cv2.imencode(".jpg", plane)
    assert ok
    out = decode_frame(enc.tobytes(), _header(10, 8, ENCODING_JPEG))
    assert out.ndim == 2


def test_decode_unknown_encoding_raises():
    h = _header(4, 4, ENCODING_MONO8)
    h.encoding = "weird"  # bypass __post_init__
    with pytest.raises(ValueError):
        decode_frame(b"\x00" * 16, h)


# ── grayscale ────────────────────────────────────────────────────────────


def test_grayscale_bgr_to_mono8():
    bgr = np.zeros((20, 30, 3), np.uint8)
    bgr[:] = (0, 255, 0)  # pure green
    data, w, h, enc = grayscale(bgr)
    assert (w, h, enc) == (30, 20, ENCODING_MONO8)
    plane = np.frombuffer(data, np.uint8).reshape(h, w)
    # BT.601 luma of pure green ~= 150.
    assert abs(plane.mean() - 150) < 5


def test_grayscale_mono8_passthrough_idempotent():
    plane = np.arange(20 * 30, dtype=np.uint8).reshape(20, 30)
    data, w, h, enc = grayscale(plane)
    assert (w, h, enc) == (30, 20, ENCODING_MONO8)
    assert np.array_equal(np.frombuffer(data, np.uint8).reshape(h, w), plane)


# ── center_crop ──────────────────────────────────────────────────────────


def test_center_crop_half_mono8_centered():
    plane = np.zeros((80, 100), np.uint8)
    plane[40, 50] = 200  # center pixel survives
    plane[0, 0] = 200  # edge pixel cropped out
    data, w, h, enc = center_crop(plane, frac=0.5)
    assert (w, h, enc) == (50, 40, ENCODING_MONO8)
    cropped = np.frombuffer(data, np.uint8).reshape(h, w)
    assert cropped[h // 2, w // 2] == 200  # center preserved
    assert cropped[0, 0] == 0  # edge gone


def test_center_crop_frac_one_unchanged():
    plane = np.arange(80 * 100, dtype=np.uint8).reshape(80, 100)
    data, w, h, enc = center_crop(plane, frac=1.0)
    assert (w, h) == (100, 80)
    assert np.array_equal(np.frombuffer(data, np.uint8).reshape(h, w), plane)


def test_center_crop_invalid_frac_raises():
    plane = np.zeros((10, 10), np.uint8)
    with pytest.raises(ValueError):
        center_crop(plane, frac=0.0)
    with pytest.raises(ValueError):
        center_crop(plane, frac=1.5)


def test_center_crop_1x1_clamps():
    plane = np.zeros((1, 1), np.uint8)
    data, w, h, enc = center_crop(plane, frac=0.5)
    assert (w, h, enc) == (1, 1, ENCODING_MONO8)
    assert len(data) == 1


def test_center_crop_bgr_reencodes_jpeg():
    bgr = np.zeros((40, 60, 3), np.uint8)
    data, w, h, enc = center_crop(bgr, frac=0.5)
    assert (w, h, enc) == (30, 20, ENCODING_JPEG)
    assert decode_frame(data, _header(w, h, ENCODING_JPEG)).shape[:2] == (20, 30)
