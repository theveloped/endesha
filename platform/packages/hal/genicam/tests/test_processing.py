"""Unit tests for the pure frame-processing path (no hardware)."""

import numpy as np
import pytest

from wf.contracts.camera2d.messages import (
    ENCODING_BAYER_RG8,
    ENCODING_JPEG,
    FrameSpec,
)
from wf.hal.genicam.processing import process_frame, t_capture_ns

JPEG_SOI = b"\xff\xd8"


def _mosaic(h: int = 64, w: int = 96) -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.integers(0, 256, size=(h, w), dtype=np.uint8)


def test_jpeg_full_frame():
    raw = _mosaic()
    data, w, h = process_frame(raw, FrameSpec(encoding=ENCODING_JPEG, quality=90))
    assert data[:2] == JPEG_SOI
    assert (w, h) == (96, 64)


def test_jpeg_scale_halves_dimensions():
    raw = _mosaic()
    data, w, h = process_frame(
        raw, FrameSpec(encoding=ENCODING_JPEG, quality=90, scale=0.5)
    )
    assert data[:2] == JPEG_SOI
    assert (w, h) == (48, 32)


def test_jpeg_roi_crop_changes_dimensions():
    raw = _mosaic()
    data, w, h = process_frame(
        raw, FrameSpec(encoding=ENCODING_JPEG, roi=[10, 20, 30, 40])
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
    # x=11,y=21,w=31,h=41 -> even-clamped 10,20,30,40 (preserves CFA phase)
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
    raw = _mosaic()
    _data, w, h = process_frame(
        raw, FrameSpec(encoding=ENCODING_JPEG, roi=[11, 21, 31, 41])
    )
    assert (w, h) == (31, 41)


def test_t_capture_ns_subtracts_half_exposure():
    # 10 ms exposure -> midpoint is 5 ms (5_000_000 ns) before the
    # end-of-exposure hardware stamp.
    assert t_capture_ns(1_000_000_000, 100, 10_000.0) == 1_000_000_100 - 5_000_000


def test_t_capture_ns_applies_epoch_offset():
    assert t_capture_ns(50, 1_000, 0.0) == 1_050
