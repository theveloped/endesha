"""Barcode/DataMatrix detection on a decoded frame (design §10.9, detect op).

Pure decode + corner pixels via zxing-cpp — no pose/grid-correspondence extras.
The pipeline runtime feeds a decoded ndarray; this returns the structured
``detections`` the result topic carries and the overlay drawer annotates.
"""

from __future__ import annotations

import numpy as np
import zxingcpp


def _formats(fmt: str):
    """Map a contract format string to a zxing-cpp ``BarcodeFormat`` (or None=all).

    ``"Any"`` -> None (zxing reads every supported symbology). ``"DataMatrix"``/
    ``"QRCode"`` -> the matching enum member.
    """
    if fmt == "Any":
        return None
    member = getattr(zxingcpp.BarcodeFormat, fmt, None)
    if member is None:
        raise ValueError(f"unknown barcode format {fmt!r}")
    return member


def detect_barcodes(img: np.ndarray, *, fmt: str = "Any") -> list[dict]:
    """Decode barcodes in ``img``; return ``[{text, format, corners}]``.

    ``corners`` is the 4 pixel corners ``[[x,y]*4]`` in
    top-left/top-right/bottom-right/bottom-left order. Zero barcodes -> ``[]``.
    """
    formats = _formats(fmt)
    barcodes = (
        zxingcpp.read_barcodes(img)
        if formats is None
        else zxingcpp.read_barcodes(img, formats=formats)
    )
    out: list[dict] = []
    for b in barcodes:
        p = b.position
        out.append(
            {
                "text": b.text,
                "format": str(b.format),
                "corners": [
                    [p.top_left.x, p.top_left.y],
                    [p.top_right.x, p.top_right.y],
                    [p.bottom_right.x, p.bottom_right.y],
                    [p.bottom_left.x, p.bottom_left.y],
                ],
            }
        )
    return out
