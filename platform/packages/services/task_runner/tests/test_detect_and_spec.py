"""Unit tests for the detection vision pipeline pieces and the flow spec."""

from __future__ import annotations

import numpy as np
import pytest
import zxingcpp

from wf.services.vision.detectors import detect_barcodes
from wf.services.vision.processors import draw_detections
from wf.services.task_runner.spec import validate_spec
from wf.contracts.camera2d.messages import ENCODING_JPEG

_PAYLOAD = "WF-PART-0042"


def _datamatrix_bgr(scale: int = 8) -> np.ndarray:
    b = zxingcpp.create_barcode(_PAYLOAD, zxingcpp.BarcodeFormat.DataMatrix)
    gray = np.asarray(b.to_image(scale=scale))
    if gray.ndim == 3:
        gray = gray[:, :, 0]
    return np.stack([gray, gray, gray], axis=-1)


# ── detector ─────────────────────────────────────────────────────────────


def test_detect_datamatrix_returns_payload():
    img = _datamatrix_bgr()
    dets = detect_barcodes(img, fmt="DataMatrix")
    assert len(dets) == 1
    assert dets[0]["text"] == _PAYLOAD
    assert "Matrix" in dets[0]["format"]
    assert len(dets[0]["corners"]) == 4
    assert all(len(c) == 2 for c in dets[0]["corners"])


def test_detect_any_format_decodes_datamatrix():
    dets = detect_barcodes(_datamatrix_bgr(), fmt="Any")
    assert [d["text"] for d in dets] == [_PAYLOAD]


def test_detect_empty_frame_returns_empty():
    blank = np.full((64, 64, 3), 255, np.uint8)
    assert detect_barcodes(blank, fmt="Any") == []


def test_detect_unknown_format_raises():
    with pytest.raises(ValueError):
        detect_barcodes(_datamatrix_bgr(), fmt="Nonsense")


# ── overlay drawer ─────────────────────────────────────────────────────────


def test_draw_detections_returns_valid_jpeg():
    import cv2

    img = _datamatrix_bgr()
    dets = detect_barcodes(img, fmt="DataMatrix")
    data, w, h, enc = draw_detections(img, dets)
    assert enc == ENCODING_JPEG
    out = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    assert out is not None and out.ndim == 3
    assert (w, h) == (img.shape[1], img.shape[0])
    assert out.shape[:2] == (h, w)


def test_draw_detections_empty_is_clean_jpeg():
    img = np.full((40, 60, 3), 200, np.uint8)
    data, w, h, enc = draw_detections(img, [])
    assert enc == ENCODING_JPEG
    assert len(data) > 0 and (w, h) == (60, 40)


def test_draw_detections_promotes_grayscale():
    gray = np.full((30, 30), 128, np.uint8)
    data, w, h, enc = draw_detections(gray, [])
    assert enc == ENCODING_JPEG and (w, h) == (30, 30)


# ── flow spec validation ────────────────────────────────────────────────

_GOOD = {
    "name": "demo_inspect",
    "poses": ["inspect_a", "inspect_b"],
    "vision": {"format": "DataMatrix", "min_count": 1, "pipeline": "demo_detect"},
    "conveyor": {"do_pin": 0, "di_pin": 0, "timeout_s": 2.0},
}


def test_validate_spec_defaults():
    out = validate_spec({"name": "m", "poses": ["a"]})
    assert out["vision"] == {"format": "Any", "min_count": 1, "pipeline": "m_detect"}
    assert out["conveyor"] == {"do_pin": 0, "di_pin": 0, "timeout_s": 3.0}


def test_validate_spec_full():
    out = validate_spec(dict(_GOOD))
    assert out["name"] == "demo_inspect"
    assert out["poses"] == ["inspect_a", "inspect_b"]
    assert out["vision"]["pipeline"] == "demo_detect"


@pytest.mark.parametrize(
    "bad",
    [
        {"poses": ["a"]},  # no name
        {"name": "a b", "poses": ["a"]},  # whitespace in name
        {"name": "a/b", "poses": ["a"]},  # slash in name
        {"name": "m", "poses": []},  # empty poses
        {"name": "m", "poses": "a"},  # poses not a list
        {"name": "m", "poses": ["a"], "vision": {"format": "EAN13"}},  # bad format
        {"name": "m", "poses": ["a"], "vision": {"min_count": -1}},  # bad min_count
        {"name": "m", "poses": ["a"], "conveyor": {"timeout_s": 0}},  # bad timeout
        {"name": "m", "poses": ["a"], "conveyor": {"do_pin": -1}},  # bad pin
    ],
)
def test_validate_spec_rejects(bad):
    with pytest.raises(ValueError) as exc:
        validate_spec(bad)
    assert str(exc.value).startswith("bad_flow:")
