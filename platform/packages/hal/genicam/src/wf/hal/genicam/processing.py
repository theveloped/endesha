"""Pure frame-processing functions — the ONE path for stream frames and
grabs (a StreamParams is a FrameSpec). Unit-testable without hardware."""

from __future__ import annotations

import cv2
import numpy as np

from wf.contracts.camera2d.messages import ENCODING_JPEG, FrameSpec


def process_frame(raw: np.ndarray, spec: FrameSpec) -> tuple[bytes, int, int]:
    """Raw 2D Bayer mosaic -> ``(encoded_bytes, out_w, out_h)`` per spec.

    ROI crop first (numpy slice in full-res pixel coords). For raw output
    the crop offsets AND extents are rounded DOWN to even values so the
    2x2 Bayer CFA phase is preserved; jpeg output (debayered first) has no
    such constraint. Then jpeg: debayer (COLOR_BayerRG2BGR) + INTER_AREA
    resize when ``scale != 1.0`` + imencode. Raw: cropped mosaic bytes
    (``scale != 1.0`` cannot reach here — FrameSpec.__post_init__ rejects
    it).
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
                bgr,
                None,
                fx=spec.scale,
                fy=spec.scale,
                interpolation=cv2.INTER_AREA,
            )
        ok, encoded = cv2.imencode(
            ".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, spec.quality]
        )
        if not ok:
            raise RuntimeError("cv2.imencode failed")
        return encoded.tobytes(), bgr.shape[1], bgr.shape[0]
    return raw.tobytes(), raw.shape[1], raw.shape[0]


def t_capture_ns(hw_ts_ns: int, epoch_offset_ns: int, exposure_us: float) -> int:
    """Host-mapped exposure midpoint.

    FLIR stamps end-of-exposure; subtract half the exposure to get the
    midpoint: ``hw_ts_ns + epoch_offset_ns - exposure_us/2 * 1000``.
    """
    return int(hw_ts_ns) + int(epoch_offset_ns) - int(exposure_us * 500)
