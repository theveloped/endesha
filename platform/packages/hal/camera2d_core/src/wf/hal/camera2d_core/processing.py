"""Shared frame-processing path for camera2d providers (RFC step 5).

The ONE path for stream frames and grabs (a StreamParams is a FrameSpec).
``process_frame`` takes a raw 2D Bayer mosaic (the hardware camera form);
``process_bgr_frame`` takes a debayered BGR image (a renderer's form) and
mosaics back to BayerRG8 for raw output. Both are unit-testable without
hardware. Consolidated from the former genicam + camera2d_sim ``processing``.
"""

from __future__ import annotations

import cv2
import numpy as np

from wf.contracts.camera2d.messages import ENCODING_JPEG, FrameSpec


def process_frame(raw: np.ndarray, spec: FrameSpec) -> tuple[bytes, int, int]:
    """Raw 2D Bayer mosaic -> ``(encoded_bytes, out_w, out_h)`` per spec.

    ROI crop first (numpy slice in full-res pixel coords). For raw output the
    crop offsets AND extents are rounded DOWN to even values so the 2x2 Bayer
    CFA phase is preserved; jpeg output (debayered first) has no such
    constraint. Then jpeg: debayer (COLOR_BayerRG2BGR) + INTER_AREA resize when
    ``scale != 1.0`` + imencode. Raw: cropped mosaic bytes (``scale != 1.0``
    cannot reach here — FrameSpec.__post_init__ rejects it).
    """
    if spec.roi is not None:
        x, y, w, h = spec.roi
        if spec.encoding != ENCODING_JPEG:
            x, y, w, h = x & ~1, y & ~1, w & ~1, h & ~1
        raw = raw[y : y + h, x : x + w]
    if spec.encoding == ENCODING_JPEG:
        bgr = cv2.cvtColor(raw, cv2.COLOR_BayerRG2BGR)
        if spec.scale != 1.0:
            bgr = cv2.resize(
                bgr, None, fx=spec.scale, fy=spec.scale, interpolation=cv2.INTER_AREA
            )
        ok, encoded = cv2.imencode(
            ".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, spec.quality]
        )
        if not ok:
            raise RuntimeError("cv2.imencode failed")
        return encoded.tobytes(), bgr.shape[1], bgr.shape[0]
    return raw.tobytes(), raw.shape[1], raw.shape[0]


def _bgr_to_bayer_rg8(bgr: np.ndarray) -> np.ndarray:
    """Mosaic a BGR image into a single-plane Bayer matching this stack's
    ``BayerRG8`` convention — i.e. one that ``cv2.COLOR_BayerRG2BGR`` (the
    debayer the genicam HAL and every downstream consumer use) decodes back to
    the original color. Empirically that places B at (0,0) and R at (1,1).
    """
    b, g, r = bgr[:, :, 0], bgr[:, :, 1], bgr[:, :, 2]
    bayer = np.empty(bgr.shape[:2], dtype=np.uint8)
    bayer[0::2, 0::2] = b[0::2, 0::2]  # B
    bayer[0::2, 1::2] = g[0::2, 1::2]  # G
    bayer[1::2, 0::2] = g[1::2, 0::2]  # G
    bayer[1::2, 1::2] = r[1::2, 1::2]  # R
    return bayer


def process_bgr_frame(bgr: np.ndarray, spec: FrameSpec) -> tuple[bytes, int, int]:
    """Rendered/debayered BGR -> ``(encoded_bytes, out_w, out_h)`` per spec.

    Same ROI/even-clamp/scale rules as ``process_frame``; jpeg skips debayering
    (already BGR), raw mosaics back to a BayerRG8 plane so raw consumers still
    see a genuine CFA.
    """
    if spec.roi is not None:
        x, y, w, h = spec.roi
        if spec.encoding != ENCODING_JPEG:
            x, y, w, h = x & ~1, y & ~1, w & ~1, h & ~1
        bgr = bgr[y : y + h, x : x + w]
    if spec.encoding == ENCODING_JPEG:
        out = bgr
        if spec.scale != 1.0:
            out = cv2.resize(
                out, None, fx=spec.scale, fy=spec.scale, interpolation=cv2.INTER_AREA
            )
        ok, encoded = cv2.imencode(
            ".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, spec.quality]
        )
        if not ok:
            raise RuntimeError("cv2.imencode failed")
        return encoded.tobytes(), out.shape[1], out.shape[0]
    bayer = _bgr_to_bayer_rg8(bgr)
    return bayer.tobytes(), bayer.shape[1], bayer.shape[0]


def t_capture_ns(hw_ts_ns: int, epoch_offset_ns: int, exposure_us: float) -> int:
    """Host-mapped exposure midpoint.

    FLIR stamps end-of-exposure; subtract half the exposure to get the
    midpoint: ``hw_ts_ns + epoch_offset_ns - exposure_us/2 * 1000``.
    """
    return int(hw_ts_ns) + int(epoch_offset_ns) - int(exposure_us * 500)
