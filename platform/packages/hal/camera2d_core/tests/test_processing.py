"""Unit tests for the shared frame-processing path (no hardware).

Covers both the raw-Bayer ``process_frame`` (hardware camera form, ex-genicam)
and the BGR ``process_bgr_frame`` (renderer form, ex-camera2d_sim), plus the
mosaic helper and the exposure-midpoint timestamp.
"""

import cv2
import numpy as np
import pytest

from wf.contracts.camera2d.messages import (
    ENCODING_BAYER_RG8,
    ENCODING_JPEG,
    FrameSpec,
)
from wf.hal.camera2d_core.processing import (
    process_bgr_frame,
    process_frame,
    t_capture_ns,
)

JPEG_SOI = b"\xff\xd8"


def _mosaic(h: int = 64, w: int = 96) -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.integers(0, 256, size=(h, w), dtype=np.uint8)


def _bgr(h: int = 64, w: int = 96) -> np.ndarray:
    rng = np.random.default_rng(11)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


# ── process_frame: raw Bayer input (hardware camera) ─────────────────────────


def test_jpeg_full_frame():
    data, w, h = process_frame(_mosaic(), FrameSpec(encoding=ENCODING_JPEG, quality=90))
    assert data[:2] == JPEG_SOI
    assert (w, h) == (96, 64)


def test_jpeg_scale_halves_dimensions():
    data, w, h = process_frame(
        _mosaic(), FrameSpec(encoding=ENCODING_JPEG, quality=90, scale=0.5)
    )
    assert data[:2] == JPEG_SOI
    assert (w, h) == (48, 32)


def test_jpeg_roi_crop_changes_dimensions():
    data, w, h = process_frame(
        _mosaic(), FrameSpec(encoding=ENCODING_JPEG, roi=[10, 20, 30, 40])
    )
    assert data[:2] == JPEG_SOI
    assert (w, h) == (30, 40)


def test_raw_passthrough_byte_equal():
    raw = _mosaic()
    data, w, h = process_frame(raw, FrameSpec(encoding=ENCODING_BAYER_RG8))
    assert data == raw.tobytes()
    assert (w, h) == (96, 64)


def test_raw_roi_odd_coords_rounded_down_to_even():
    raw = _mosaic()
    data, w, h = process_frame(
        raw, FrameSpec(encoding=ENCODING_BAYER_RG8, roi=[11, 21, 31, 41])
    )
    assert (w, h) == (30, 40)
    assert data == raw[20 : 20 + 40, 10 : 10 + 30].tobytes()


def test_raw_roi_even_coords_unchanged():
    raw = _mosaic()
    data, w, h = process_frame(
        raw, FrameSpec(encoding=ENCODING_BAYER_RG8, roi=[2, 4, 16, 8])
    )
    assert (w, h) == (16, 8)
    assert data == raw[4:12, 2:18].tobytes()


def test_jpeg_roi_keeps_odd_coords():
    _data, w, h = process_frame(
        _mosaic(), FrameSpec(encoding=ENCODING_JPEG, roi=[11, 21, 31, 41])
    )
    assert (w, h) == (31, 41)


# ── process_bgr_frame: debayered BGR input (renderer) ────────────────────────


def test_bgr_jpeg_full_frame():
    data, w, h = process_bgr_frame(_bgr(), FrameSpec(encoding=ENCODING_JPEG, quality=90))
    assert data[:2] == JPEG_SOI
    assert (w, h) == (96, 64)


def test_bgr_jpeg_scale_halves_dimensions():
    data, w, h = process_bgr_frame(
        _bgr(), FrameSpec(encoding=ENCODING_JPEG, quality=90, scale=0.5)
    )
    assert data[:2] == JPEG_SOI
    assert (w, h) == (48, 32)


def test_bgr_jpeg_roi_crop_keeps_odd_coords():
    _data, w, h = process_bgr_frame(
        _bgr(), FrameSpec(encoding=ENCODING_JPEG, roi=[11, 21, 31, 41])
    )
    assert (w, h) == (31, 41)


def test_bgr_raw_mosaic_dimensions_and_length():
    data, w, h = process_bgr_frame(_bgr(), FrameSpec(encoding=ENCODING_BAYER_RG8))
    assert (w, h) == (96, 64)
    assert len(data) == 96 * 64  # single-plane 8-bit Bayer


def test_bgr_raw_roi_even_clamped():
    data, w, h = process_bgr_frame(
        _bgr(), FrameSpec(encoding=ENCODING_BAYER_RG8, roi=[11, 21, 31, 41])
    )
    assert (w, h) == (30, 40)
    assert len(data) == 30 * 40


def test_bgr_raw_mosaic_debayers_back_to_similar_color():
    bgr = np.empty((32, 32, 3), np.uint8)
    bgr[:] = (40, 130, 200)  # B, G, R
    data, w, h = process_bgr_frame(bgr, FrameSpec(encoding=ENCODING_BAYER_RG8))
    bayer = np.frombuffer(data, np.uint8).reshape(h, w)
    back = cv2.cvtColor(bayer, cv2.COLOR_BayerRG2BGR)
    assert np.allclose(back[4:-4, 4:-4].mean(axis=(0, 1)), (40, 130, 200), atol=12)


def test_invalid_scale_on_raw_rejected():
    with pytest.raises(ValueError):
        FrameSpec(encoding=ENCODING_BAYER_RG8, scale=0.5)


# ── t_capture_ns ─────────────────────────────────────────────────────────────


def test_t_capture_ns_subtracts_half_exposure():
    assert t_capture_ns(1_000_000_000, 100, 10_000.0) == 1_000_000_100 - 5_000_000


def test_t_capture_ns_applies_epoch_offset():
    assert t_capture_ns(50, 1_000, 0.0) == 1_050
