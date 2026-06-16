"""Frame-processing path for the sim camera — the ONE path for stream frames
and grabs (a StreamParams is a FrameSpec). Input is the renderer's debayered
BGR image, so the JPEG path skips debayering; the raw path mosaics back to a
BayerRG8 plane so raw consumers still see a genuine CFA. Unit-testable.
"""

from __future__ import annotations

import cv2
import numpy as np

from wf.contracts.camera2d.messages import ENCODING_JPEG, FrameSpec


def _bgr_to_bayer_rg8(bgr: np.ndarray) -> np.ndarray:
    """Mosaic a BGR image into a single-plane Bayer matching this stack's
    ``BayerRG8`` convention — i.e. one that ``cv2.COLOR_BayerRG2BGR`` (the
    debayer the genicam HAL and every downstream consumer use) decodes back
    to the original color. Empirically that places B at (0,0) and R at (1,1).
    """
    b, g, r = bgr[:, :, 0], bgr[:, :, 1], bgr[:, :, 2]
    bayer = np.empty(bgr.shape[:2], dtype=np.uint8)
    bayer[0::2, 0::2] = b[0::2, 0::2]  # B
    bayer[0::2, 1::2] = g[0::2, 1::2]  # G
    bayer[1::2, 0::2] = g[1::2, 0::2]  # G
    bayer[1::2, 1::2] = r[1::2, 1::2]  # R
    return bayer


def process_frame(bgr: np.ndarray, spec: FrameSpec) -> tuple[bytes, int, int]:
    """Rendered BGR -> ``(encoded_bytes, out_w, out_h)`` per spec.

    ROI crop first (numpy slice, full-res pixel coords). For raw output the
    crop offsets AND extents are rounded DOWN to even values so the 2x2 Bayer
    CFA phase is preserved (matches the genicam HAL); jpeg has no such
    constraint. Then jpeg: optional INTER_AREA resize + imencode. Raw:
    mosaic the cropped BGR (``scale != 1.0`` cannot reach here — FrameSpec
    rejects it).
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
