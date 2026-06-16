"""Consumer-side frame decode: image bytes + FrameHeader -> ndarray.

The HALs only carry producer-side encode paths; a processor needs the inverse.
Pure, hardware-free, unit-testable — the seam the processors call.
"""

from __future__ import annotations

import cv2
import numpy as np

from wf.contracts.camera2d.messages import (
    ENCODING_BAYER_RG8,
    ENCODING_JPEG,
    ENCODING_MONO8,
    FrameHeader,
)


def decode_frame(data: bytes, header: FrameHeader) -> np.ndarray:
    """Image bytes + header -> ndarray. BGR for color encodings, ``(h, w)`` for Mono8."""
    buf = np.frombuffer(data, np.uint8)
    if header.encoding == ENCODING_JPEG:
        # UNCHANGED: a grayscale JPEG stays 1-channel, color stays BGR.
        return cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
    if header.encoding == ENCODING_BAYER_RG8:
        return cv2.cvtColor(
            buf.reshape(header.h, header.w), cv2.COLOR_BayerRG2BGR
        )
    if header.encoding == ENCODING_MONO8:
        return buf.reshape(header.h, header.w)
    raise ValueError(f"unsupported encoding {header.encoding!r}")
