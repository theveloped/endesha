"""Unit tests for the sim camera frame-processing path (no hardware)."""

import cv2
import numpy as np
import pytest

from wf.contracts.camera2d.messages import (
    ENCODING_BAYER_RG8,
    ENCODING_JPEG,
    FrameSpec,
)
from wf.hal.camera2d_sim.processing import process_frame

_JPEG_SOI = b"\xff\xd8"


def _bgr(h: int = 64, w: int = 96) -> np.ndarray:
    rng = np.random.default_rng(11)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def test_jpeg_full_frame():
    data, w, h = process_frame(_bgr(), FrameSpec(encoding=ENCODING_JPEG, quality=90))
    assert data[:2] == _JPEG_SOI
    assert (w, h) == (96, 64)


def test_jpeg_scale_halves_dimensions():
    data, w, h = process_frame(
        _bgr(), FrameSpec(encoding=ENCODING_JPEG, quality=90, scale=0.5)
    )
    assert data[:2] == _JPEG_SOI
    assert (w, h) == (48, 32)


def test_jpeg_roi_crop_keeps_odd_coords():
    _data, w, h = process_frame(
        _bgr(), FrameSpec(encoding=ENCODING_JPEG, roi=[11, 21, 31, 41])
    )
    assert (w, h) == (31, 41)


def test_raw_mosaic_dimensions_and_length():
    data, w, h = process_frame(_bgr(), FrameSpec(encoding=ENCODING_BAYER_RG8))
    assert (w, h) == (96, 64)
    assert len(data) == 96 * 64  # single-plane 8-bit Bayer


def test_raw_roi_even_clamped():
    # x=11,y=21,w=31,h=41 -> even-clamped 10,20,30,40 (preserves CFA phase).
    data, w, h = process_frame(
        _bgr(), FrameSpec(encoding=ENCODING_BAYER_RG8, roi=[11, 21, 31, 41])
    )
    assert (w, h) == (30, 40)
    assert len(data) == 30 * 40


def test_raw_mosaic_debayers_back_to_similar_color():
    # A flat color round-trips through mosaic + debayer to ~itself.
    bgr = np.empty((32, 32, 3), np.uint8)
    bgr[:] = (40, 130, 200)  # B, G, R
    data, w, h = process_frame(bgr, FrameSpec(encoding=ENCODING_BAYER_RG8))
    bayer = np.frombuffer(data, np.uint8).reshape(h, w)
    back = cv2.cvtColor(bayer, cv2.COLOR_BayerRG2BGR)
    assert np.allclose(back[4:-4, 4:-4].mean(axis=(0, 1)), (40, 130, 200), atol=12)


def test_invalid_scale_on_raw_rejected():
    with pytest.raises(ValueError):
        FrameSpec(encoding=ENCODING_BAYER_RG8, scale=0.5)
