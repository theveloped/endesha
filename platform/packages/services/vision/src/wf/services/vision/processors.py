"""Pure pixel transforms. Each processor: ``ndarray -> (bytes, w, h, encoding)``
so the pipeline runtime stays transform-agnostic.
"""

from __future__ import annotations

import cv2
import numpy as np

from wf.contracts.camera2d.messages import ENCODING_JPEG, ENCODING_MONO8


def grayscale(img: np.ndarray) -> tuple[bytes, int, int, str]:
    """BGR -> Mono8. A 2D (already-Mono8) input passes through unchanged."""
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    return gray.tobytes(), gray.shape[1], gray.shape[0], ENCODING_MONO8


def center_crop(img: np.ndarray, *, frac: float) -> tuple[bytes, int, int, str]:
    """Centered crop of ``round(w*frac) x round(h*frac)`` (each clamped >= 1).

    2D (Mono8) input -> Mono8; 3D (BGR) input -> JPEG (no raw single-plane
    encoding for color).
    """
    if frac <= 0 or frac > 1:
        raise ValueError(f"frac must be in (0, 1], got {frac!r}")
    h, w = img.shape[0], img.shape[1]
    cw = max(1, round(w * frac))
    ch = max(1, round(h * frac))
    x0 = (w - cw) // 2
    y0 = (h - ch) // 2
    cropped = img[y0 : y0 + ch, x0 : x0 + cw]
    if cropped.ndim == 2:
        return cropped.tobytes(), cw, ch, ENCODING_MONO8
    ok, encoded = cv2.imencode(".jpg", cropped)
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return encoded.tobytes(), cw, ch, ENCODING_JPEG


def draw_detections(
    img: np.ndarray, detections: list[dict]
) -> tuple[bytes, int, int, str]:
    """Annotate ``img`` with each detection's bbox + text; return a JPEG frame.

    Mirrors the color processor return contract ``(bytes, w, h, encoding)`` so
    the pipeline's image-republish path carries the overlay unchanged. A 2D
    (Mono8) input is promoted to BGR so the green annotations are visible.
    Zero detections -> a clean (un-annotated) JPEG of the frame, not an error.
    """
    canvas = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img.copy()
    for det in detections:
        pts = np.asarray(det["corners"], dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(canvas, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
        x, y = int(det["corners"][0][0]), int(det["corners"][0][1])
        cv2.putText(
            canvas,
            det["text"],
            (x, max(0, y - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )
    h, w = canvas.shape[0], canvas.shape[1]
    ok, encoded = cv2.imencode(".jpg", canvas)
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return encoded.tobytes(), w, h, ENCODING_JPEG
